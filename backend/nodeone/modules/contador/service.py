"""Lógica de negocio del módulo Contador."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import secrets
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_

from nodeone.core.db import db
from models.contador import (
    ContadorCaptureLog,
    ContadorCountLine,
    ContadorExportLog,
    ContadorProductTemplate,
    ContadorProductVariant,
    ContadorSession,
)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ''
    s = str(value).strip().upper()
    s = re.sub(r'\s+', ' ', s)
    return s


def format_sesion_display_name(name: str | None) -> str:
    """Texto de sesión para títulos y listas: normaliza espacios y aplica title case (p. ej. PLanta baja → Planta Baja)."""
    if name is None:
        return ''
    s = str(name).strip()
    if not s:
        return ''
    s = re.sub(r'\s+', ' ', s)
    return s.title()


def _next_variant_code(organization_id: int) -> str:
    rows = (
        db.session.query(ContadorProductVariant.code)
        .filter(ContadorProductVariant.organization_id == int(organization_id))
        .all()
    )
    mx = 0
    for (code,) in rows:
        if not code:
            continue
        m = re.match(r'^CNT-(\d+)$', str(code).strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f'CNT-{mx + 1:06d}'


def _cell_str(val) -> str:
    if val is None or (isinstance(val, float) and str(val) == 'nan'):
        return ''
    try:
        import pandas as pd

        if pd.isna(val):
            return ''
    except Exception:
        pass
    return str(val).strip()


def _find_column(columns: list, *aliases: str):
    """Empareja nombre de columna Excel (normalizado) con alias."""
    norm_map = {normalize_text(str(c)): c for c in columns}
    for a in aliases:
        na = normalize_text(a)
        if na in norm_map:
            return norm_map[na]
        for nk, orig in norm_map.items():
            if na and (na in nk or nk in na):
                return orig
    return None


def _find_column_exact(columns: list, *exact_labels: str) -> str | None:
    """Coincidencia exacta del encabezado normalizado (evita falsos positivos con 'SUB')."""
    want = {normalize_text(x) for x in exact_labels}
    for c in columns:
        if normalize_text(str(c)) in want:
            return c
    return None


# Unidades / abreviaturas típicas en columnas "Producto" mal etiquetadas (no son nombre de ítem)
_UOM_TOKENS = frozenset(
    {
        'UND',
        'UN',
        'U',
        'U.',
        'KG',
        'G',
        'GR',
        'LT',
        'L',
        'ML',
        'CC',
        'M',
        'MT',
        'CM',
        'M2',
        'M3',
        'PAR',
        'PZA',
        'PZ',
        'CAJ',
        'BL',
        'ROL',
        'JGO',
        'CJA',
    }
)


def _looks_like_uom(val) -> bool:
    s = _cell_str(val).strip()
    if not s or len(s) > 12:
        return False
    u = normalize_text(s)
    if u in _UOM_TOKENS:
        return True
    return bool(re.match(r'^[A-Z]{1,4}\.?$', u)) and len(u) <= 5


def _looks_like_internal_ref(val) -> bool:
    """Código tipo PA0075, REF-123, etc. (no es categoría de negocio)."""
    s = _cell_str(val).strip()
    if not s or len(s) > 40:
        return False
    u = s.upper().replace(' ', '')
    if re.match(r'^[A-Z]{1,4}\d{4,}$', u):
        return True
    if re.match(r'^[A-Z]{2,4}-?\d{3,}$', u):
        return True
    if re.match(r'^\d{5,}$', u):
        return True
    return False


def _sanitize_variant_code_from_import(raw: str) -> str | None:
    s = _cell_str(raw).strip()
    if not s or len(s) > 36:
        return None
    if not re.match(r'^[A-Za-z0-9._\-]+$', s):
        return None
    return s


def _detect_fixed_layout(
    raw_a: str, raw_b: str, raw_c: str, raw_d: str, raw_e: str
) -> str:
    """
    - classic: A cat, B sub, C clase, D nombre, E presentación (documentación histórica).
    - code_name: A ref interna, B nombre, C clase, D U.M., E presentación (exportaciones típicas).
    """
    b = _cell_str(raw_b)
    e = _cell_str(raw_e)
    if (
        _looks_like_internal_ref(raw_a)
        and len(b) >= 8
        and _looks_like_uom(raw_d)
        and len(e) >= 1
    ):
        return 'code_name'
    return 'classic'


# Límites (models.contador) — nunca exceder al insertar
_TPL_NAME_MAX = 300
_TPL_NAME_NORM_MAX = 320
_TPL_CAT_MAX = 120
_TPL_SUB_MAX = 120
_TPL_CLS_MAX = 80


def _clip_template_dims(cat: str, sub: str, cls: str) -> tuple[str, str, str]:
    return (cat[:_TPL_CAT_MAX], sub[:_TPL_SUB_MAX], cls[:_TPL_CLS_MAX])


def _looks_like_meta_or_instruction(name_raw: str, attr_raw: str) -> bool:
    """Filas de explicación / títulos, no filas de producto con variante."""
    n = (name_raw or '').strip()
    a = (attr_raw or '').strip()
    if not n or not a:
        return True
    nu, au = normalize_text(n), normalize_text(a)
    if len(nu) > 220 or len(au) > 220:
        return True
    blob = f'{nu} {au}'
    markers = (
        'CONSOLIDAT',
        'MADRE/DERIVADO',
        'MADRE / DERIVADO',
        'MADRE DERIVADO',
        'NUEVO FORMATO',
        '548-ROW',
        '548 ROW',
        'BUILT ',
        ' INTO ',
        ' FOR ODOO',
        'IMPORT SHEET',
        'CATALOG SHEETS',
        'SPARSE ',
    )
    if any(m in blob for m in markers):
        return True
    if re.search(
        r'(?i)built\s+\d+\s*[-–]?\s*row|consolidat(e|ed)\s+.*\b(sheet|formato|product)\b',
        f'{n} {a}',
    ):
        return True
    return False


def _pick_data_sheet_name(sheet_names: list[str]) -> str:
    """Prefiere hoja con datos reales (p. ej. 'Nuevo Formato') en lugar de instrucciones."""
    for n in sheet_names:
        nn = normalize_text(str(n))
        if 'INSTRUCC' in nn or 'AYUDA' in nn or 'LEEM' in nn:
            continue
        if any(k in nn for k in ('NUEVO FORMATO', 'IMPORT', 'PRODUCTO', 'CATALOGO', 'ODOO')):
            return n
    for n in sheet_names:
        if 'INSTRUCC' not in normalize_text(n) and 'AYUDA' not in normalize_text(n):
            return n
    return sheet_names[0] if sheet_names else ''


CONTADOR_WIZARD_TMP = Path(tempfile.gettempdir()) / 'nodeone_contador_wizard'


def _excel_col_label(idx: int) -> str:
    """Etiqueta tipo Excel (A, B, … Z, AA, AB)."""
    n = idx + 1
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def wizard_save_upload(raw: bytes, user_id: int) -> str:
    """Guarda el archivo subido y devuelve un token opaco para la sesión del asistente."""
    CONTADOR_WIZARD_TMP.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    dest_dir = CONTADOR_WIZARD_TMP / token
    dest_dir.mkdir(parents=True, exist_ok=False)
    path = dest_dir / 'catalog.xlsx'
    path.write_bytes(raw)
    meta = dest_dir / 'meta.json'
    meta.write_text(json.dumps({'user_id': int(user_id)}), encoding='utf8')
    return token


def wizard_load_path(token: str | None) -> Path | None:
    if not token or '/' in token or '\\' in token or '..' in token:
        return None
    p = CONTADOR_WIZARD_TMP / token / 'catalog.xlsx'
    return p if p.is_file() else None


def wizard_meta(token: str | None) -> dict[str, Any] | None:
    if not token or '/' in token or '\\' in token or '..' in token:
        return None
    mp = CONTADOR_WIZARD_TMP / token / 'meta.json'
    if not mp.is_file():
        return None
    try:
        return json.loads(mp.read_text(encoding='utf8'))
    except Exception:
        return None


def wizard_delete_upload(token: str | None) -> None:
    if not token or '/' in token or '\\' in token or '..' in token:
        return
    d = CONTADOR_WIZARD_TMP / token
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)


def suggest_column_indices(headers: list[str]) -> dict[str, int | None]:
    """Sugerencias iniciales de mapeo (mismo criterio que el import automático)."""
    h = [str(x) for x in headers]

    def _ix(*aliases: str) -> int | None:
        c = _find_column(h, *aliases)
        if c is None:
            return None
        for i, x in enumerate(h):
            if str(x) == str(c):
                return i
        return None

    sub_e = _find_column_exact(h, 'SUB')
    sub_i: int | None
    if sub_e is not None:
        try:
            sub_i = h.index(sub_e)
        except ValueError:
            sub_i = _ix('SUBCATEGORIA', 'SUBCATEGORÍA', 'SUB CATEGORIA', 'SUB-GRUPO', 'SUBGRUPO', 'SUB GRUPO')
    else:
        sub_i = _ix('SUBCATEGORIA', 'SUBCATEGORÍA', 'SUB CATEGORIA', 'SUB-GRUPO', 'SUBGRUPO', 'SUB GRUPO')
    return {
        'name': _ix(
            'DESCRIPCION',
            'DESCRIPCIÓN',
            'DESCRIPCION LARGA',
            'NOMBRE',
            'NOMBRE DEL PRODUCTO',
            'NOMBRE PRODUCTO',
            'NAME',
            'ARTICULO',
            'ARTÍCULO',
            'ITEM',
            'PRODUCT',
            'PRODUCTO',
        ),
        'presentation': _ix(
            'PRESENTACIÓN',
            'PRESENTACION',
            'VARIANTE',
            'MEDIDA',
            'TAMAÑO',
            'FORMATO',
            'ENVASE',
            'CAPACIDAD',
        ),
        'category': _ix(
            'CATEGORIA',
            'CATEGORÍA',
            'CATEGORY',
            'CATEGORÍA PRODUCTO',
            'RUBRO',
            'LINEA',
            'LÍNEA',
            'FAMILIA',
        ),
        'subcategory': sub_i,
        'product_class': _ix(
            'CLASE',
            'CLASE PRODUCTO',
            'TIPO PRODUCTO',
            'PRODUCT CLASS',
            'TIPO',
            'TIPO ARTICULO',
            'TIPO ARTÍCULO',
            'PROD TERMINADO',
            'PRODUCTO TERMINADO',
        ),
        'code': _ix(
            'REFERENCIA INTERNA',
            'REF. INTERNA',
            'REF INTERNA',
            'REFERENCIA',
            'DEFAULT CODE',
            'DEFAULT_CODE',
            'CODIGO',
            'CÓDIGO',
            'CODIGO INTERNO',
            'CÓDIGO INTERNO',
            'INTERNAL REFERENCE',
        ),
        'barcode': _ix(
            'CODIGO DE BARRAS',
            'CÓDIGO DE BARRAS',
            'BARCODE',
            'EAN',
        ),
    }


def build_import_preview(
    raw: bytes,
    *,
    sheet_name: str | None = None,
    has_header: bool = True,
    preview_rows: int = 8,
) -> dict[str, Any]:
    """Vista previa para el asistente de importación (tipo Odoo)."""
    import pandas as pd

    bio = io.BytesIO(raw)
    xl = pd.ExcelFile(bio, engine='openpyxl')
    sheets = list(xl.sheet_names)
    sheet = sheet_name if sheet_name and sheet_name in sheets else _pick_data_sheet_name(sheets)
    bio.seek(0)
    if has_header:
        df = pd.read_excel(bio, sheet_name=sheet, header=0, engine='openpyxl')
        labels = [
            (str(c).strip() if str(c).strip() and str(c) != 'nan' else f'Columna {i + 1}')
            for i, c in enumerate(df.columns)
        ]
    else:
        df = pd.read_excel(bio, sheet_name=sheet, header=None, engine='openpyxl')
        labels = [f'{_excel_col_label(i)} (col. {i + 1})' for i in range(len(df.columns))]
    ncols = len(labels)
    max_r = min(int(preview_rows), len(df))
    rows_out: list[list[str]] = []
    for i in range(max_r):
        r = df.iloc[i]
        rows_out.append([_cell_str(x) for x in r.tolist()])
    if has_header and ncols:
        defaults = suggest_column_indices(labels)
    else:
        defaults = {
            'name': None,
            'presentation': None,
            'category': None,
            'subcategory': None,
            'product_class': None,
            'code': None,
            'barcode': None,
        }
    columns_meta = [{'index': i, 'label': labels[i]} for i in range(ncols)]
    return {
        'sheet_names': sheets,
        'sheet': sheet,
        'has_header': has_header,
        'ncols': ncols,
        'columns': columns_meta,
        'preview_rows': rows_out,
        'defaults': defaults,
    }


def _rows_from_excel_mapping(
    raw: bytes,
    *,
    sheet_name: str,
    has_header: bool,
    col_name: int,
    col_pres: int,
    col_cat: int | None = None,
    col_sub: int | None = None,
    col_cls: int | None = None,
    col_code: int | None = None,
    col_bc: int | None = None,
) -> list[tuple[Any, ...]]:
    """Importación con columnas explícitas (asistente)."""
    import pandas as pd

    bio = io.BytesIO(raw)
    if has_header:
        df = pd.read_excel(bio, sheet_name=sheet_name, header=0, engine='openpyxl')
    else:
        df = pd.read_excel(bio, sheet_name=sheet_name, header=None, engine='openpyxl')
    ncols = int(df.shape[1])

    def _ok(i: int | None) -> bool:
        if i is None:
            return True
        return 0 <= int(i) < ncols

    if not _ok(col_name) or not _ok(col_pres):
        raise ValueError('Las columnas de nombre y presentación no son válidas')
    for label, idx in (
        ('Categoría', col_cat),
        ('Subcategoría', col_sub),
        ('Clase', col_cls),
        ('Código', col_code),
        ('Código de barras', col_bc),
    ):
        if idx is not None and not _ok(idx):
            raise ValueError(f'Columna inválida para {label}')

    out: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        if row.isna().all():
            continue

        def cell(col_idx: int | None) -> str:
            if col_idx is None:
                return ''
            return _cell_str(row.iloc[int(col_idx)])

        name_raw = row.iloc[int(col_name)]
        attr_cell = row.iloc[int(col_pres)]
        raw_name = _cell_str(name_raw)
        raw_attr = _cell_str(attr_cell)
        cat = normalize_text(cell(col_cat)) if col_cat is not None else ''
        sub = normalize_text(cell(col_sub)) if col_sub is not None else ''
        cls = normalize_text(cell(col_cls)) if col_cls is not None else ''
        internal_ref = _sanitize_variant_code_from_import(cell(col_code)) if col_code is not None else None
        bc_part = cell(col_bc) if col_bc is not None else ''
        bc = bc_part or None
        out.append((cat, sub, cls, name_raw, raw_attr, bc, internal_ref))
    return out


def _execute_catalog_import(
    rows_iter,
    organization_id: int,
    filename: str,
) -> dict[str, Any]:
    """Graba plantillas/variantes a partir de filas ya interpretadas."""
    templates_created = 0
    variants_created = 0
    variants_updated = 0
    rows_skipped = 0

    for cat, sub, cls, name_raw, attr_stripped, barcode_opt, internal_ref_opt in rows_iter:
        name_s = _cell_str(name_raw)
        attr_s = _cell_str(attr_stripped)
        if _looks_like_meta_or_instruction(name_s, attr_s):
            rows_skipped += 1
            continue
        name_n = normalize_text(name_s)[:_TPL_NAME_NORM_MAX]
        attr_n = normalize_text(attr_s)
        if not name_n or not attr_n:
            continue
        cat, sub, cls = _clip_template_dims(cat, sub, cls)

        tpl = ContadorProductTemplate.query.filter_by(
            organization_id=organization_id,
            category=cat,
            subcategory=sub,
            product_class=cls,
            name_normalized=name_n,
        ).first()
        if not tpl:
            tpl = ContadorProductTemplate(
                organization_id=organization_id,
                name=name_s[:_TPL_NAME_MAX],
                name_normalized=name_n,
                category=cat,
                subcategory=sub,
                product_class=cls,
                is_active=True,
            )
            db.session.add(tpl)
            db.session.flush()
            templates_created += 1

        display = f'{name_s} - {attr_s}'
        if internal_ref_opt:
            v_by_code = ContadorProductVariant.query.filter_by(
                organization_id=organization_id,
                code=internal_ref_opt,
            ).first()
            if v_by_code:
                v_by_code.template_id = tpl.id
                v_by_code.display_name = display[:400]
                v_by_code.attribute_value = attr_s[:200]
                v_by_code.attribute_value_normalized = attr_n
                v_by_code.is_active = True
                if barcode_opt:
                    v_by_code.barcode = barcode_opt[:80]
                variants_updated += 1
                continue

        existing_v = ContadorProductVariant.query.filter_by(
            template_id=tpl.id,
            attribute_value_normalized=attr_n,
        ).first()
        if existing_v:
            existing_v.display_name = display[:400]
            existing_v.attribute_value = attr_s[:200]
            existing_v.is_active = True
            if barcode_opt:
                existing_v.barcode = barcode_opt[:80]
            variants_updated += 1
            continue

        code = internal_ref_opt or _next_variant_code(organization_id)
        v = ContadorProductVariant(
            organization_id=organization_id,
            template_id=tpl.id,
            attribute_name='PRESENTACIÓN',
            attribute_value=attr_s[:200],
            attribute_value_normalized=attr_n,
            display_name=display[:400],
            code=code,
            barcode=(barcode_opt[:80] if barcode_opt else None),
            is_active=True,
        )
        db.session.add(v)
        variants_created += 1

    db.session.commit()
    return {
        'filename': filename,
        'templates_created': templates_created,
        'variants_created': variants_created,
        'variants_updated': variants_updated,
        'rows_skipped': rows_skipped,
    }


def import_xlsx_bytes_mapped(
    raw: bytes,
    filename: str,
    organization_id: int,
    user_id: int | None,
    *,
    sheet_name: str,
    has_header: bool,
    col_name: int,
    col_pres: int,
    col_cat: int | None = None,
    col_sub: int | None = None,
    col_cls: int | None = None,
    col_code: int | None = None,
    col_bc: int | None = None,
) -> dict[str, Any]:
    """Import con columnas elegidas en el asistente."""
    try:
        import pandas as pd  # noqa: F401
    except ImportError as e:
        raise RuntimeError('pandas es requerido para importar') from e
    rows = _rows_from_excel_mapping(
        raw,
        sheet_name=sheet_name,
        has_header=has_header,
        col_name=col_name,
        col_pres=col_pres,
        col_cat=col_cat,
        col_sub=col_sub,
        col_cls=col_cls,
        col_code=col_code,
        col_bc=col_bc,
    )
    return _execute_catalog_import(rows, organization_id, filename)


def _rows_from_excel(raw: bytes):
    """Devuelve filas (cat, sub, cls, name_raw, attr_raw, barcode_opt, internal_ref_opt)."""
    import pandas as pd

    bio = io.BytesIO(raw)
    xl = pd.ExcelFile(bio, engine='openpyxl')
    sheet = _pick_data_sheet_name(list(xl.sheet_names))
    bio.seek(0)
    df_hdr = pd.read_excel(bio, sheet_name=sheet, header=0, engine='openpyxl')
    cols = list(df_hdr.columns)
    # Descripción / nombre antes que "Producto" (a menudo trae U.M. tipo UND)
    name_col = _find_column(
        cols,
        'DESCRIPCION',
        'DESCRIPCIÓN',
        'DESCRIPCION LARGA',
        'NOMBRE',
        'NOMBRE DEL PRODUCTO',
        'NOMBRE PRODUCTO',
        'NAME',
        'ARTICULO',
        'ARTÍCULO',
        'ITEM',
        'PRODUCT',
        'PRODUCTO',
    )
    attr_col = _find_column(
        cols,
        'PRESENTACIÓN',
        'PRESENTACION',
        'VARIANTE',
        'VARIANTES',
        'ATRIBUTO',
        'ATRIBUTOS',
        'VALOR VARIANTE',
        'VALORES DE VARIANTE',
        'COMBINACION',
        'REFERENCIA VARIANTE',
        'COMBINACION DE ATRIBUTOS',
        'MEDIDA',
        'TAMAÑO',
        'FORMATO',
        'ENVASE',
        'EMPAQUE',
        'CONTENIDO',
        'TALLA',
        'CAPACIDAD',
    )
    cat_col = _find_column(
        cols,
        'CATEGORIA',
        'CATEGORÍA',
        'CATEGORY',
        'CATEGORÍA PRODUCTO',
        'RUBRO',
        'LINEA',
        'LÍNEA',
        'FAMILIA',
    )
    sub_col = _find_column(
        cols, 'SUBCATEGORIA', 'SUBCATEGORÍA', 'SUB CATEGORIA', 'SUB-GRUPO', 'SUBGRUPO', 'SUB GRUPO'
    )
    if not sub_col:
        sub_col = _find_column_exact(cols, 'SUB')
    cls_col = _find_column(
        cols,
        'CLASE',
        'CLASE PRODUCTO',
        'TIPO PRODUCTO',
        'PRODUCT CLASS',
        'TIPO',
        'TIPO ARTICULO',
        'TIPO ARTÍCULO',
        'PROD TERMINADO',
        'PRODUCTO TERMINADO',
    )
    ref_col = _find_column(
        cols,
        'REFERENCIA INTERNA',
        'REF. INTERNA',
        'REF INTERNA',
        'REFERENCIA',
        'DEFAULT CODE',
        'DEFAULT_CODE',
        'CODIGO',
        'CÓDIGO',
        'CODIGO INTERNO',
        'CÓDIGO INTERNO',
        'COD',
        'INTERNAL REFERENCE',
    )
    uom_col = _find_column(
        cols,
        'UM',
        'U M',
        'U.M',
        'U.M.',
        'UD',
        'UDM',
        'UNIDAD',
        'UNIDAD DE MEDIDA',
        'UNIDAD MEDIDA',
        'UOM',
    )
    bc_col = _find_column(
        cols,
        'CODIGO DE BARRAS',
        'CÓDIGO DE BARRAS',
        'BARCODE',
        'EAN',
    )

    if name_col and attr_col:
        out = []
        for _, row in df_hdr.iterrows():
            raw_name = _cell_str(row.get(name_col))
            raw_attr = _cell_str(row.get(attr_col))
            raw_cat = _cell_str(row.get(cat_col)) if cat_col else ''
            raw_sub = _cell_str(row.get(sub_col)) if sub_col else ''
            raw_ref = _cell_str(row.get(ref_col)) if ref_col else ''
            raw_uom = _cell_str(row.get(uom_col)) if uom_col else ''

            # Columnas desplazadas: "Categoría" con código, Sub con nombre largo, Producto con UND
            if (
                _looks_like_uom(raw_name)
                and _looks_like_internal_ref(raw_cat)
                and len(raw_sub.strip()) >= 8
            ):
                internal_ref = _sanitize_variant_code_from_import(raw_cat) or None
                name_raw = raw_sub
                attr_stripped = raw_attr
                cat = ''
                sub = ''
                cls = normalize_text(_cell_str(row.get(cls_col)) if cls_col else '')
                bc = _cell_str(row.get(bc_col)) if bc_col else ''
                if raw_uom:
                    attr_stripped = attr_stripped or raw_uom
                _nn = normalize_text(_cell_str(name_raw))
                _an = normalize_text(attr_stripped)
                if not _nn or not _an:
                    continue
                out.append((cat, sub, cls, name_raw, attr_stripped, bc or None, internal_ref))
                continue

            name_raw = row.get(name_col)
            attr_raw = row.get(attr_col)
            name_n = normalize_text(_cell_str(name_raw))
            attr_stripped = _cell_str(attr_raw)
            attr_n = normalize_text(attr_stripped)
            if not name_n or not attr_n:
                continue
            cat = normalize_text(raw_cat)
            sub = normalize_text(raw_sub)
            cls = normalize_text(_cell_str(row.get(cls_col)) if cls_col else '')
            bc = _cell_str(row.get(bc_col)) if bc_col else ''
            internal_ref = _sanitize_variant_code_from_import(raw_ref) if raw_ref else None
            out.append((cat, sub, cls, name_raw, attr_stripped, bc or None, internal_ref))
        return out

    bio.seek(0)
    df = pd.read_excel(bio, sheet_name=sheet, header=None, engine='openpyxl')
    out = []
    for _, row in df.iterrows():
        if row.isna().all():
            continue
        raw_a = row.iloc[0] if len(row) > 0 else ''
        raw_b = row.iloc[1] if len(row) > 1 else ''
        raw_c = row.iloc[2] if len(row) > 2 else ''
        raw_d = row.iloc[3] if len(row) > 3 else ''
        raw_e = row.iloc[4] if len(row) > 4 else ''
        raw_f = row.iloc[5] if len(row) > 5 else ''

        # Seis columnas: A tipo/clase de ítem, B categoría, C sub, D hueco o código corto, E nombre, F presentación.
        # El modo clásico A–E pondría el nombre en D y deja categoría/sub fuera; este formato es frecuente en catálogos LIMPIEZA / TC / nombre largo / medida.
        if len(row) >= 6:
            d_txt = _cell_str(raw_d).strip()
            e_txt = _cell_str(raw_e).strip()
            f_txt = _cell_str(raw_f).strip()
            if len(e_txt) >= 8 and len(f_txt) >= 1:
                d_blankish = (not d_txt) or d_txt in ('—', '-', 'N/A', 'NA', '.')
                d_short_code = len(d_txt) <= 4 and not re.search(r'\s', d_txt)
                if d_blankish or d_short_code:
                    cat = normalize_text(_cell_str(raw_b))
                    sub = normalize_text(_cell_str(raw_c))
                    cls = normalize_text(_cell_str(raw_a))
                    name_n = normalize_text(e_txt)
                    attr_n = normalize_text(f_txt)
                    if name_n and attr_n:
                        out.append((cat, sub, cls, raw_e, f_txt, None, None))
                        continue

        layout = _detect_fixed_layout(raw_a, raw_b, raw_c, raw_d, raw_e)
        if layout == 'code_name':
            internal_ref = _sanitize_variant_code_from_import(raw_a)
            name_raw = raw_b
            cls = normalize_text(raw_c)
            attr_stripped = _cell_str(raw_e)
            cat = ''
            sub = ''
            name_n = normalize_text(_cell_str(name_raw))
            attr_n = normalize_text(attr_stripped)
            if not name_n or not attr_n:
                continue
            out.append((cat, sub, cls, name_raw, attr_stripped, None, internal_ref))
            continue
        cat = normalize_text(raw_a)
        sub = normalize_text(raw_b)
        cls = normalize_text(raw_c)
        name_raw = raw_d
        attr_raw = raw_e
        name_n = normalize_text(_cell_str(name_raw))
        attr_stripped = _cell_str(attr_raw)
        attr_n = normalize_text(attr_stripped)
        if not name_n or not attr_n:
            continue
        out.append((cat, sub, cls, name_raw, attr_stripped, None, None))
    return out


def import_xlsx_bytes(raw: bytes, filename: str, organization_id: int, user_id: int | None) -> dict[str, Any]:
    """Importa catálogo desde XLS/XLSX (cabeceras tipo Odoo o columnas fijas A–E)."""
    try:
        import pandas as pd  # noqa: F401
    except ImportError as e:
        raise RuntimeError('pandas es requerido para importar') from e

    rows_iter = _rows_from_excel(raw)
    return _execute_catalog_import(rows_iter, organization_id, filename)


def search_variants(
    organization_id: int,
    q: str,
    limit: int = 12,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Búsqueda rápida tipo many2one (solo lectura del catálogo).
    Devuelve items + has_more para paginar como en Odoo («Buscar más»).
    """
    term = (q or '').strip()
    if len(term) < 2:
        return {'items': [], 'has_more': False}
    like = f'%{term}%'
    limit = max(1, min(int(limit), 80))
    offset = max(0, int(offset))
    fetch = limit + 1

    base = (
        db.session.query(ContadorProductVariant, ContadorProductTemplate)
        .join(ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id)
        .filter(ContadorProductVariant.organization_id == organization_id)
        .filter(ContadorProductVariant.is_active.is_(True))
        .filter(
            or_(
                ContadorProductTemplate.name.ilike(like),
                ContadorProductVariant.attribute_value.ilike(like),
                ContadorProductVariant.display_name.ilike(like),
                ContadorProductVariant.code.ilike(like),
                func.coalesce(ContadorProductVariant.barcode, '').ilike(like),
                ContadorProductTemplate.category.ilike(like),
                ContadorProductTemplate.subcategory.ilike(like),
                ContadorProductTemplate.product_class.ilike(like),
            )
        )
        .order_by(ContadorProductVariant.display_name.asc())
    )

    rows = base.offset(offset).limit(fetch).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    out: list[dict[str, Any]] = []
    for v, t in rows:
        out.append(
            {
                'variant_id': v.id,
                'code': v.code,
                'template_name': t.name,
                'attribute_name': v.attribute_name,
                'attribute_value': v.attribute_value,
                'display_name': v.display_name,
                'category': t.category,
                'subcategory': t.subcategory,
                'product_class': t.product_class,
                'barcode': v.barcode or '',
            }
        )
    return {'items': out, 'has_more': has_more}


