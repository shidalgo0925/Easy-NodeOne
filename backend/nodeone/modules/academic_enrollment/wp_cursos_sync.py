"""Sincronización cursos IIUS: WordPress (pág. 2006 /cursos-detalle/) ↔ AcademicProgram.

Tarjetas Elementor (imagen + texto + botón «Ver más» → /inscripcion/<slug>).
El slug canónico de cada tarjeta se deduce del archivo de imagen (cableado WP histórico).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
    _apps_public_base,
    _patch_image_widget,
    _run_wp_cli,
    _strip_html,
    _walk_nodes,
)

WP_CURSOS_PAGE_ID = 2006

# 12 tarjetas en /cursos-detalle/ (neuroplasticidad no está en esta página).
CURSO_SLUGS: tuple[str, ...] = (
    'curso-en-liderazgo-y-gestion-de-equipos',
    'cursos-en-emprendimiento-y-desarrollo-de-negocios',
    'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
    'curso-en-finanzas-personales-y-empresariales',
    'curso-en-coaching-profesional-integral',
    'curso-tecnicas-anclaje-pnl',
    'curso-en-inteligencia-emocional-y-bienestar',
    'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl',
    'curso-en-mindfulness-y-reduccion-del-estres',
    'curso-en-espiritualidad-y-crecimiento-personal',
    'renovacion-de-la-mente',
    'la-mujer-virtuosa-de-prov-31',
)

from nodeone.modules.academic_enrollment.catalog_public import (
    ARTE_CATEGORY,
    ARTE_SLUGS,
    ARTE_WP_CONTAINER_IDS,
    ARTE_WP_SECTION_TITLES,
)

CURSO_SECTION_HEADINGS: frozenset[str] = frozenset(
    ('Cursos de Negocios', 'Cursos en Ciencia', 'Cursos en Espiritualidad', ARTE_CATEGORY)
)

# Orden oficial por sección (alineado a cursos-detalle en WP). Arte = misma lógica que Espiritualidad.
CURSO_SLUGS_BY_SECTION: dict[str, tuple[str, ...]] = {
    'Cursos de Negocios': CURSO_SLUGS[0:4],
    'Cursos en Ciencia': CURSO_SLUGS[4:8],
    'Cursos en Espiritualidad': CURSO_SLUGS[8:12],
    ARTE_CATEGORY: ARTE_SLUGS,
}

CURSO_CONTAINER_TO_CATEGORY: dict[str, str] = {
    'curso_negocios': 'Cursos de Negocios',
    'curso_ciencia': 'Cursos en Ciencia',
    'cursos_espiritualidad': 'Cursos en Espiritualidad',
}

# Nombre de archivo WP → slug (misma matriz que apply_iius_wp_ver_mas_inscripcion).
_IMAGE_STEM_TO_SLUG: dict[str, str] = {
    'liderasgo-de-gestion-de-equipo': 'curso-en-liderazgo-y-gestion-de-equipos',
    'desarrollo-de-negocio': 'cursos-en-emprendimiento-y-desarrollo-de-negocios',
    'liderasgo-organizacional': 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
    'finanzas-personales': 'curso-en-finanzas-personales-y-empresariales',
    'finanzapersonales': 'curso-en-finanzas-personales-y-empresariales',
    'coaching-prof': 'curso-en-coaching-profesional-integral',
    'coaching-profesional-integral': 'curso-en-coaching-profesional-integral',
    'ancalje': 'curso-tecnicas-anclaje-pnl',
    'ieyb': 'curso-en-inteligencia-emocional-y-bienestar',
    'iemo': 'curso-en-inteligencia-emocional-y-bienestar',
    'pnl': 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl',
    'pnlarte': 'curso-tecnicas-anclaje-pnl',  # archivo PNL arte; no confundir con CreatividadVak
    'reencuadrespnl': 'curso-tecnicas-anclaje-pnl',
    'mindfulness': 'curso-en-mindfulness-y-reduccion-del-estres',
    'espiritualidad-crecimiento': 'curso-en-espiritualidad-y-crecimiento-personal',
    'renovacion-de-mente': 'renovacion-de-la-mente',
    'mujer-virtuosa': 'la-mujer-virtuosa-de-prov-31',
    # Cursos de Arte (imagen WP → slug curso-en-*)
    'collagemapas': 'curso-en-aprendizaje-practico',
    'chatgpt-image-19-may-2026-22_01_31': 'curso-en-liderazgo-y-comunicacion',
    'creatividadvak': 'curso-en-creatividad-y-expresion-artistica-aplicada',
    'eldr': 'curso-en-desarrollo-humano',
}

# Títulos formales en apps (no usar solo el copy corto de la tarjeta WP).
_CURSO_FORMAL_NAMES: dict[str, str] = {
    'curso-en-liderazgo-y-gestion-de-equipos': 'Curso en Liderazgo y Gestión de Equipos',
    'cursos-en-emprendimiento-y-desarrollo-de-negocios': 'Cursos en Emprendimiento y Desarrollo de Negocios',
    'curso-en-coaching-ejecutivo-y-liderazgo-organizacional': 'Curso en Coaching Ejecutivo y Liderazgo Organizacional',
    'curso-en-finanzas-personales-y-empresariales': 'Curso en Finanzas Personales y Empresariales',
    'curso-en-coaching-profesional-integral': 'Curso en Coaching Profesional Integral',
    'curso-tecnicas-anclaje-pnl': 'Técnicas de Anclaje PNL',
    'curso-en-inteligencia-emocional-y-bienestar': 'Curso en Inteligencia Emocional y Bienestar',
    'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl': (
        'Curso en Neuroeducación y Programación Neurolingüística (PNL)'
    ),
    'curso-en-mindfulness-y-reduccion-del-estres': 'Curso en Mindfulness y Reducción del Estrés',
    'curso-en-espiritualidad-y-crecimiento-personal': 'Curso en Espiritualidad y Crecimiento Personal',
    'renovacion-de-la-mente': 'Renovación de la Mente',
    'la-mujer-virtuosa-de-prov-31': 'La Mujer Virtuosa de Prov 31',
    'curso-en-aprendizaje-practico': 'Curso en Aprendizaje Práctico',
    'curso-en-liderazgo-y-comunicacion': 'Curso en Liderazgo y Comunicación',
    'curso-en-creatividad-y-expresion-artistica-aplicada': (
        'Curso en Creatividad y Expresión Artística Aplicada'
    ),
    'curso-en-desarrollo-humano': 'Curso en Desarrollo Humano',
}

WP_CURSO_SLUGS: frozenset[str] = frozenset(CURSO_SLUGS)
WP_ARTE_SLUGS: frozenset[str] = frozenset(ARTE_SLUGS)
WP_PAGE_CURSO_SLUGS: frozenset[str] = WP_CURSO_SLUGS | WP_ARTE_SLUGS

# En BD pero no en cursos-detalle: no mezclar con los 4 de Ciencia en WP.
CURSO_CIENCIA_APPS_ONLY_SLUGS: frozenset[str] = frozenset({'curso-de-neuroeducacion-y-neuroplasticidad'})


def is_wp_curso_slug(slug: str | None) -> bool:
    from nodeone.modules.academic_enrollment.wp_talleres_sync import canonical_arte_slug

    s = canonical_arte_slug(slug) or (slug or '').strip().lower()
    return s in WP_PAGE_CURSO_SLUGS


def wp_sync_target_for_slug(slug: str | None) -> str | None:
    from nodeone.modules.academic_enrollment.wp_talleres_sync import canonical_arte_slug

    s = canonical_arte_slug(slug) or (slug or '').strip().lower()
    if s in WP_ARTE_SLUGS:
        return 'arte'
    if s in WP_CURSO_SLUGS:
        return 'cursos'
    return None


def _normalize_element_id(raw: str | None) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (raw or '').strip().lower()).strip('_')


def _slug_from_inscripcion_url(url: str | None) -> str | None:
    from nodeone.modules.academic_enrollment.wp_talleres_sync import canonical_arte_slug

    if not url or '/inscripcion/' not in url:
        return None
    raw = url.split('/inscripcion/')[-1].split('?')[0].strip('/').lower()
    return canonical_arte_slug(raw) or raw


def _inscripcion_url(slug: str) -> str:
    return f'{_apps_public_base()}/inscripcion/{slug.strip().lower()}'


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


def _title_from_card_plain(plain: str) -> str | None:
    s = (plain or '').strip().lstrip('💡').strip()
    if ':' in s:
        return s.split(':', 1)[0].strip()
    return None


@dataclass
class _WpCursoCard:
    slug: str
    category: str | None = None
    sort_order: int = 0
    text_node: dict | None = None
    image_node: dict | None = None
    button_node: dict | None = None
    pull_short_plain: str | None = None
    pull_image_url: str | None = None
    pull_cta_label: str | None = None
    wiring_fixed: bool = False

    def to_pull_block(self) -> dict[str, Any]:
        short = _short_from_card_plain(self.pull_short_plain or '')
        name = _CURSO_FORMAL_NAMES.get(self.slug) or _title_from_card_plain(self.pull_short_plain or '')
        return {
            'slug': self.slug,
            'name': name,
            'category': self.category,
            'short_description': short or None,
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


def _index_cursos_cards(data: list) -> tuple[dict[str, _WpCursoCard], list[str]]:
    """Recorre la página en orden; cada tarjeta = imagen + texto + botón en la misma sección."""
    flat: list[dict] = []
    _walk_nodes(data, flat)

    cur_cat: str | None = None
    sort_in_section = 0
    pending_image: tuple[dict, str] | None = None
    pending_text: tuple[dict, str] | None = None
    cards: dict[str, _WpCursoCard] = {}
    wiring_notes: list[str] = []

    def flush_card(button_node: dict, btn_slug: str | None) -> None:
        nonlocal sort_in_section, pending_image, pending_text
        if not cur_cat:
            return
        img_slug = _slug_from_image_url(pending_image[1]) if pending_image else None
        slug = img_slug or btn_slug
        if cur_cat == ARTE_CATEGORY and slug not in WP_ARTE_SLUGS:
            order = CURSO_SLUGS_BY_SECTION.get(ARTE_CATEGORY, ())
            if sort_in_section < len(order):
                slug = order[sort_in_section]
        if not slug or slug not in WP_PAGE_CURSO_SLUGS:
            pending_image = pending_text = None
            return

        if img_slug and btn_slug and img_slug != btn_slug:
            st = _node_settings(button_node)
            link = st.get('link')
            if not isinstance(link, dict):
                link = {}
                st['link'] = link
            link['url'] = _inscripcion_url(img_slug)
            wiring_notes.append(f'Botón corregido: {btn_slug} → {img_slug} (imagen {pending_image[1].rsplit("/", 1)[-1]})')

        expected_order = CURSO_SLUGS_BY_SECTION.get(cur_cat, ())
        if slug in expected_order:
            sort_in_section = expected_order.index(slug) + 1
        else:
            sort_in_section += 1

        cards[slug] = _WpCursoCard(
            slug=slug,
            category=cur_cat,
            sort_order=sort_in_section,
            text_node=pending_text[0] if pending_text else None,
            image_node=pending_image[0] if pending_image else None,
            button_node=button_node,
            pull_short_plain=pending_text[1] if pending_text else None,
            pull_image_url=pending_image[1] if pending_image else None,
            pull_cta_label=(_node_settings(button_node).get('text') or '').strip() or None,
            wiring_fixed=bool(img_slug and btn_slug and img_slug != btn_slug),
        )
        pending_image = pending_text = None

    for node in flat:
        wt = node.get('widgetType') or ''
        el = node.get('elType') or ''
        st = _node_settings(node)
        eid = _normalize_element_id(st.get('_element_id'))

        if el in ('container', 'section') and eid:
            if eid in ARTE_WP_CONTAINER_IDS:
                cur_cat = ARTE_CATEGORY
                sort_in_section = 0
                pending_image = pending_text = None
            elif eid in CURSO_CONTAINER_TO_CATEGORY:
                cur_cat = CURSO_CONTAINER_TO_CATEGORY[eid]
                sort_in_section = 0
                pending_image = pending_text = None
            continue

        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in CURSO_SECTION_HEADINGS:
                cur_cat = ARTE_CATEGORY if title in ARTE_WP_SECTION_TITLES else title
                sort_in_section = 0
                pending_image = pending_text = None
            elif title in ARTE_WP_SECTION_TITLES:
                cur_cat = ARTE_CATEGORY
                sort_in_section = 0
                pending_image = pending_text = None
            elif title in ('Talleres', 'Catálogo de Cursos y Programas'):
                cur_cat = None
                pending_image = pending_text = None
            continue

        if cur_cat not in CURSO_SECTION_HEADINGS:
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
            btn_slug = _slug_from_inscripcion_url((st.get('link') or {}).get('url') or '')
            if btn_slug or pending_image:
                flush_card(node, btn_slug)

    return cards, wiring_notes


class _CursosElementorPage:
    def __init__(self, data: list | None = None) -> None:
        self.data = data if data is not None else _load_elementor_data()
        self.cards, self.wiring_notes = _index_cursos_cards(self.data)

    def pull_blocks(self) -> list[dict[str, Any]]:
        blocks = []
        for section, slugs in CURSO_SLUGS_BY_SECTION.items():
            for slug in slugs:
                if slug in self.cards:
                    blocks.append(self.cards[slug].to_pull_block())
        return blocks

    def push(self, programs: list, *, save: bool = True) -> int:
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

    def save(self) -> None:
        _save_elementor_data(self.data)


def _normalize_ciencia_apps_only(db, organization_id: int) -> None:
    """Cursos en Ciencia que no están en WP: orden al final del bloque (no intercalados)."""
    from models.academic_program import AcademicProgram

    for slug in CURSO_CIENCIA_APPS_ONLY_SLUGS:
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if row and (row.category or '').strip() == 'Cursos en Ciencia':
            row.catalog_sort_order = 99


def pull_cursos_from_wp(organization_id: int, db) -> tuple[int, list[str]]:
    from models.academic_program import AcademicProgram

    errors: list[str] = []
    page = _CursosElementorPage()
    if page.wiring_notes:
        errors.extend(page.wiring_notes[:8])
        if len(page.wiring_notes) > 8:
            errors.append(f'… y {len(page.wiring_notes) - 8} avisos de cableado en WP (sin escribir WP en pull)')

    blocks = page.pull_blocks()
    missing_wp = [s for s in CURSO_SLUGS if s not in page.cards]
    if missing_wp:
        errors.append(f'En WP no hay tarjeta para: {", ".join(missing_wp[:4])}' + ('…' if len(missing_wp) > 4 else ''))

    if len(blocks) < 10:
        errors.append(f'Solo se detectaron {len(blocks)} tarjetas curso en WP (se esperan 12).')

    updated = 0
    for block in blocks:
        slug = block.get('slug')
        if not slug:
            continue
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if not row:
            errors.append(f'No existe en apps: {slug}')
            continue
        if (row.program_type or '').lower() != 'curso':
            errors.append(f'«{slug}» no es program_type=curso en apps (omitido).')
            continue

        if block.get('category'):
            row.category = block['category']
        if block.get('name'):
            row.name = block['name']
        if block.get('short_description'):
            row.short_description = block['short_description']
        if block.get('image_url'):
            row.image_url = block['image_url']
        if block.get('cta_label'):
            row.cta_label = block['cta_label']
        if block.get('catalog_sort_order') is not None:
            row.catalog_sort_order = int(block['catalog_sort_order'])
        updated += 1

    _normalize_ciencia_apps_only(db, organization_id)
    db.session.commit()
    return updated, errors


def push_cursos_to_wp(organization_id: int) -> tuple[int, list[str]]:
    from models.academic_program import AcademicProgram

    errors: list[str] = []
    programs = []
    for slug in (*CURSO_SLUGS, *ARTE_SLUGS):
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if row and (row.program_type or '').lower() == 'curso':
            programs.append(row)
        elif not row:
            errors.append(f'Falta en apps: {slug}')
    if not programs:
        return 0, errors
    n = _CursosElementorPage().push(programs)
    return n, errors


def push_curso_slug_to_wp(organization_id: int, slug: str) -> tuple[bool, str | None]:
    from models.academic_program import AcademicProgram

    slug = (slug or '').strip().lower()
    from nodeone.modules.academic_enrollment.wp_talleres_sync import canonical_arte_slug

    slug = canonical_arte_slug(slug) or slug
    if slug not in WP_PAGE_CURSO_SLUGS:
        return False, 'Este programa no está cableado en /cursos-detalle/ (12 cursos + 4 arte).'
    row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
    if row is None:
        return False, f'No existe el programa «{slug}» en apps.'
    if (row.program_type or '').lower() != 'curso':
        return False, 'Solo se publican programas con tipo «curso».'
    page = _CursosElementorPage()
    if slug not in page.cards:
        return False, f'No se encontró tarjeta en WordPress para «{slug}».'
    page.push([row])
    return True, None
