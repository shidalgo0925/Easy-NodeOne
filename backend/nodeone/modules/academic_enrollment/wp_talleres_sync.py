"""Sincronización Cursos de Arte / talleres IIUS: WP pág. 2006 (sección) ↔ AcademicProgram.

Tarjetas en /cursos-detalle/ bajo «Cursos de Arte» (Creatividad + 3 talleres).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from nodeone.modules.academic_enrollment.catalog_public import (
    ARTE_CATEGORY,
    ARTE_SLUGS,
    ARTE_WP_CONTAINER_IDS,
    ARTE_WP_SECTION_TITLES,
)
from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
    _apps_public_base,
    _patch_image_widget,
    _run_wp_cli,
    _strip_html,
    _walk_nodes,
)

WP_CURSOS_PAGE_ID = 2006
ARTE_SECTION_HEADINGS_READ: frozenset[str] = frozenset((*ARTE_WP_SECTION_TITLES, 'Talleres'))
ARTE_CONTAINER_IDS = ARTE_WP_CONTAINER_IDS
CURSO_SECTION_CONTAINER_IDS: frozenset[str] = frozenset(
    ('curso_negocios', 'curso_ciencia', 'cursos_espiritualidad', 'cursos', 'curso')
)

ARTE_SECTION_HEADING = ARTE_CATEGORY
ARTE_SLUGS_BY_ORDER: tuple[str, ...] = ARTE_SLUGS

# Catálogo oficial pull WP → Apps (solo estos 4 títulos, orden en sección «Cursos de Arte»).
# Matching Apps: solo si existe exactamente ``canonical_slug`` (no botón WP ni slugs legacy).
ARTE_WP_TITLE_PULL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        'wp_title': 'Técnicas de Anclaje PNL para Desarrollo Personal y Profesional en el Arte',
        'canonical_slug': 'curso-en-arte-tecnicas-anclaje-pnl',
        'image_stems': ('pnlarte', 'anclaje'),
    },
    {
        'wp_title': 'Creatividad con Visualización VAK',
        'canonical_slug': 'curso-en-creatividad-visualizacion-vak',
        'image_stems': ('creatividadvak', 'vak'),
    },
    {
        'wp_title': 'Arte con Herramientas de Reencuadre PNL',
        'canonical_slug': 'curso-en-arte-herramientas-reencuadre-pnl',
        'image_stems': ('reencuadrespnl', 'reencuadre'),
    },
    {
        'wp_title': 'Arte Collage con Mapas Mentales',
        'canonical_slug': 'curso-en-arte-collage-mapas-mentales',
        'image_stems': ('collagemapas', 'collage'),
    },
)

# Programa Apps previo; no se modifica en pull (decisión manual).
ARTE_APPS_LEGACY_REVIEW_SLUGS: frozenset[str] = frozenset(('curso-en-aprendizaje-practico',))

ARTE_PULL_PROTECTED_FIELDS: frozenset[str] = frozenset(
    ('image_url', 'flyer_url', 'price_from', 'status')
)
ARTE_PULL_PROTECTED_LABELS: tuple[str, ...] = (
    'image_url',
    'flyer_url',
    'planes de pago',
    'price_from',
    'status',
)
ARTE_PULL_ALLOWED_FIELDS: frozenset[str] = frozenset(
    ('name', 'slug', 'category', 'short_description', 'image_wp_landing', 'program_type')
)

# Slugs históricos (taller-*, diplomado-*, botones WP viejos) → slug publicado en Apps.
ARTE_SLUG_LEGACY: dict[str, str] = {
    # taller-* → ver wp_talleres_catalog_sync.TALLERES_SLUG_LEGACY (no mezclar con arte)
    'diplomado-en-creatividad-y-expresion-artistica-aplicada': 'curso-en-creatividad-visualizacion-vak',
    # Botones «Ver más» en WP antes del push (cursos-detalle / Cursos de Arte)
    'curso-en-aprendizaje-practico': 'curso-en-arte-collage-mapas-mentales',
    'curso-en-liderazgo-y-comunicacion': 'curso-en-arte-herramientas-reencuadre-pnl',
    'curso-en-creatividad-y-expresion-artistica-aplicada': 'curso-en-creatividad-visualizacion-vak',
    'curso-en-desarrollo-humano': 'curso-en-arte-herramientas-reencuadre-pnl',
}

_IMAGE_STEM_TO_SLUG: dict[str, str] = {
    'collagemapas': 'curso-en-aprendizaje-practico',
    'talleres': 'curso-en-aprendizaje-practico',
    'chatgpt-image-19-may-2026-21_51_22': 'curso-en-aprendizaje-practico',
    'liderasgo-organizacional': 'curso-en-liderazgo-y-comunicacion',
    'chatgpt-image-19-may-2026-22_01_31': 'curso-en-liderazgo-y-comunicacion',
    'creatividadvak': 'curso-en-creatividad-y-expresion-artistica-aplicada',
    'chatgpt-image-19-may-2026-21_55_28': 'curso-en-creatividad-y-expresion-artistica-aplicada',
    'chatgpt-image-19-may-2026-21_57_45': 'curso-en-desarrollo-humano',
    'creatividad': 'curso-en-creatividad-y-expresion-artistica-aplicada',
    'eldr': 'curso-en-desarrollo-humano',
}

_FORMAL_NAMES: dict[str, str] = {
    'curso-en-arte-tecnicas-anclaje-pnl': (
        'Técnicas de Anclaje PNL para Desarrollo Personal y Profesional en el Arte'
    ),
    'curso-en-creatividad-visualizacion-vak': 'Creatividad con Visualización VAK',
    'curso-en-arte-herramientas-reencuadre-pnl': 'Arte con Herramientas de Reencuadre PNL',
    'curso-en-arte-collage-mapas-mentales': 'Arte Collage con Mapas Mentales',
    # Legacy (solo referencia en mapeos viejos)
    'curso-en-aprendizaje-practico': 'Curso en Aprendizaje Práctico',
    'curso-en-liderazgo-y-comunicacion': 'Curso en Liderazgo y Comunicación',
    'curso-en-creatividad-y-expresion-artistica-aplicada': (
        'Curso en Creatividad y Expresión Artística Aplicada'
    ),
    'curso-en-desarrollo-humano': 'Curso en Desarrollo Humano',
}


def canonical_arte_slug(slug: str | None) -> str | None:
    s = (slug or '').strip().lower()
    if not s:
        return None
    return ARTE_SLUG_LEGACY.get(s, s)

WP_ARTE_SLUGS: frozenset[str] = frozenset(ARTE_SLUGS)
# Slugs Apps con botón «Actualizar WP» (un programa → una tarjeta en Elementor).
WP_ARTE_PUSH_SLUGS: frozenset[str] = frozenset(
    entry['canonical_slug'] for entry in ARTE_WP_TITLE_PULL_CATALOG
)


def is_wp_arte_push_slug(slug: str | None) -> bool:
    """True si este programa puede publicarse en WP (solo los 4 del catálogo por título)."""
    return (slug or '').strip().lower() in WP_ARTE_PUSH_SLUGS


def is_wp_arte_slug(slug: str | None) -> bool:
    """Compat: push por catálogo nuevo; lectura legacy por slug antiguo."""
    return is_wp_arte_push_slug(slug) or canonical_arte_slug(slug) in WP_ARTE_SLUGS


def wp_sync_target_for_slug(slug: str | None) -> str | None:
    return 'arte' if is_wp_arte_push_slug(slug) else None


def _arte_catalog_slot_for_slug(slug: str) -> int | None:
    key = (slug or '').strip().lower()
    for i, entry in enumerate(ARTE_WP_TITLE_PULL_CATALOG):
        if entry['canonical_slug'] == key:
            return i
    return None


def _slug_from_inscripcion_url(url: str | None) -> str | None:
    if not url or '/inscripcion/' not in url:
        return None
    raw = url.split('/inscripcion/')[-1].split('?')[0].strip('/').lower()
    return canonical_arte_slug(raw) or raw


def _slug_from_image_url(url: str | None) -> str | None:
    if not url:
        return None
    fname = url.rsplit('/', 1)[-1].lower()
    stem = re.sub(r'\.[a-z0-9]+$', '', fname, flags=re.I)
    if stem in _IMAGE_STEM_TO_SLUG:
        return _IMAGE_STEM_TO_SLUG[stem]
    for key, slug in sorted(_IMAGE_STEM_TO_SLUG.items(), key=lambda x: -len(x[0])):
        if len(key) >= 5 and key in fname:
            return slug
    return None


def _inscripcion_url(slug: str) -> str:
    return f'{_apps_public_base()}/inscripcion/{slug.strip().lower()}'


def _node_settings(node: dict) -> dict:
    st = node.get('settings')
    if not isinstance(st, dict):
        st = {}
        node['settings'] = st
    return st


def _load_elementor_data() -> list:
    proc = _run_wp_cli(['post', 'meta', 'get', str(WP_CURSOS_PAGE_ID), '_elementor_data'])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli falló')
    raw = (proc.stdout or '').strip()
    if not raw or raw == '[]':
        raise RuntimeError('Elementor vacío en página cursos WP')
    return json.loads(raw)


def _save_elementor_data(data: list) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    proc = _run_wp_cli(
        ['post', 'meta', 'update', str(WP_CURSOS_PAGE_ID), '_elementor_data', payload],
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli update falló')
    _run_wp_cli(['elementor', 'flush-css'])


def _short_from_card_plain(plain: str) -> str:
    s = (plain or '').strip().lstrip('💡').strip()
    if ':' in s:
        return s.split(':', 1)[1].strip()
    return s


@dataclass
class _WpArteCard:
    slug: str
    category: str | None = None
    sort_order: int = 0
    text_node: dict | None = None
    image_node: dict | None = None
    button_node: dict | None = None
    pull_short_plain: str | None = None
    pull_image_url: str | None = None
    pull_cta_label: str | None = None

    def to_pull_block(self) -> dict[str, Any]:
        return {
            'slug': self.slug,
            'name': _FORMAL_NAMES.get(self.slug),
            'category': 'Cursos de Arte',
            'short_description': _short_from_card_plain(self.pull_short_plain or '') or None,
            'image_url': self.pull_image_url,
            'cta_label': self.pull_cta_label,
            'catalog_sort_order': self.sort_order,
        }

    def apply_program(self, program, *, media_base: str) -> None:
        from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

        if self.text_node and program.short_description:
            plain = (program.short_description or '').strip()
            if plain:
                _node_settings(self.text_node)['editor'] = f'<p>{plain}</p>'

        img_path = (program.image_url or '').strip()
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
            link['url'] = _inscripcion_url(program.slug or self.slug)


def _normalize_element_id(raw: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (raw or '').strip().lower()).strip('_')


def _index_arte_cards(data: list) -> tuple[dict[str, _WpArteCard], list[str]]:
    flat: list[dict] = []
    _walk_nodes(data, flat)

    in_arte = False
    arte_slot = 0
    pending_image: tuple[dict, str] | None = None
    pending_text: tuple[dict, str] | None = None
    cards: dict[str, _WpArteCard] = {}
    notes: list[str] = []

    def _enter_arte() -> None:
        nonlocal in_arte, arte_slot, pending_image, pending_text
        in_arte = True
        arte_slot = 0
        pending_image = pending_text = None

    def _leave_arte() -> None:
        nonlocal in_arte, arte_slot, pending_image, pending_text
        in_arte = False
        arte_slot = 0
        pending_image = pending_text = None

    def flush(button_node: dict, btn_slug: str | None) -> None:
        nonlocal pending_image, pending_text, arte_slot
        if not in_arte:
            return
        img_slug = _slug_from_image_url(pending_image[1]) if pending_image else None
        if arte_slot < len(ARTE_SLUGS_BY_ORDER):
            slug = ARTE_SLUGS_BY_ORDER[arte_slot]
            if (btn_slug and btn_slug != slug) or (img_slug and img_slug != slug):
                notes.append(
                    f'Arte: posición {arte_slot + 1} → {slug}'
                    f' (imagen→{img_slug or "—"}, botón→{btn_slug or "—"})'
                )
        else:
            slug = img_slug if img_slug in WP_ARTE_SLUGS else btn_slug
        if not slug or slug not in WP_ARTE_SLUGS:
            pending_image = pending_text = None
            return
        if img_slug and btn_slug and img_slug != btn_slug:
            st = _node_settings(button_node)
            link = st.get('link')
            if not isinstance(link, dict):
                link = {}
                st['link'] = link
            link['url'] = _inscripcion_url(img_slug)
            notes.append(f'Arte: botón {btn_slug} → {img_slug}')

        order = ARTE_SLUGS_BY_ORDER.index(slug) + 1 if slug in ARTE_SLUGS_BY_ORDER else len(cards) + 1
        cards[slug] = _WpArteCard(
            slug=slug,
            category='Cursos de Arte',
            sort_order=order,
            text_node=pending_text[0] if pending_text else None,
            image_node=pending_image[0] if pending_image else None,
            button_node=button_node,
            pull_short_plain=pending_text[1] if pending_text else None,
            pull_image_url=pending_image[1] if pending_image else None,
            pull_cta_label=(_node_settings(button_node).get('text') or '').strip() or None,
        )
        pending_image = pending_text = None
        arte_slot += 1

    for node in flat:
        wt = node.get('widgetType') or ''
        el = node.get('elType') or ''
        st = _node_settings(node)
        eid = _normalize_element_id(st.get('_element_id'))

        if el in ('container', 'section') and eid:
            if eid in ARTE_CONTAINER_IDS:
                _enter_arte()
            elif eid in CURSO_SECTION_CONTAINER_IDS:
                _leave_arte()
            continue

        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in ARTE_SECTION_HEADINGS_READ:
                _enter_arte()
            elif title in (
                'Cursos de Negocios',
                'Cursos en Ciencia',
                'Cursos en Espiritualidad',
                'Catálogo de Cursos y Programas',
            ):
                _leave_arte()
            continue
        if not in_arte:
            continue
        if wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                pending_image = (node, url)
            continue
        if wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain:
                pending_text = (node, plain)
            continue
        if wt == 'button':
            flush(node, _slug_from_inscripcion_url((st.get('link') or {}).get('url') or ''))

    return cards, notes


@dataclass
class _WpArteCatalogCard:
    """Tarjeta WP por posición en sección Arte (slug canónico Apps, nodos Elementor para push)."""

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
        """Escribe solo esta tarjeta en Elementor (texto, imagen, botón → inscripción Apps)."""
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


def _index_arte_catalog_cards(data: list) -> tuple[list[_WpArteCatalogCard], list[str]]:
    """Hasta 4 tarjetas en sección Arte, en orden DOM (para catálogo por título)."""
    flat: list[dict] = []
    _walk_nodes(data, flat)

    in_arte = False
    arte_slot = 0
    pending_image: tuple[dict, str] | None = None
    pending_text: tuple[dict, str] | None = None
    cards: list[_WpArteCatalogCard] = []
    notes: list[str] = []

    def _enter_arte() -> None:
        nonlocal in_arte, arte_slot, pending_image, pending_text
        in_arte = True
        arte_slot = 0
        pending_image = pending_text = None

    def _leave_arte() -> None:
        nonlocal in_arte, arte_slot, pending_image, pending_text
        in_arte = False
        arte_slot = 0
        pending_image = pending_text = None

    def flush(button_node: dict, btn_slug: str | None) -> None:
        nonlocal pending_image, pending_text, arte_slot
        if not in_arte or arte_slot >= len(ARTE_WP_TITLE_PULL_CATALOG):
            pending_image = pending_text = None
            return
        entry = ARTE_WP_TITLE_PULL_CATALOG[arte_slot]
        img_url = pending_image[1] if pending_image else None
        if img_url and btn_slug and btn_slug != entry['canonical_slug']:
            notes.append(
                f'Arte posición {arte_slot + 1}: botón WP apunta a «{btn_slug}»; '
                f'push usará slug Apps «{entry["canonical_slug"]}».'
            )
        cards.append(
            _WpArteCatalogCard(
                slot=arte_slot + 1,
                slug=entry['canonical_slug'],
                text_node=pending_text[0] if pending_text else None,
                image_node=pending_image[0] if pending_image else None,
                button_node=button_node,
                pull_short_plain=pending_text[1] if pending_text else None,
                pull_image_url=img_url,
                pull_button_slug=(btn_slug or '').strip().lower() or None,
                pull_cta_label=(_node_settings(button_node).get('text') or '').strip() or None,
            )
        )
        pending_image = pending_text = None
        arte_slot += 1

    for node in flat:
        wt = node.get('widgetType') or ''
        el = node.get('elType') or ''
        st = _node_settings(node)
        eid = _normalize_element_id(st.get('_element_id'))

        if el in ('container', 'section') and eid:
            if eid in ARTE_CONTAINER_IDS:
                _enter_arte()
            elif eid in CURSO_SECTION_CONTAINER_IDS:
                _leave_arte()
            continue

        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in ARTE_SECTION_HEADINGS_READ:
                _enter_arte()
            elif title in (
                'Cursos de Negocios',
                'Cursos en Ciencia',
                'Cursos en Espiritualidad',
                'Catálogo de Cursos y Programas',
            ):
                _leave_arte()
            continue
        if not in_arte:
            continue
        if wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                pending_image = (node, url)
            continue
        if wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain:
                pending_text = (node, plain)
            continue
        if wt == 'button':
            flush(node, _slug_from_inscripcion_url((st.get('link') or {}).get('url') or ''))

    return cards, notes


def _find_apps_program_by_canonical_slug(organization_id: int, canonical_slug: str) -> Any | None:
    """Solo coincidencia exacta del slug canónico (sin botón WP ni legacy)."""
    from models.academic_program import AcademicProgram

    slug = (canonical_slug or '').strip().lower()
    if not slug:
        return None
    return AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()


def _description_from_wp_card(card: _WpArteCatalogCard | None) -> str | None:
    if not card or not card.pull_short_plain:
        return None
    return _short_from_card_plain(card.pull_short_plain) or (card.pull_short_plain or '').strip() or None


def _proposed_arte_title_pull_updates(
    row,
    catalog_entry: dict[str, Any],
    card: _WpArteCatalogCard | None,
    *,
    for_create: bool,
) -> dict[str, Any]:
    desc = _description_from_wp_card(card)
    wp_image = (card.pull_image_url if card else None) or None
    proposed: dict[str, Any] = {
        'name': catalog_entry['wp_title'],
        'category': ARTE_CATEGORY,
        'program_type': 'curso',
        'short_description': desc,
        'image_wp_landing': (wp_image or '').strip() or None,
    }
    if for_create:
        proposed['slug'] = catalog_entry['canonical_slug']
        proposed['_create_status'] = 'draft'

    changes: dict[str, Any] = {}
    for field, new_val in proposed.items():
        if field.startswith('_') or field not in ARTE_PULL_ALLOWED_FIELDS:
            continue
        if field in ARTE_PULL_PROTECTED_FIELDS:
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


def scan_arte_wp_title_pull_table(organization_id: int) -> dict[str, Any]:
    """
    Dry-run: solo los 4 títulos del catálogo ARTE_WP_TITLE_PULL_CATALOG.
    No escribe BD ni Elementor.
    """
    page_data = _load_elementor_data()
    wp_cards, notes = _index_arte_catalog_cards(page_data)
    errors: list[str] = list(notes[:16])

    rows: list[dict[str, Any]] = []
    canonical_slugs = {c['canonical_slug'] for c in ARTE_WP_TITLE_PULL_CATALOG}

    for i, catalog_entry in enumerate(ARTE_WP_TITLE_PULL_CATALOG):
        card = wp_cards[i] if i < len(wp_cards) else None
        slug_wp = card.pull_button_slug if card else None
        wp_detected = card is not None
        canonical = catalog_entry['canonical_slug']
        apps_row = _find_apps_program_by_canonical_slug(int(organization_id), canonical)
        apps_row_is_arte = (
            apps_row is not None
            and (apps_row.category or '').strip() == ARTE_CATEGORY
        )

        field_updates: dict[str, Any] = {}
        nota: str | None = None
        if not wp_detected:
            action = 'ignorar'
            errors.append(f'WP sin tarjeta en posición {i + 1}: {catalog_entry["wp_title"][:50]}…')
        elif apps_row is not None and not apps_row_is_arte:
            action = 'ignorar'
            nota = (
                f'Slug «{canonical}» ya existe en Apps (id={apps_row.id}, '
                f'categoría «{apps_row.category}», status={apps_row.status}). '
                'No se actualiza ni se reutiliza; definir slug distinto para arte o resolver manualmente.'
            )
            errors.append(nota)
        elif apps_row is None:
            action = 'crear'
            field_updates = _proposed_arte_title_pull_updates(
                None, catalog_entry, card, for_create=True
            )
        elif not _proposed_arte_title_pull_updates(apps_row, catalog_entry, card, for_create=False):
            action = 'ignorar'
        else:
            action = 'actualizar'
            field_updates = _proposed_arte_title_pull_updates(
                apps_row, catalog_entry, card, for_create=False
            )

        rows.append(
            {
                'wp_title': catalog_entry['wp_title'],
                'slug_wp': slug_wp,
                'slug_wp_note': 'solo informativo; no usado para matching',
                'canonical_slug': canonical,
                'existe_en_apps': 'sí' if apps_row is not None else 'no',
                'existe_slug_arte': 'sí' if apps_row_is_arte else ('no' if apps_row is None else 'no (otra categoría)'),
                'slug_apps_relacionado': (apps_row.slug if apps_row else canonical),
                'apps_id': int(apps_row.id) if apps_row else None,
                'apps_status': (apps_row.status if apps_row else None),
                'accion_propuesta': action,
                'campos_actualizar': field_updates,
                'campos_protegidos': list(ARTE_PULL_PROTECTED_LABELS),
                'wp_image_readonly': (card.pull_image_url if card else None),
                'wp_description_readonly': _description_from_wp_card(card),
                'nota': nota,
            }
        )

    from models.academic_program import AcademicProgram

    for legacy_slug in sorted(ARTE_APPS_LEGACY_REVIEW_SLUGS):
        if legacy_slug in canonical_slugs:
            continue
        legacy_row = AcademicProgram.query.filter_by(
            organization_id=int(organization_id), slug=legacy_slug
        ).first()
        if legacy_row is None:
            continue
        rows.append(
            {
                'wp_title': f'(Apps legacy) {legacy_row.name}',
                'slug_wp': '—',
                'slug_wp_note': 'no aplica',
                'canonical_slug': '—',
                'existe_en_apps': 'sí',
                'slug_apps_relacionado': legacy_slug,
                'apps_id': int(legacy_row.id),
                'apps_status': legacy_row.status,
                'accion_propuesta': 'legacy/revisar',
                'campos_actualizar': {},
                'campos_protegidos': list(ARTE_PULL_PROTECTED_LABELS),
                'wp_image_readonly': None,
                'wp_description_readonly': None,
                'nota': (
                    'No se modifica en pull. Posible CollageMapas publicado; '
                    'decisión manual antes de archivar o renombrar.'
                ),
            }
        )

    return {
        'organization_id': int(organization_id),
        'wp_page_id': WP_CURSOS_PAGE_ID,
        'mode': 'dry_run',
        'catalog_titles': [c['wp_title'] for c in ARTE_WP_TITLE_PULL_CATALOG],
        'wp_cards_found': len(wp_cards),
        'rows': rows,
        'errors': errors,
    }


class _ArteElementorPage:
    def __init__(self, data: list | None = None) -> None:
        self.data = data if data is not None else _load_elementor_data()
        self.catalog_cards, self.wiring_notes = _index_arte_catalog_cards(self.data)
        self.cards, _legacy_notes = _index_arte_cards(self.data)

    def pull_blocks(self) -> list[dict[str, Any]]:
        return [self.cards[s].to_pull_block() for s in ARTE_SLUGS if s in self.cards]

    def push(self, programs: list, *, save: bool = True) -> int:
        """Varios programas (legacy). Preferir ``push_arte_slug_to_wp`` (uno por uno)."""
        by_slug = {(p.slug or '').strip().lower(): p for p in programs}
        media_base = _apps_public_base()
        n = 0
        for slug, card in self.cards.items():
            if slug in by_slug:
                card.apply_program(by_slug[slug], media_base=media_base)
                n += 1
        if save and n:
            self.save()
        return n

    def push_one_catalog_slot(self, program, slot_index: int) -> None:
        """Actualiza solo la tarjeta en posición ``slot_index`` (0–3) y guarda Elementor."""
        if slot_index < 0 or slot_index >= len(self.catalog_cards):
            raise ValueError(f'Posición de tarjeta WP inválida: {slot_index}')
        self.catalog_cards[slot_index].apply_program(program, media_base=_apps_public_base())
        self.save()

    def save(self) -> None:
        _save_elementor_data(self.data)


# Campos que un pull seguro puede proponer (nunca image_url, flyer_url, status ni planes).
ARTE_PULL_SAFE_FIELDS: frozenset[str] = frozenset(
    ('category', 'program_type', 'name', 'short_description', 'cta_label', 'catalog_sort_order')
)


def _proposed_arte_field_updates(
    row,
    block: dict[str, Any],
    card: _WpArteCard | None,
) -> dict[str, Any]:
    """Valores destino desde WP; vacío si no hay cambio respecto a Apps."""
    slug = (block.get('slug') or '').strip().lower()
    proposed: dict[str, Any] = {
        'category': ARTE_CATEGORY,
        'program_type': 'curso',
        'name': _FORMAL_NAMES.get(slug) or block.get('name') or row.name,
        'cta_label': (block.get('cta_label') or '').strip() or None,
        'catalog_sort_order': int(block.get('catalog_sort_order') or 0),
    }
    img_slug = _slug_from_image_url(card.pull_image_url if card else None)
    if img_slug == slug and block.get('short_description'):
        proposed['short_description'] = block['short_description']

    changes: dict[str, Any] = {}
    for field, new_val in proposed.items():
        if field not in ARTE_PULL_SAFE_FIELDS:
            continue
        old_val = getattr(row, field, None)
        if field == 'catalog_sort_order':
            old_cmp = int(old_val or 0)
            new_cmp = int(new_val or 0)
            if old_cmp != new_cmp:
                changes[field] = new_cmp
            continue
        old_s = (old_val if old_val is not None else '')
        if isinstance(old_s, str):
            old_s = old_s.strip()
        new_s = (new_val if new_val is not None else '')
        if isinstance(new_s, str):
            new_s = new_s.strip()
        if old_s != new_s:
            changes[field] = new_val
    return changes


def scan_arte_wp_for_apps(organization_id: int) -> dict[str, Any]:
    """
    Lee WP (solo sección Arte) y compara con AcademicProgram por slug.
    No escribe BD ni Elementor.
    """
    from models.academic_program import AcademicProgram

    page = _ArteElementorPage()
    errors: list[str] = list(page.wiring_notes[:12])
    wp_slugs_detected = list(page.cards.keys())
    missing_in_wp = [s for s in ARTE_SLUGS if s not in page.cards]
    if not page.cards:
        errors.append(
            'No hay tarjetas en la sección Arte de WP /cursos-detalle/ '
            f'(título «Cursos en Arte» / «{ARTE_SECTION_HEADING}» o contenedor CSS id Cursos_arte).'
        )

    items: list[dict[str, Any]] = []
    for slug in ARTE_SLUGS:
        block = page.cards[slug].to_pull_block() if slug in page.cards else None
        card = page.cards.get(slug)
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        wp_preview = {}
        if block:
            wp_preview = {
                'wp_short_description': block.get('short_description'),
                'wp_cta_label': block.get('cta_label'),
                'wp_catalog_sort_order': block.get('catalog_sort_order'),
                'wp_image_url_readonly': block.get('image_url'),
            }
        entry: dict[str, Any] = {
            'slug': slug,
            'in_wp': slug in page.cards,
            'in_apps': row is not None,
            'apps_id': int(row.id) if row else None,
            'apps_status': (row.status if row else None),
            'apps_image_url': (row.image_url if row else None),
            'apps_flyer_url': (row.flyer_url if row else None),
            'wp': wp_preview,
            'field_updates': {},
            'skipped_fields': ['image_url', 'flyer_url', 'status', 'pricing_plans'],
        }
        if row and block:
            entry['field_updates'] = _proposed_arte_field_updates(row, block, card)
        elif not row:
            errors.append(f'No existe en Apps (solo pull a filas existentes): {slug}')
        items.append(entry)

    return {
        'organization_id': int(organization_id),
        'wp_page_id': WP_CURSOS_PAGE_ID,
        'wp_slugs_detected': wp_slugs_detected,
        'expected_slugs': list(ARTE_SLUGS),
        'missing_in_wp': missing_in_wp,
        'items': items,
        'errors': errors,
    }


def apply_arte_wp_title_pull(
    organization_id: int,
    db,
    *,
    dry_run: bool = True,
) -> tuple[int, list[str], dict[str, Any]]:
    """Aplica pull por catálogo de títulos (crear borrador / actualizar campos permitidos)."""
    report = scan_arte_wp_title_pull_table(organization_id)
    errors: list[str] = list(report.get('errors') or [])
    created = updated = 0

    if dry_run:
        report['dry_run'] = True
        report['would_create'] = sum(1 for r in report['rows'] if r['accion_propuesta'] == 'crear')
        report['would_update'] = sum(1 for r in report['rows'] if r['accion_propuesta'] == 'actualizar')
        report['would_legacy'] = sum(1 for r in report['rows'] if r['accion_propuesta'] == 'legacy/revisar')
        return 0, errors, report

    from models.academic_program import AcademicProgram

    for row_data in report.get('rows') or []:
        action = row_data.get('accion_propuesta')
        if action in ('legacy/revisar', 'ignorar'):
            continue
        changes = dict(row_data.get('campos_actualizar') or {})
        create_status = changes.pop('_create_status', None)

        if action == 'crear':
            slug = changes.pop('slug', None) or row_data.get('canonical_slug')
            if not slug:
                continue
            if AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first():
                errors.append(f'Ya existe slug {slug}; omitido crear')
                continue
            prog = AcademicProgram(
                organization_id=int(organization_id),
                slug=slug,
                status='draft',
                name=changes.get('name') or row_data.get('wp_title'),
                program_type=changes.get('program_type') or 'curso',
                category=changes.get('category') or ARTE_CATEGORY,
                short_description=changes.get('short_description'),
                image_wp_landing=changes.get('image_wp_landing'),
            )
            db.session.add(prog)
            created += 1
        elif action == 'actualizar':
            prog = None
            if row_data.get('slug_apps_relacionado'):
                prog = AcademicProgram.query.filter_by(
                    organization_id=int(organization_id),
                    slug=row_data['slug_apps_relacionado'],
                ).first()
            if not prog:
                errors.append(f'Sin fila Apps para actualizar: {row_data.get("wp_title")}')
                continue
            for field, val in changes.items():
                if field in ARTE_PULL_ALLOWED_FIELDS and field not in ARTE_PULL_PROTECTED_FIELDS:
                    setattr(prog, field, val)
            updated += 1

    if created or updated:
        db.session.commit()
    report['dry_run'] = False
    report['created'] = created
    report['updated'] = updated
    return created + updated, errors, report


def pull_arte_from_wp_safe(
    organization_id: int,
    db,
    *,
    dry_run: bool = True,
) -> tuple[int, list[str], dict[str, Any]]:
    """Pull selectivo Arte (catálogo por título)."""
    return apply_arte_wp_title_pull(organization_id, db, dry_run=dry_run)


def _pull_arte_from_wp_safe_legacy(
    organization_id: int,
    db,
    *,
    dry_run: bool = True,
) -> tuple[int, list[str], dict[str, Any]]:
    """
    Pull legacy por slug ARTE_SLUGS (deprecado para operación manual).
    """
    report = scan_arte_wp_for_apps(organization_id)
    errors: list[str] = list(report.get('errors') or [])
    updated = 0

    if dry_run:
        return 0, errors, report

    from models.academic_program import AcademicProgram

    for entry in report.get('items') or []:
        slug = entry.get('slug')
        changes = entry.get('field_updates') or {}
        if not changes:
            continue
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if not row:
            continue
        for field, val in changes.items():
            if field in ARTE_PULL_SAFE_FIELDS:
                setattr(row, field, val)
        updated += 1

    if updated:
        db.session.commit()
    return updated, errors, report


def pull_arte_from_wp(organization_id: int, db) -> tuple[int, list[str]]:
    """Importación Arte (modo seguro). No publica ni sobrescribe medios de catálogo/inscripción."""
    n, errs, _report = pull_arte_from_wp_safe(organization_id, db, dry_run=False)
    return n, errs


def push_arte_slug_to_wp(organization_id: int, slug: str) -> tuple[bool, str | None]:
    """
    Publica en WordPress **solo la tarjeta** del programa (posición 1–4 en «Cursos de Arte»).
    No actualiza las otras tres tarjetas ni el resto de /cursos-detalle/.
    """
    from models.academic_program import AcademicProgram

    slug = (slug or '').strip().lower()
    slot = _arte_catalog_slot_for_slug(slug)
    if slot is None:
        return False, (
            f'Solo los 4 cursos de «{ARTE_SECTION_HEADING}» con slug canónico '
            f'({", ".join(sorted(WP_ARTE_PUSH_SLUGS))}).'
        )
    row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
    if not row:
        return False, f'No existe «{slug}» en Apps.'
    page = _ArteElementorPage()
    if slot >= len(page.catalog_cards):
        title = ARTE_WP_TITLE_PULL_CATALOG[slot]['wp_title']
        return False, (
            f'No hay tarjeta WP en posición {slot + 1} («{title[:50]}…»). '
            'Revisá la sección Cursos de Arte en /cursos-detalle/.'
        )
    try:
        page.push_one_catalog_slot(row, slot)
    except Exception as e:
        return False, str(e)
    return True, None