def purge_organization_contador_data(organization_id: int) -> dict[str, int]:
    """
    Elimina todo el módulo Contador para una organización: sesiones, líneas,
    logs de captura/exportación, variantes y plantillas (irreversible).
    """
    oid = int(organization_id)
    n_log = ContadorCaptureLog.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    n_exp = ContadorExportLog.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    n_line = ContadorCountLine.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    n_sess = ContadorSession.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    n_var = ContadorProductVariant.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    n_tpl = ContadorProductTemplate.query.filter_by(organization_id=oid).delete(synchronize_session=False)
    db.session.commit()
    return {
        'capture_logs': n_log,
        'export_logs': n_exp,
        'lines': n_line,
        'sessions': n_sess,
        'variants': n_var,
        'templates': n_tpl,
    }


def purge_all_contador_organizations() -> dict[str, Any]:
    """Purga Contador para cada organization_id que aún tenga filas en cualquier tabla."""
    org_ids: set[int] = set()
    for model in (
        ContadorCaptureLog,
        ContadorExportLog,
        ContadorCountLine,
        ContadorSession,
        ContadorProductVariant,
        ContadorProductTemplate,
    ):
        for row in db.session.query(model.organization_id).distinct():
            oid = row[0]
            if oid is not None:
                org_ids.add(int(oid))
    total: dict[str, int] = {}
    for oid in sorted(org_ids):
        part = purge_organization_contador_data(oid)
        for k, v in part.items():
            total[k] = total.get(k, 0) + v
    total['organizations'] = len(org_ids)
    return total


