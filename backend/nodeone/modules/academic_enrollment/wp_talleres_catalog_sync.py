"""Sincronización sección Talleres IIUS: WP ↔ AcademicProgram (patrón Cursos de Arte).

Pull: pág. WP 2233 (legacy, puede estar en papelera) — solo lectura de tarjetas por posición.
Push: pág. WP 2006 solo si el bloque «Talleres» ya existe (no se crea ni clona desde Apps).

Matching por posición 1–4 y catálogo de títulos; no por slug del botón WP.
"""
from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from html import unescape
from typing import Any

from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
    _apps_public_base,
    _patch_image_widget,
    _run_wp_cli,
    _strip_html,
    _walk_nodes,
)

TALLERES_CATEGORY = 'Talleres'
TALLERES_SECTION_HEADINGS: frozenset[str] = frozenset(('Talleres', 'Catálogo de Talleres'))
TALLERES_CONTAINER_IDS: frozenset[str] = frozenset(
    ('talleres', 'catalogo_talleres', 'talleres_grid', 'cursos_talleres')
)

WP_CURSOS_PAGE_ID = 2006
WP_TALLERES_SOURCE_PAGE_ID = 2233

# Orden visual en /cursos-detalle/ (bloque Talleres en pág. 2006). No usar orden WP 2233.
TALLERES_VISUAL_ORDER: tuple[str, ...] = (
    'taller-de-aprendizaje-practico',
    'taller-de-creatividad-e-innovacion',
    'taller-de-desarrollo-humano',
    'taller-de-liderazgo-y-comunicacion',
)

TALLERES_WP_TITLE_PULL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        'wp_title': 'Aprendizaje Práctico',
        'canonical_slug': 'taller-de-aprendizaje-practico',
        'image_stems': ('chatgpt-image-19-may-2026-21_51_22', 'collagemapas', 'talleres'),
        'title_keys': (
            'aprendizaje práctico',
            'aprendizaje practico',
            'desarrolla habilidades',
            'habilidades aplicadas',
        ),
    },
    {
        'wp_title': 'Creatividad e Innovación',
        'canonical_slug': 'taller-de-creatividad-e-innovacion',
        'image_stems': ('chatgpt-image-19-may-2026-21_55_28', 'creatividadvak', 'creatividad'),
        'title_keys': ('creatividad e innovación', 'creatividad e innovacion', 'pensamiento creativo'),
    },
    {
        'wp_title': 'Desarrollo Humano',
        'canonical_slug': 'taller-de-desarrollo-humano',
        'image_stems': ('chatgpt-image-19-may-2026-21_57_45', 'eldr'),
        'title_keys': ('desarrollo humano', 'crecimiento integral'),
    },
    {
        'wp_title': 'Liderazgo y Comunicación',
        'canonical_slug': 'taller-de-liderazgo-y-comunicacion',
        'image_stems': ('chatgpt-image-19-may-2026-22_01_31', 'liderasgo-organizacional'),
        'title_keys': ('liderazgo y comunicación', 'liderazgo y comunicacion'),
    },
)

WP_TALLERES_PUSH_SLUGS: frozenset[str] = frozenset(
    entry['canonical_slug'] for entry in TALLERES_WP_TITLE_PULL_CATALOG
)

TALLERES_PULL_PROTECTED_FIELDS: frozenset[str] = frozenset(
    ('image_url', 'flyer_url', 'price_from', 'status')
)
TALLERES_PULL_ALLOWED_FIELDS: frozenset[str] = frozenset(
    ('name', 'slug', 'category', 'short_description', 'image_wp_landing', 'program_type')
)
TALLERES_PULL_PROTECTED_LABELS: tuple[str, ...] = (
    'image_url',
    'flyer_url',
    'planes de pago',
    'price_from',
    'status',
)

# Slugs legacy (botones WP / taller-*) → canónico taller-de-* publicado en Apps.
TALLERES_SLUG_LEGACY: dict[str, str] = {
    'taller-aprendizaje-practico': 'taller-de-aprendizaje-practico',
    'taller-liderazgo-y-comunicacion': 'taller-de-liderazgo-y-comunicacion',
    'diplomado-en-creatividad-y-expresion-artistica-aplicada': 'taller-de-creatividad-e-innovacion',
    'curso-en-creatividad-y-expresion-artistica-aplicada': 'taller-de-creatividad-e-innovacion',
    'taller-desarrollo-humano': 'taller-de-desarrollo-humano',
    'taller-fundamentos-coaching-ejecutivo': 'taller-de-aprendizaje-practico',
}


