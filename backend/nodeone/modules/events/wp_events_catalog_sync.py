"""Sincronización eventos IIUS: WP /eventos-2/ ↔ Apps Event (separado de cursos/talleres/arte).

Pull: pág. WP 2262 — lectura por sección (Eventos_Profesionales / Eventos_Personales).
Push: misma página, botones → /events/{slug} (solo slugs canónicos evento-profesional-* / evento-personal-*).

``event_type`` lógico → ``Event.category`` ('profesional' | 'personal'); no hay columna event_type en ORM.

---
FASE 3 CERRADA: 8 borradores (ids 1–8), publish_status=draft, 0 publicados, 0 push WP.

FASE 4 (manual Apps): fechas, cover, modalidad, precio, cupos, descripción, publicar.
NO ejecutar pull / push / publish / sync WP hasta completar FASE 4.

Criterio desbloqueo FASE 5 (los 8 eventos):
  - cover correcto, fechas reales, modalidad, descripción, publicados
  - /events mostrando correctamente los 8

FASE 5 (solo tras criterio anterior, con autorización):
  1. Push WP dry-run por sección
  2. Revisar mapping
  3. Push WP apply
  4. Validar botones y enlaces
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import Any

from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
    _apps_public_base,
    _run_wp_cli,
    _strip_html,
    _walk_nodes,
)

WP_EVENTS_PAGE_ID = 2262
EVENTS_SECTION_PROF = 'Eventos_Profesionales'
EVENTS_SECTION_PERS = 'Eventos_Personales'

EVENTS_PULL_PROTECTED_FIELDS: frozenset[str] = frozenset(
    ('publish_status', 'start_date', 'end_date', 'cover_image', 'base_price', 'capacity', 'format')
)
EVENTS_PULL_ALLOWED_FIELDS: frozenset[str] = frozenset(
    ('title', 'slug', 'summary', 'description', 'category', 'cover_image_wp_source')
)

# Catálogo canónico: slug viejo botón WP → slug evento Apps (no reutilizar curso-*).
EVENTS_WP_PULL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        'section': EVENTS_SECTION_PROF,
        'event_type': 'profesional',
        'position': 1,
        'title_short': 'Liderazgo y Gestión de Equipos',
        'slug_old': 'curso-en-liderazgo-y-gestion-de-equipos',
        'slug_proposed': 'evento-profesional-liderazgo-organizacional',
    },
    {
        'section': EVENTS_SECTION_PROF,
        'event_type': 'profesional',
        'position': 2,
        'title_short': 'Emprendimiento y Desarrollo de Negocios',
        'slug_old': 'cursos-en-emprendimiento-y-desarrollo-de-negocios',
        'slug_proposed': 'evento-profesional-emprendimiento-negocios',
    },
    {
        'section': EVENTS_SECTION_PROF,
        'event_type': 'profesional',
        'position': 3,
        'title_short': 'Coaching Ejecutivo y Liderazgo Organizacional',
        'slug_old': 'curso-en-coaching-ejecutivo-y-liderazgo-organizacional',
        'slug_proposed': 'evento-profesional-coaching-ejecutivo',
    },
    {
        'section': EVENTS_SECTION_PROF,
        'event_type': 'profesional',
        'position': 4,
        'title_short': 'Finanzas Personales y Empresariales',
        'slug_old': 'curso-en-finanzas-personales-y-empresariales',
        'slug_proposed': 'evento-profesional-finanzas-empresariales',
    },
    {
        'section': EVENTS_SECTION_PERS,
        'event_type': 'personal',
        'position': 1,
        'title_short': 'Coaching Profesional Integral',
        'slug_old': 'curso-en-coaching-profesional-integral',
        'slug_proposed': 'evento-personal-coaching-integral',
    },
    {
        'section': EVENTS_SECTION_PERS,
        'event_type': 'personal',
        'position': 2,
        'title_short': 'Técnicas de Anclaje PNL',
        'slug_old': 'curso-tecnicas-anclaje-pnl',
        'slug_proposed': 'evento-personal-tecnicas-anclaje-pnl',
    },
    {
        'section': EVENTS_SECTION_PERS,
        'event_type': 'personal',
        'position': 3,
        'title_short': 'Inteligencia Emocional y Bienestar',
        'slug_old': 'curso-en-inteligencia-emocional-y-bienestar',
        'slug_proposed': 'evento-personal-inteligencia-emocional',
    },
    {
        'section': EVENTS_SECTION_PERS,
        'event_type': 'personal',
        'position': 4,
        'title_short': 'Neuroeducación y Programación Neurolingüística',
        'slug_old': 'curso-en-neuroeducacion-y-programacion-neurolinguistica-pnl',
        'slug_proposed': 'evento-personal-neuroeducacion-pnl',
    },
)

WP_EVENTS_PUSH_SLUGS: frozenset[str] = frozenset(e['slug_proposed'] for e in EVENTS_WP_PULL_CATALOG)
EVENTS_SLUG_OLD_TO_PROPOSED: dict[str, str] = {
    e['slug_old']: e['slug_proposed'] for e in EVENTS_WP_PULL_CATALOG
}


def _load_elementor_data(page_id: int) -> list:
    proc = _run_wp_cli(['post', 'meta', 'get', str(page_id), '_elementor_data'])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli falló')
    raw = (proc.stdout or '').strip()
    if not raw or raw == '[]':
        return []
    return json.loads(raw)


def _slug_from_button_url(url: str | None) -> str:
    if not url:
        return ''
    u = url.strip().rstrip('\\').lower()
    if '/inscripcion/' in u:
        return u.split('/inscripcion/')[-1].split('?')[0].strip('/')
    if '/events/' in u:
        return u.split('/events/')[-1].split('?')[0].strip('/')
    return ''


def _events_url(slug: str) -> str:
    return f'{_apps_public_base()}/events/{slug.strip().lower()}'


@dataclass
class _WpEventCard:
    section: str
    position: int
    title_visible: str
    image_url: str
    slug_button: str
    button_url: str


def _section_from_heading(title: str) -> str | None:
    tl = (title or '').lower()
    if 'profesional' in tl:
        return EVENTS_SECTION_PROF
    if 'personal' in tl:
        return EVENTS_SECTION_PERS
    return None


def scan_wp_events_sections(page_id: int = WP_EVENTS_PAGE_ID) -> list[_WpEventCard]:
    """Lee tarjetas en /eventos-2/ agrupadas por heading de sección (solo lectura)."""
    data = _load_elementor_data(page_id)
    flat: list[dict] = []
    _walk_nodes(data, flat)

    section = ''
    pos_prof = pos_pers = 0
    pending_text = ''
    pending_img = ''
    cards: list[_WpEventCard] = []

    for node in flat:
        wt = node.get('widgetType') or ''
        st = node.get('settings') or {}
        if wt == 'heading':
            sec = _section_from_heading((st.get('title') or '').strip())
            if sec:
                section = sec
        elif wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain:
                pending_text = plain
        elif wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url:
                pending_img = url
        elif wt == 'button':
            btn_url = ((st.get('link') or {}).get('url') or '').strip().rstrip('\\')
            slug_btn = _slug_from_button_url(btn_url)
            if not slug_btn and not pending_img:
                continue
            if section == EVENTS_SECTION_PROF:
                pos_prof += 1
                pos = pos_prof
            elif section == EVENTS_SECTION_PERS:
                pos_pers += 1
                pos = pos_pers
            else:
                pos = 0
            cards.append(
                _WpEventCard(
                    section=section or '—',
                    position=pos,
                    title_visible=pending_text or '—',
                    image_url=pending_img,
                    slug_button=slug_btn,
                    button_url=btn_url,
                )
            )
            pending_text = pending_img = ''

    return cards


def _catalog_by_slug_old(slug_old: str) -> dict[str, Any] | None:
    s = (slug_old or '').strip().lower()
    for entry in EVENTS_WP_PULL_CATALOG:
        if entry['slug_old'] == s:
            return entry
    return None


def _catalog_by_section_position(section: str, position: int) -> dict[str, Any] | None:
    for entry in EVENTS_WP_PULL_CATALOG:
        if entry['section'] == section and int(entry['position']) == int(position):
            return entry
    return None


def run_events_section_inventory(page_id: int = WP_EVENTS_PAGE_ID) -> dict[str, Any]:
    """FASE 2 — tabla por sección (solo lectura)."""
    cards = scan_wp_events_sections(page_id)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for card in cards:
        catalog = _catalog_by_slug_old(card.slug_button) or _catalog_by_section_position(
            card.section, card.position
        )
        slug_proposed = (catalog or {}).get('slug_proposed') or '—'
        if not catalog:
            errors.append(
                f'Sin catálogo para sección={card.section} pos={card.position} slug={card.slug_button}'
            )
        elif catalog['slug_old'] != card.slug_button:
            errors.append(
                f'Slug botón WP ({card.slug_button}) ≠ catálogo ({catalog["slug_old"]}) '
                f'en {card.section} pos {card.position}'
            )
        rows.append(
            {
                'section': card.section,
                'position': card.position,
                'title_visible': card.title_visible,
                'title_short': (catalog or {}).get('title_short') or '—',
                'image': card.image_url,
                'slug_old_button': card.slug_button or '—',
                'slug_evento_propuesto': slug_proposed,
                'event_type': (catalog or {}).get('event_type') or '—',
                'button_url': card.button_url,
            }
        )

    expected = len(EVENTS_WP_PULL_CATALOG)
    if len(cards) != expected:
        errors.append(f'Esperadas {expected} tarjetas en WP; encontradas {len(cards)}')

    return {
        'wp_page_id': page_id,
        'wp_page_slug': 'eventos-2',
        'cards_found': len(cards),
        'rows': rows,
        'errors': errors,
        'catalog_count': expected,
    }


def _placeholder_event_dates() -> tuple[datetime, datetime]:
    """Fechas placeholder para borrador pull; FASE 4 debe reemplazarlas."""
    start = datetime.utcnow() + timedelta(days=90)
    end = start + timedelta(hours=3)
    return start, end


def _find_apps_event_by_slug(slug: str):
    from app import Event

    return Event.query.filter_by(slug=(slug or '').strip().lower()).first()


def _proposed_pull_fields(catalog_entry: dict[str, Any], card: _WpEventCard | None) -> dict[str, Any]:
    summary = (card.title_visible if card else '') or catalog_entry['title_short']
    return {
        'title': catalog_entry['title_short'],
        'slug': catalog_entry['slug_proposed'],
        'category': catalog_entry['event_type'],
        'summary': summary[:500] if summary else '',
        'description': summary,
        'cover_image_wp_source': (card.image_url if card else None) or '',
        '_publish_status': 'draft',
        '_start_date': _placeholder_event_dates()[0].isoformat(),
        '_end_date': _placeholder_event_dates()[1].isoformat(),
    }


def scan_events_wp_pull_table(organization_id: int) -> dict[str, Any]:
    """FASE 3 — dry-run pull WP → Apps (borradores)."""
    cards = scan_wp_events_sections(WP_EVENTS_PAGE_ID)
    cards_by_old: dict[str, _WpEventCard] = {c.slug_button: c for c in cards if c.slug_button}
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for entry in EVENTS_WP_PULL_CATALOG:
        card = cards_by_old.get(entry['slug_old'])
        slug = entry['slug_proposed']
        apps_row = _find_apps_event_by_slug(slug)

        if card is None:
            action = 'ignorar'
            errors.append(f'WP sin tarjeta slug_old={entry["slug_old"]}')
            fields: dict[str, Any] = {}
        elif apps_row is None:
            action = 'crear'
            fields = _proposed_pull_fields(entry, card)
        else:
            action = 'ignorar'
            fields = {}
            if (apps_row.publish_status or '') != 'draft':
                errors.append(f'{slug} ya existe (id={apps_row.id}, status={apps_row.publish_status})')

        rows.append(
            {
                'section': entry['section'],
                'position': entry['position'],
                'title_short': entry['title_short'],
                'slug_old': entry['slug_old'],
                'slug_proposed': slug,
                'event_type': entry['event_type'],
                'existe_en_apps': 'sí' if apps_row else 'no',
                'apps_id': int(apps_row.id) if apps_row else None,
                'apps_status': (apps_row.publish_status if apps_row else None),
                'accion_propuesta': action,
                'campos_actualizar': fields,
                'wp_image': card.image_url if card else None,
            }
        )

    return {
        'organization_id': int(organization_id),
        'wp_page_id': WP_EVENTS_PAGE_ID,
        'mode': 'dry_run',
        'rows': rows,
        'errors': errors,
        'would_create': sum(1 for r in rows if r['accion_propuesta'] == 'crear'),
        'would_update': sum(1 for r in rows if r['accion_propuesta'] == 'actualizar'),
    }


def apply_events_wp_pull(
    organization_id: int,
    db,
    *,
    dry_run: bool = True,
    created_by_user_id: int | None = None,
) -> tuple[int, list[str], dict[str, Any]]:
    """Pull WP → Apps. Por defecto dry_run; --apply crea borradores (publish_status=draft)."""
    from app import Event, User

    report = scan_events_wp_pull_table(organization_id)
    errors: list[str] = list(report.get('errors') or [])
    created = 0

    if dry_run:
        report['dry_run'] = True
        return 0, errors, report

    uid = created_by_user_id
    if not uid:
        u = User.query.filter_by(organization_id=int(organization_id)).order_by(User.id.asc()).first()
        uid = int(u.id) if u else 1

    start_pl, end_pl = _placeholder_event_dates()

    for row in report.get('rows') or []:
        if row.get('accion_propuesta') != 'crear':
            continue
        fields = row.get('campos_actualizar') or {}
        slug = row['slug_proposed']
        if _find_apps_event_by_slug(slug):
            errors.append(f'Abortado crear {slug}: slug ya existe')
            continue
        ev = Event(
            title=fields.get('title') or row['title_short'],
            slug=slug,
            summary=(fields.get('summary') or '')[:500],
            description=fields.get('description') or '',
            category=row['event_type'],
            format='virtual',
            publish_status='draft',
            visibility='public',
            start_date=start_pl,
            end_date=end_pl,
            capacity=0,
            base_price=0.0,
            cover_image=(fields.get('cover_image_wp_source') or '').strip() or None,
            created_by=uid,
        )
        db.session.add(ev)
        created += 1

    if created:
        db.session.commit()

    report['dry_run'] = False
    report['created'] = created
    return created, errors, report