def create_session(
    organization_id: int, name: str, description: str | None, user_id: int | None
) -> ContadorSession:
    s = ContadorSession(
        organization_id=organization_id,
        name=name.strip()[:200],
        description=(description or '').strip() or None,
        status='draft',
        created_by=user_id,
    )
    db.session.add(s)
    db.session.commit()
    return s


def open_session(session_id: int, organization_id: int) -> ContadorSession:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'draft':
        raise ValueError('Solo se puede abrir una sesión en borrador')
    variants = ContadorProductVariant.query.filter_by(organization_id=organization_id, is_active=True).all()
    if not variants:
        raise ValueError('No hay variantes activas en el catálogo; importá un XLS primero')
    existing_ids = {lid for (lid,) in db.session.query(ContadorCountLine.variant_id).filter_by(session_id=s.id).all()}
    for v in variants:
        if v.id in existing_ids:
            continue
        db.session.add(
            ContadorCountLine(
                organization_id=organization_id,
                session_id=s.id,
                variant_id=v.id,
                counted_qty=None,
                status='pending',
            )
        )
    s.status = 'open'
    s.opened_at = datetime.utcnow()
    db.session.commit()
    return s


def close_session(session_id: int, organization_id: int) -> ContadorSession:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'open':
        raise ValueError('Solo se puede cerrar una sesión abierta')
    s.status = 'closed'
    s.closed_at = datetime.utcnow()
    db.session.commit()
    return s