def canonical_talleres_slug(slug: str | None) -> str | None:
    s = (slug or '').strip().lower()
    if not s:
        return None
    return TALLERES_SLUG_LEGACY.get(s, s)


def is_wp_talleres_push_slug(slug: str | None) -> bool:
    return (slug or '').strip().lower() in WP_TALLERES_PUSH_SLUGS


def wp_sync_target_for_slug(slug: str | None) -> str | None:
    return 'talleres' if is_wp_talleres_push_slug(slug) else None


def _normalize_element_id(raw: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (raw or '').strip().lower()).strip('_')


def _slug_from_inscripcion_url(url: str | None) -> str | None:
    if not url or '/inscripcion/' not in url:
        return None
    raw = url.split('/inscripcion/')[-1].split('?')[0].strip('/').lower()
    return canonical_talleres_slug(raw) or raw


def _inscripcion_url(slug: str) -> str:
    return f'{_apps_public_base()}/inscripcion/{slug.strip().lower()}'


def _node_settings(node: dict) -> dict:
    st = node.get('settings')
    if not isinstance(st, dict):
        st = {}
        node['settings'] = st
    return st


def _load_elementor_data(page_id: int) -> list:
    proc = _run_wp_cli(['post', 'meta', 'get', str(page_id), '_elementor_data'])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli falló')
    raw = (proc.stdout or '').strip()
    if not raw or raw == '[]':
        return []
    return json.loads(raw)


def _save_elementor_data(page_id: int, data: list) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    proc = _run_wp_cli(['post', 'meta', 'update', str(page_id), '_elementor_data', payload])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli update falló')
    _run_wp_cli(['elementor', 'flush-css'])


def _image_stem(url: str) -> str:
    if not url:
        return ''
    fn = url.rsplit('/', 1)[-1].lower()
    return re.sub(r'\.[a-z0-9]+$', '', fn)


def _canonical_slug_from_talleres_card(plain: str | None, img_url: str | None) -> str | None:
    """Empareja tarjeta WP por imagen y título visible; no por índice DOM ni slug legacy del botón."""
    low = (plain or '').lower()
    stem = _image_stem(img_url or '')
    for entry in TALLERES_WP_TITLE_PULL_CATALOG:
        for key in entry.get('image_stems') or ():
            if key in stem:
                return entry['canonical_slug']
    for entry in TALLERES_WP_TITLE_PULL_CATALOG:
        for key in entry.get('title_keys') or ():
            if key in low:
                return entry['canonical_slug']
    return None


def _card_from_talleres_container(root_el: dict) -> _WpTalleresCatalogCard | None:
    sub_flat: list[dict] = []
    _walk_nodes([root_el], sub_flat)
    img_n = txt_n = btn_n = None
    plain = ''
    img_url = ''
    btn_slug = None
    for sn in sub_flat:
        swt = sn.get('widgetType') or ''
        sst = _node_settings(sn)
        if swt == 'image':
            url = (sst.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                img_n, img_url = sn, url
        elif swt == 'text-editor':
            p = _strip_html(sst.get('editor') or '')
            if p and len(p) > len(plain):
                plain, txt_n = p, sn
        elif swt == 'button':
            btn_n = sn
            btn_slug = _slug_from_inscripcion_url((sst.get('link') or {}).get('url') or '')
    canonical = _canonical_slug_from_talleres_card(plain, img_url)
    if not canonical or not btn_n:
        return None
    return _WpTalleresCatalogCard(
        slot=0,
        slug=canonical,
        text_node=txt_n,
        image_node=img_n,
        button_node=btn_n,
        pull_short_plain=plain or None,
        pull_image_url=img_url or None,
        pull_button_slug=btn_slug,
        pull_cta_label=(_node_settings(btn_n).get('text') or '').strip() or None,
    )


def _order_talleres_cards(cards: list[_WpTalleresCatalogCard]) -> list[_WpTalleresCatalogCard]:
    by_slug = {c.slug: c for c in cards}
    ordered: list[_WpTalleresCatalogCard] = []
    for vis_i, slug in enumerate(TALLERES_VISUAL_ORDER, 1):
        c = by_slug.get(slug)
        if c is not None:
            c.slot = vis_i
            ordered.append(c)
    return ordered


def _short_from_card_plain(plain: str) -> str:
    s = (plain or '').strip().lstrip('💡').strip()
    if ':' in s:
        s = s.split(':', 1)[1].strip()
    return s[:500] if s else ''


def _regen_element_ids(node: dict) -> None:
    if isinstance(node, dict):
        if node.get('id'):
            node['id'] = secrets.token_hex(4)
        for ch in node.get('elements') or []:
            if isinstance(ch, dict):
                _regen_element_ids(ch)
    elif isinstance(node, list):
        for x in node:
            if isinstance(x, dict):
                _regen_element_ids(x)


@dataclass
class _WpTalleresCatalogCard:
    slot: int
    slug: str
    text_node: dict | None = None
    image_node: dict | None = None
    button_node: dict | None = None
    pull_short_plain: str | None = None
    pull_image_url: str | None = None
    pull_button_slug: str | None = None
    pull_cta_label: str | None = None

    def apply_program(self, program, *, media_base: str) -> None:
        from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

        if self.text_node and program.short_description:
            plain = (program.short_description or '').strip()
            if plain:
                _node_settings(self.text_node)['editor'] = f'<p>{plain}</p>'

        img_path = (program.image_url or program.image_wp_landing or '').strip()
        img_url = absolute_public_asset_url(img_path, external_base=media_base) if img_path else None
        if img_url and self.image_node and '_qr' not in img_url.lower():
            _patch_image_widget(self.image_node, img_url)

        if self.button_node:
            st = _node_settings(self.button_node)
            if program.cta_label:
                st['text'] = program.cta_label
            link = st.get('link')
            if not isinstance(link, dict):
                link = {}
                st['link'] = link
            apps_slug = (program.slug or self.slug or '').strip().lower()
            link['url'] = _inscripcion_url(apps_slug)


def _index_talleres_catalog_cards(data: list) -> tuple[list[_WpTalleresCatalogCard], list[str]]:
    notes: list[str] = []
    iius_cards: list[_WpTalleresCatalogCard] = []
    for root in data:
        if root.get('elType') != 'container':
            continue
        eid = _normalize_element_id((root.get('settings') or {}).get('_element_id'))
        if eid != 'talleres_iius_card':
            continue
        card = _card_from_talleres_container(root)
        if card:
            iius_cards.append(card)
    if len(iius_cards) >= len(TALLERES_VISUAL_ORDER):
        notes.append('Indexadas 4 tarjetas en contenedores talleres_iius_card (bloque canónico).')
        return _order_talleres_cards(iius_cards), notes

    flat: list[dict] = []
    _walk_nodes(data, flat)

    in_sec = False
    slot = 0
    pending_image: tuple[dict, str] | None = None
    pending_text: tuple[dict, str] | None = None
    cards: list[_WpTalleresCatalogCard] = []
    notes.append('Fallback: indexación por sección Talleres (sin contenedores talleres_iius_card).')

    def _enter() -> None:
        nonlocal in_sec, slot, pending_image, pending_text
        in_sec = True
        slot = 0
        pending_image = pending_text = None

    def _leave() -> None:
        nonlocal in_sec, slot, pending_image, pending_text
        in_sec = False
        slot = 0
        pending_image = pending_text = None

    def flush(button_node: dict, btn_slug: str | None) -> None:
        nonlocal pending_image, pending_text, slot
        if not in_sec:
            pending_image = pending_text = None
            return
        img_url = pending_image[1] if pending_image else None
        plain = pending_text[1] if pending_text else ''
        canonical = _canonical_slug_from_talleres_card(plain, img_url)
        if not canonical:
            notes.append(f'Talleres tarjeta {slot + 1}: sin match de título/imagen; omitida.')
            pending_image = pending_text = None
            slot += 1
            return
        if btn_slug and btn_slug != canonical:
            notes.append(
                f'Talleres DOM {slot + 1}: botón WP «{btn_slug}» → push «{canonical}» (por título visible).'
            )
        cards.append(
            _WpTalleresCatalogCard(
                slot=0,
                slug=canonical,
                text_node=pending_text[0] if pending_text else None,
                image_node=pending_image[0] if pending_image else None,
                button_node=button_node,
                pull_short_plain=plain or None,
                pull_image_url=img_url,
                pull_button_slug=(btn_slug or '').strip().lower() or None,
                pull_cta_label=(_node_settings(button_node).get('text') or '').strip() or None,
            )
        )
        pending_image = pending_text = None
        slot += 1

    leave_titles = frozenset(
        {
            'Catálogo de Cursos y Programas',
            'Cursos de Negocios',
            'Cursos en Ciencia',
            'Cursos en Espiritualidad',
            'Cursos de Arte',
            'Cursos en Arte',
        }
    )

    for node in flat:
        wt = node.get('widgetType') or ''
        el = node.get('elType') or ''
        st = _node_settings(node)
        eid = _normalize_element_id(st.get('_element_id'))

        if el in ('container', 'section') and eid:
            if eid in TALLERES_CONTAINER_IDS or eid in ('catalogo_talleres_iius', 'talleres_iius_card'):
                _enter()
            continue

        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in TALLERES_SECTION_HEADINGS and title == 'Talleres':
                _enter()
            elif in_sec and title in leave_titles:
                _leave()
            continue

        if not in_sec:
            continue
        if wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                pending_image = (node, url)
        elif wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain:
                pending_text = (node, plain)
        elif wt == 'button':
            flush(node, _slug_from_inscripcion_url((st.get('link') or {}).get('url') or ''))

    # Pág. 2233 (legacy): 4 contenedores raíz sin heading «Talleres» en el árbol
    if (
        not cards
        and len(data) >= len(TALLERES_WP_TITLE_PULL_CATALOG)
        and len(data) <= 6
    ):
        for i, root_el in enumerate(data[: len(TALLERES_WP_TITLE_PULL_CATALOG)]):
            if root_el.get('elType') != 'container':
                continue
            sub_flat: list[dict] = []
            _walk_nodes([root_el], sub_flat)
            img_n = txt_n = btn_n = None
            plain = ''
            img_url = ''
            btn_slug = None
            for sn in sub_flat:
                swt = sn.get('widgetType') or ''
                sst = _node_settings(sn)
                if swt == 'image':
                    url = (sst.get('image') or {}).get('url') or ''
                    if url and 'uploads' in url:
                        img_n, img_url = sn, url
                elif swt == 'text-editor':
                    p = _strip_html(sst.get('editor') or '')
                    if p and len(p) > len(plain):
                        plain, txt_n = p, sn
                elif swt == 'button':
                    btn_n = sn
                    btn_slug = _slug_from_inscripcion_url((sst.get('link') or {}).get('url') or '')
            canonical = _canonical_slug_from_talleres_card(plain, img_url)
            if canonical and btn_n:
                cards.append(
                    _WpTalleresCatalogCard(
                        slot=0,
                        slug=canonical,
                        text_node=txt_n,
                        image_node=img_n,
                        button_node=btn_n,
                        pull_short_plain=plain or None,
                        pull_image_url=img_url or None,
                        pull_button_slug=btn_slug,
                        pull_cta_label=(_node_settings(btn_n).get('text') or '').strip() if btn_n else None,
                    )
                )
        if cards:
            notes.append('Tarjetas indexadas por contenedores raíz (pág. talleres legacy).')

    return _order_talleres_cards(cards), notes


def _talleres_block_present_on_cursos_page(data: list) -> bool:
    raw = json.dumps(data, ensure_ascii=False).lower()
    return any(f'/inscripcion/{s}' in raw for s in WP_TALLERES_PUSH_SLUGS)


def ensure_talleres_block_on_cursos_page(*, save: bool = True) -> tuple[bool, str]:
    """
    Deshabilitado: no modificar /cursos-detalle/ (WP 2006) desde Apps.
    El bloque Talleres en Elementor lo arma el equipo en WP manualmente.
    """
    del save  # reservado por compatibilidad de scripts; nunca escribe WP
    return False, (
        'Política: no se añade ni clona el bloque Talleres en la página de cursos desde Apps. '
        'Editar Elementor en WordPress manualmente si hace falta.'
    )


def _find_apps_by_canonical(organization_id: int, canonical_slug: str) -> Any | None:
    from models.academic_program import AcademicProgram

    slug = (canonical_slug or '').strip().lower()
    if not slug:
        return None
    return AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()


def _description_from_card(card: _WpTalleresCatalogCard | None) -> str | None:
    if not card or not card.pull_short_plain:
        return None
    return _short_from_card_plain(card.pull_short_plain) or (card.pull_short_plain or '').strip() or None


def _proposed_pull_updates(
    row,
    catalog_entry: dict[str, Any],
    card: _WpTalleresCatalogCard | None,
    *,
    for_create: bool,
) -> dict[str, Any]:
    desc = _description_from_card(card)
    wp_image = (card.pull_image_url if card else None) or None
    proposed: dict[str, Any] = {
        'name': catalog_entry['wp_title'],
        'category': TALLERES_CATEGORY,
        'program_type': 'taller',
        'short_description': desc,
        'image_wp_landing': (wp_image or '').strip() or None,
    }
    if for_create:
        proposed['slug'] = catalog_entry['canonical_slug']
        proposed['_create_status'] = 'draft'

    changes: dict[str, Any] = {}
    for field, new_val in proposed.items():
        if field.startswith('_') or field not in TALLERES_PULL_ALLOWED_FIELDS:
            continue
        if field in TALLERES_PULL_PROTECTED_FIELDS:
            continue
        old_val = getattr(row, field, None) if row is not None else None
        old_s = (old_val if old_val is not None else '')
        if isinstance(old_s, str):
            old_s = old_s.strip()
        new_s = (new_val if new_val is not None else '')
        if isinstance(new_s, str):
            new_s = new_s.strip()
        if old_s != new_s:
            changes[field] = new_val
    return changes


def scan_talleres_wp_title_pull_table(organization_id: int) -> dict[str, Any]:
    """Dry-run pull: lee tarjetas desde WP 2233 (fuente), sin escribir BD."""
    page_data = _load_elementor_data(WP_TALLERES_SOURCE_PAGE_ID)
    wp_cards, notes = _index_talleres_catalog_cards(page_data)
    errors: list[str] = list(notes[:16])
    rows: list[dict[str, Any]] = []

    for i, catalog_entry in enumerate(TALLERES_WP_TITLE_PULL_CATALOG):
        card = wp_cards[i] if i < len(wp_cards) else None
        canonical = catalog_entry['canonical_slug']
        apps_row = _find_apps_by_canonical(int(organization_id), canonical)
        apps_ok = apps_row is not None and (apps_row.category or '').strip() == TALLERES_CATEGORY

        field_updates: dict[str, Any] = {}
        nota: str | None = None
        if card is None:
            action = 'ignorar'
            errors.append(f'WP sin tarjeta en posición {i + 1}: {catalog_entry["wp_title"]}')
        elif apps_row is not None and not apps_ok:
            action = 'ignorar'
            nota = (
                f'Slug «{canonical}» existe (id={apps_row.id}, categoría «{apps_row.category}»). '
                'Resolver manualmente antes de pull.'
            )
            errors.append(nota)
        elif apps_row is None:
            action = 'crear'
            field_updates = _proposed_pull_updates(None, catalog_entry, card, for_create=True)
        elif not _proposed_pull_updates(apps_row, catalog_entry, card, for_create=False):
            action = 'ignorar'
        else:
            action = 'actualizar'
            field_updates = _proposed_pull_updates(apps_row, catalog_entry, card, for_create=False)

        rows.append(
            {
                'position': i + 1,
                'wp_title': catalog_entry['wp_title'],
                'slug_wp': card.pull_button_slug if card else None,
                'canonical_slug': canonical,
                'existe_en_apps': 'sí' if apps_row is not None else 'no',
                'apps_id': int(apps_row.id) if apps_row else None,
                'apps_status': (apps_row.status if apps_row else None),
                'accion_propuesta': action,
                'campos_actualizar': field_updates,
                'campos_protegidos': list(TALLERES_PULL_PROTECTED_LABELS),
                'wp_image_readonly': (card.pull_image_url if card else None),
                'nota': nota,
            }
        )

    push_cards, _ = _index_talleres_catalog_cards(_load_elementor_data(WP_CURSOS_PAGE_ID))
    return {
        'organization_id': int(organization_id),
        'wp_source_page_id': WP_TALLERES_SOURCE_PAGE_ID,
        'wp_push_page_id': WP_CURSOS_PAGE_ID,
        'mode': 'dry_run',
        'wp_cards_found': len(wp_cards),
        'wp_push_cards_found': len(push_cards),
        'rows': rows,
        'errors': errors,
    }


def apply_talleres_wp_title_pull(
    organization_id: int,
    db,
    *,
    dry_run: bool = True,
) -> tuple[int, list[str], dict[str, Any]]:
    report = scan_talleres_wp_title_pull_table(organization_id)
    errors: list[str] = list(report.get('errors') or [])
    created = updated = 0

    if dry_run:
        report['dry_run'] = True
        report['would_create'] = sum(1 for r in report['rows'] if r['accion_propuesta'] == 'crear')
        report['would_update'] = sum(1 for r in report['rows'] if r['accion_propuesta'] == 'actualizar')
        return 0, errors, report

    from models.academic_program import AcademicProgram

    for row_data in report.get('rows') or []:
        action = row_data.get('accion_propuesta')
        if action == 'ignorar':
            continue
        changes = dict(row_data.get('campos_actualizar') or {})
        changes.pop('_create_status', None)

        if action == 'crear':
            slug = changes.pop('slug', None) or row_data.get('canonical_slug')
            if AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first():
                errors.append(f'Ya existe slug {slug}; omitido crear')
                continue
            prog = AcademicProgram(
                organization_id=int(organization_id),
                slug=slug,
                status='draft',
                name=changes.get('name') or row_data.get('wp_title'),
                program_type='taller',
                category=TALLERES_CATEGORY,
                short_description=changes.get('short_description'),
                image_wp_landing=changes.get('image_wp_landing'),
            )
            db.session.add(prog)
            created += 1
        elif action == 'actualizar':
            prog = _find_apps_by_canonical(int(organization_id), row_data.get('canonical_slug') or '')
            if not prog:
                errors.append(f'Sin fila Apps: {row_data.get("wp_title")}')
                continue
            for field, val in changes.items():
                if field in TALLERES_PULL_ALLOWED_FIELDS and field not in TALLERES_PULL_PROTECTED_FIELDS:
                    setattr(prog, field, val)
            updated += 1

    if created or updated:
        db.session.commit()
    report['dry_run'] = False
    report['created'] = created
    report['updated'] = updated
    return created + updated, errors, report


def pull_talleres_from_wp(organization_id: int, db) -> tuple[int, list[str]]:
    n, errs, _ = apply_talleres_wp_title_pull(organization_id, db, dry_run=False)
    return n, errs


class _TalleresElementorPage:
    def __init__(self, data: list | None = None) -> None:
        self.data = data if data is not None else _load_elementor_data(WP_CURSOS_PAGE_ID)
        self.catalog_cards, self.wiring_notes = _index_talleres_catalog_cards(self.data)

    def push_one_catalog_slot(self, program, slot_index: int) -> None:
        if slot_index < 0 or slot_index >= len(self.catalog_cards):
            raise ValueError(f'Posición inválida: {slot_index}')
        self.catalog_cards[slot_index].apply_program(program, media_base=_apps_public_base())
        _save_elementor_data(WP_CURSOS_PAGE_ID, self.data)

    def save(self) -> None:
        _save_elementor_data(WP_CURSOS_PAGE_ID, self.data)


def push_talleres_slug_to_wp(organization_id: int, slug: str) -> tuple[bool, str | None]:
    from models.academic_program import AcademicProgram

    slug = (slug or '').strip().lower()
    page = _TalleresElementorPage()
    slot = next((i for i, c in enumerate(page.catalog_cards) if c.slug == slug), None)
    if slot is None:
        return False, (
            f'Solo los 4 talleres con slug canónico ({", ".join(sorted(WP_TALLERES_PUSH_SLUGS))}).'
        )
    row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
    if not row:
        return False, f'No existe «{slug}» en Apps.'

    page = _TalleresElementorPage()
    slot = next((i for i, c in enumerate(page.catalog_cards) if c.slug == slug), None)
    if slot is None or slot >= len(page.catalog_cards):
        return False, f'No hay tarjeta WP indexada para «{slug}» en /cursos-detalle/.'
    try:
        page.push_one_catalog_slot(row, slot)
    except Exception as e:
        return False, str(e)
    return True, None