def delete_session_if_draft(session_id: int, organization_id: int) -> None:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'draft':
        raise ValueError('Solo se pueden eliminar sesiones en borrador')
    db.session.delete(s)
    db.session.commit()


def _qty_equal(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def _append_log(
    organization_id: int,
    session_id: int,
    line_id: int,
    variant_id: int,
    old_qty: float | int | None,
    new_qty: float | int | None,
    action: str,
    user_id: int | None,
) -> None:
    db.session.add(
        ContadorCaptureLog(
            organization_id=organization_id,
            session_id=session_id,
            line_id=line_id,
            variant_id=variant_id,
            old_qty=old_qty,
            new_qty=new_qty,
            action=action,
            user_id=user_id,
        )
    )


def capture_quantity(
    session_id: int,
    variant_id: int,
    qty: float | int,
    organization_id: int,
    user_id: int | None,
    *,
    operator_restrict_own: bool = False,
) -> ContadorCountLine:
    qty_f = float(qty)
    if qty_f < 0:
        raise ValueError('La cantidad no puede ser negativa')
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'open':
        raise ValueError('La sesión no está abierta para captura')

    line = ContadorCountLine.query.filter_by(session_id=session_id, variant_id=variant_id).first_or_404()

    if operator_restrict_own and line.counted_by is not None and line.counted_by != user_id:
        raise PermissionError('Solo podés editar tus propios conteos')

    old = line.counted_qty
    action = 'update' if old is not None else 'create'
    line.counted_qty = qty_f
    line.counted_by = user_id
    line.counted_at = datetime.utcnow()
    line.status = 'counted'

    _append_log(organization_id, session_id, line.id, variant_id, old, qty_f, action, user_id)
    db.session.commit()
    return line


def review_line(
    session_id: int,
    variant_id: int,
    qty: float | int | None,
    mark_reviewed: bool,
    notes: str | None,
    organization_id: int,
    user_id: int | None,
) -> ContadorCountLine:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status not in ('open', 'closed'):
        raise ValueError('Sesión no válida para revisión')

    line = ContadorCountLine.query.filter_by(session_id=session_id, variant_id=variant_id).first_or_404()
    old = line.counted_qty
    if qty is not None:
        qf = float(qty)
        if qf < 0:
            raise ValueError('La cantidad no puede ser negativa')
        line.counted_qty = qf
        _append_log(organization_id, session_id, line.id, variant_id, old, qf, 'review', user_id)
        if not mark_reviewed:
            line.status = 'counted'
    if mark_reviewed:
        line.status = 'reviewed'
        line.reviewed_by = user_id
        line.reviewed_at = datetime.utcnow()
    if notes is not None:
        line.notes = notes[:2000]
    db.session.commit()
    return line


def session_lines_for_detail(session_id: int, organization_id: int) -> list[dict[str, Any]]:
    """Filas para la vista tipo lista de sesión (sin columna diferencia; fechas solo calendario)."""
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    rows = (
        db.session.query(ContadorCountLine, ContadorProductVariant, ContadorProductTemplate)
        .join(ContadorProductVariant, ContadorProductVariant.id == ContadorCountLine.variant_id)
        .join(ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id)
        .filter(ContadorCountLine.session_id == session_id)
        .order_by(ContadorProductVariant.display_name.asc())
        .all()
    )

    from models.users import User

    def fmt_day(dt):
        if dt is None:
            return '—'
        return dt.strftime('%d/%m/%Y')

    out: list[dict[str, Any]] = []
    for line, v, _t in rows:
        u = User.query.get(line.counted_by) if line.counted_by else None
        ref_dt = line.counted_at or line.updated_at or s.opened_at or s.created_at
        out.append(
            {
                'line_id': line.id,
                'variant_id': v.id,
                'product_label': v.display_name or v.code,
                'counted_qty': line.counted_qty,
                'fecha_day': fmt_day(ref_dt),
                'usuario_label': (u.email if u else '') or '—',
            }
        )
    return out


def _product_and_presentation_labels(t: ContadorProductTemplate, v: ContadorProductVariant) -> tuple[str, str]:
    """
    Columnas Producto / Presentación: prioriza display_name \"Nombre - Presentación\"
    (como se arma en import); si la plantilla tiene basura tipo UND/BIENES, el split corrige.
    """
    dn = (v.display_name or '').strip()
    if ' - ' in dn:
        left, right = dn.split(' - ', 1)
        product = (left or '').strip() or ((t.name or '').strip() or '—')
        presentation = (right or '').strip() or ((v.attribute_value or '').strip() or '—')
        return product, presentation
    product = ((t.name or '').strip() or dn or '—')
    presentation = ((v.attribute_value or '').strip() or '—')
    return product, presentation


def list_session_lines_for_capture(
    session_id: int,
    organization_id: int,
    *,
    page: int = 1,
    per_page: int = 10,
    q: str | None = None,
    filtro: str = 'all',
) -> tuple[list[dict[str, Any]], ContadorSession, int]:
    """
    Filas para la grilla de captura con paginación y filtros en servidor.
    filtro: all | pend (sin cantidad) | done (con cantidad).
    Devuelve (filas, sesión, total coincidentes).
    """
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()

    base = (
        db.session.query(ContadorCountLine, ContadorProductVariant, ContadorProductTemplate)
        .join(ContadorProductVariant, ContadorProductVariant.id == ContadorCountLine.variant_id)
        .join(ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id)
        .filter(ContadorCountLine.session_id == session_id)
    )

    fv = (filtro or 'all').strip().lower()
    if fv == 'pend':
        base = base.filter(ContadorCountLine.counted_qty.is_(None))
    elif fv == 'done':
        base = base.filter(ContadorCountLine.counted_qty.isnot(None))

    term = (q or '').strip()
    if term:
        like = f'%{term}%'
        base = base.filter(
            or_(
                ContadorProductTemplate.name.ilike(like),
                ContadorProductVariant.display_name.ilike(like),
                ContadorProductVariant.attribute_value.ilike(like),
                ContadorProductVariant.code.ilike(like),
                func.coalesce(ContadorProductVariant.barcode, '').ilike(like),
                ContadorProductTemplate.category.ilike(like),
                ContadorProductTemplate.subcategory.ilike(like),
                ContadorProductTemplate.product_class.ilike(like),
            )
        )

    total = base.count()

    pg = max(1, int(page))
    pp = max(1, min(int(per_page), 100))

    rows = (
        base.order_by(
            ContadorProductTemplate.category.asc(),
            ContadorProductTemplate.subcategory.asc(),
            ContadorProductTemplate.name.asc(),
            ContadorProductVariant.attribute_value.asc(),
        )
        .offset((pg - 1) * pp)
        .limit(pp)
        .all()
    )

    from models.users import User

    out: list[dict[str, Any]] = []
    for line, v, t in rows:
        u = User.query.get(line.counted_by) if line.counted_by else None
        if u:
            nm = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip()
            user_disp = nm or (u.email or '')
        else:
            user_disp = None
        product_name, presentation = _product_and_presentation_labels(t, v)
        blob_parts = [
            product_name,
            presentation,
            (t.name or ''),
            (v.attribute_value or ''),
            (v.display_name or ''),
            (v.code or ''),
            (v.barcode or ''),
            (t.category or ''),
            (t.subcategory or ''),
            (t.product_class or ''),
        ]
        search_blob = ' '.join(blob_parts).lower()
        out.append(
            {
                'line_id': line.id,
                'variant_id': v.id,
                'product_name': product_name,
                'presentation': presentation,
                'display_name': v.display_name,
                'counted_qty': line.counted_qty,
                'status': line.status,
                'user_label': user_disp,
                'search_blob': search_blob,
            }
        )
    return out, s, total


def format_last_capture_label(summary: dict[str, Any] | None) -> str | None:
    """Etiqueta DD/MM/YYYY HH:MM para encabezado de captura."""
    if not summary:
        return None
    raw = summary.get('last_capture_at')
    if not raw:
        return None
    try:
        s = str(raw).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(raw)[:16]


def capture_bulk(
    session_id: int,
    organization_id: int,
    user_id: int | None,
    lines_payload: list[dict[str, Any]],
    *,
    operator_restrict_own: bool = False,
) -> int:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    if s.status != 'open':
        raise ValueError('La sesión no está abierta para captura')
    updated = 0
    for item in lines_payload:
        lid = int(item.get('line_id') or 0)
        if not lid:
            continue
        line = ContadorCountLine.query.filter_by(
            id=lid, session_id=session_id, organization_id=organization_id
        ).first()
        if line is None:
            raise ValueError(f'Línea no encontrada: {lid}')
        raw = item.get('counted_qty')
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ''):
            new_val = None
        else:
            try:
                new_val = float(raw)
            except (TypeError, ValueError) as e:
                raise ValueError(f'Cantidad inválida en línea {lid}') from e
        if new_val is not None and new_val < 0:
            raise ValueError('Cantidad negativa no permitida')
        if operator_restrict_own and line.counted_by is not None and line.counted_by != user_id:
            raise PermissionError(
                'Solo podés editar líneas que vos capturaste (operador).'
            )
        old = line.counted_qty
        if _qty_equal(old, new_val):
            continue
        if new_val is None:
            line.counted_qty = None
            line.status = 'pending'
            line.counted_by = None
            line.counted_at = None
        else:
            line.counted_qty = new_val
            line.status = 'counted'
            line.counted_by = user_id
            line.counted_at = datetime.utcnow()
        _append_log(
            organization_id,
            session_id,
            line.id,
            line.variant_id,
            old,
            new_val,
            'update',
            user_id,
        )
        updated += 1
    db.session.commit()
    return updated


def session_summary(session_id: int, organization_id: int) -> dict[str, Any]:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    total = ContadorCountLine.query.filter_by(session_id=session_id).count()
    pending = ContadorCountLine.query.filter_by(session_id=session_id, status='pending').count()
    counted = ContadorCountLine.query.filter_by(session_id=session_id, status='counted').count()
    reviewed = ContadorCountLine.query.filter_by(session_id=session_id, status='reviewed').count()
    void = ContadorCountLine.query.filter_by(session_id=session_id, status='void').count()
    done = (
        ContadorCountLine.query.filter(
            ContadorCountLine.session_id == session_id,
            ContadorCountLine.status.in_(('counted', 'reviewed')),
        ).count()
    )
    last = (
        db.session.query(func.max(ContadorCountLine.counted_at))
        .filter(ContadorCountLine.session_id == session_id)
        .scalar()
    )
    ops = (
        db.session.query(func.count(func.distinct(ContadorCountLine.counted_by)))
        .filter(ContadorCountLine.session_id == session_id, ContadorCountLine.counted_by.isnot(None))
        .scalar()
    )
    pct = round(done * 100.0 / total, 1) if total else 0.0
    with_qty = (
        ContadorCountLine.query.filter(
            ContadorCountLine.session_id == session_id,
            ContadorCountLine.counted_qty.isnot(None),
        ).count()
    )
    return {
        'session_id': s.id,
        'status': s.status,
        'total_lines': total,
        'pending': pending,
        'counted': counted,
        'reviewed': reviewed,
        'void': void,
        'progress_pct': pct,
        'lines_with_qty': int(with_qty),
        'last_capture_at': last.isoformat() if last else None,
        'distinct_operators': int(ops or 0),
    }


def export_rows(session_id: int, organization_id: int) -> list[dict[str, Any]]:
    s = ContadorSession.query.filter_by(id=session_id, organization_id=organization_id).first_or_404()
    rows = db.session.query(ContadorCountLine, ContadorProductVariant, ContadorProductTemplate).join(
        ContadorProductVariant, ContadorProductVariant.id == ContadorCountLine.variant_id
    ).join(
        ContadorProductTemplate, ContadorProductTemplate.id == ContadorProductVariant.template_id
    ).filter(ContadorCountLine.session_id == session_id).order_by(ContadorProductVariant.display_name.asc()).all()

    from models.users import User

    out = []
    for line, v, t in rows:
        cu = User.query.get(line.counted_by) if line.counted_by else None
        ru = User.query.get(line.reviewed_by) if line.reviewed_by else None
        out.append(
            {
                'session_name': s.name,
                'code': v.code,
                'barcode': v.barcode or '',
                'category': t.category,
                'subcategory': t.subcategory,
                'product_class': t.product_class,
                'product_name': t.name,
                'attribute_name': v.attribute_name,
                'attribute_value': v.attribute_value,
                'display_name': v.display_name,
                'counted_qty': line.counted_qty,
                'status': line.status,
                'counted_by_email': (cu.email if cu else ''),
                'counted_at': line.counted_at.strftime('%Y-%m-%d %H:%M') if line.counted_at else '',
                'reviewed_by_email': (ru.email if ru else ''),
                'reviewed_at': line.reviewed_at.strftime('%Y-%m-%d %H:%M') if line.reviewed_at else '',
                'notes': line.notes or '',
            }
        )
    return out


def build_export_xlsx(rows: list[dict[str, Any]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = 'conteo'
    headers = list(rows[0].keys()) if rows else [
        'session_name',
        'code',
        'barcode',
        'category',
        'subcategory',
        'product_class',
        'product_name',
        'attribute_name',
        'attribute_value',
        'display_name',
        'counted_qty',
        'status',
        'counted_by_email',
        'counted_at',
        'reviewed_by_email',
        'reviewed_at',
        'notes',
    ]
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, '') for h in headers])
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def build_export_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        headers = [
            'session_name',
            'code',
            'barcode',
            'category',
            'subcategory',
            'product_class',
            'product_name',
            'attribute_name',
            'attribute_value',
            'display_name',
            'counted_qty',
            'status',
            'counted_by_email',
            'counted_at',
            'reviewed_by_email',
            'reviewed_at',
            'notes',
        ]
    else:
        headers = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in headers})
    return buf.getvalue().encode('utf-8-sig')


def log_export(
    organization_id: int,
    session_id: int,
    export_type: str,
    filename: str | None,
    status: str,
    message: str | None,
    user_id: int | None,
) -> None:
    db.session.add(
        ContadorExportLog(
            organization_id=organization_id,
            session_id=session_id,
            export_type=export_type,
            filename=filename,
            target_name=None,
            status=status,
            message=message,
            created_by=user_id,
        )
    )
    db.session.commit()
