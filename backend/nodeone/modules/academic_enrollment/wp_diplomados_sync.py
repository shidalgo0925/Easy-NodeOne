"""Sincronización diplomados IIUS: WordPress (pág. 212) ↔ AcademicProgram.

Índice único del árbol Elementor por slug; pull y push comparten la misma estructura.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from typing import Any

from models.academic_program import format_start_date_es

WP_DIPLOMADOS_PAGE_ID = 212
WP_ROOT = '/var/www/wordpress'
WP_CLI_BIN = '/usr/local/bin/wp'
SUDO_BIN = '/usr/bin/sudo'

# Los 4 bloques de la página WordPress /diplomados/ (Elementor pág. 212). No otros slugs.
DIPLOMADO_SLUGS: tuple[str, ...] = (
    'neuro-liderazgo-intercultural',
    'neuro-descodificacion-psicogenealogia-pnl',
    'neuro-teologia-coaching-cristiano-transgeneracional',
    'neuro-heuristica-coaching-vida',
)
WP_DIPLOMADO_SLUGS: frozenset[str] = frozenset(DIPLOMADO_SLUGS)


def is_wp_diplomado_slug(slug: str | None) -> bool:
    return (slug or '').strip().lower() in WP_DIPLOMADO_SLUGS

_TITLE_TO_SLUG: tuple[tuple[str, str], ...] = (
    ('neuro-liderazgo', 'neuro-liderazgo-intercultural'),
    ('decodific', 'neuro-descodificacion-psicogenealogia-pnl'),
    ('teolog', 'neuro-teologia-coaching-cristiano-transgeneracional'),
    ('heur', 'neuro-heuristica-coaching-vida'),
)

_MONTHS_ES = {
    'enero': 1,
    'febrero': 2,
    'marzo': 3,
    'abril': 4,
    'mayo': 5,
    'junio': 6,
    'julio': 7,
    'agosto': 8,
    'septiembre': 9,
    'octubre': 10,
    'noviembre': 11,
    'diciembre': 12,
}


# --- WP-CLI -----------------------------------------------------------------


def _apps_public_base() -> str:
    return (os.environ.get('NODEONE_PUBLIC_BASE_URL') or 'https://apps.internationalinstitute.us').rstrip('/')


def _wp_cli_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if isinstance(v, str)}
    env['PATH'] = '/usr/local/bin:/usr/bin:/bin'
    env.setdefault('WP_CLI_CACHE_DIR', '/var/www/.wp-cli/cache')
    return env


def _run_wp_cli(wp_args: list[str]) -> subprocess.CompletedProcess[str]:
    env = _wp_cli_env()
    last: subprocess.CompletedProcess[str] | None = None
    for as_www in (False, True):
        cmd = [WP_CLI_BIN, *wp_args, f'--path={WP_ROOT}']
        if as_www:
            if not os.path.isfile(SUDO_BIN):
                break
            cmd = [SUDO_BIN, '-u', 'www-data', *cmd]
        try:
            last = subprocess.run(cmd, capture_output=True, text=True, env=env)
        except FileNotFoundError as e:
            if as_www:
                raise RuntimeError(f'WP-CLI no disponible: {e}') from e
            continue
        if last.returncode == 0:
            return last
    assert last is not None
    return last


def _load_elementor_data() -> list:
    proc = _run_wp_cli(['post', 'meta', 'get', str(WP_DIPLOMADOS_PAGE_ID), '_elementor_data'])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli falló')
    raw = (proc.stdout or '').strip()
    if not raw or raw == '[]':
        raise RuntimeError('Elementor vacío en página diplomados WP')
    return json.loads(raw)


def _save_elementor_data(data: list) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    proc = _run_wp_cli(
        ['post', 'meta', 'update', str(WP_DIPLOMADOS_PAGE_ID), '_elementor_data', payload],
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'wp-cli update falló')
    _run_wp_cli(['elementor', 'flush-css'])


# --- Utilidades texto / slug ------------------------------------------------


def _strip_html(html: str) -> str:
    s = re.sub(r'<br\s*/?>', '\n', html or '', flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return unescape(re.sub(r'\s+', ' ', s)).strip()


def _parse_start_date_es(text: str) -> datetime | None:
    t = _strip_html(text).lower()
    m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', t)
    if not m:
        return None
    month = _MONTHS_ES.get(m.group(2))
    if not month:
        return None
    return datetime(int(m.group(3)), month, int(m.group(1)))


def _slug_from_title(title: str) -> str | None:
    low = (title or '').lower()
    for needle, slug in _TITLE_TO_SLUG:
        if needle in low:
            return slug
    return None


def _is_page_header_title(title: str) -> bool:
    t = title.lower()
    return 'diplomados internacionales' in t and 'neuro' in t and 'ciencia aplicados' in t


def _heading_slug(title: str) -> str | None:
    title = (title or '').strip()
    if not title or _is_page_header_title(title):
        return None
    if title.lower().strip() in ('diplomados', 'diplomado'):
        return None
    if 'diplomado' not in title.lower():
        return None
    return _slug_from_title(title)


def _is_fecha_text(plain_lower: str) -> bool:
    return 'próximo inicio' in plain_lower or 'proximo inicio' in plain_lower


def _html_fecha(dt: datetime) -> str:
    label = format_start_date_es(dt) or ''
    return f'<p class="iius-fecha-inicio-diplomado"><strong>Próximo inicio:</strong> {label}</p>'


def _html_enfoques(key_focuses: str | None, ideal_for: str | None) -> str:
    parts = []
    if key_focuses:
        parts.append(f'<strong>Enfoques clave:</strong> {key_focuses}.')
    if ideal_for:
        parts.append(f'<br><strong>Ideal para:</strong> {ideal_for}.')
    return f'<p>{"".join(parts)}</p>' if parts else ''


# --- Árbol Elementor ----------------------------------------------------------


def _walk_nodes(nodes: list, acc: list[dict]) -> None:
    for node in nodes or []:
        if isinstance(node, dict):
            acc.append(node)
            _walk_nodes(node.get('elements') or [], acc)


def _node_settings(node: dict) -> dict:
    st = node.get('settings')
    if not isinstance(st, dict):
        st = {}
        node['settings'] = st
    return st


def _patch_image_widget(node: dict, url: str) -> None:
    if '_qr' in url.lower():
        return
    st = _node_settings(node)
    prev = st.get('image') if isinstance(st.get('image'), dict) else {}
    st['image'] = {
        'id': '',
        'url': url,
        'source': 'url',
        'size': '',
        'alt': prev.get('alt') or '',
    }


def _patch_background(node: dict, url: str) -> None:
    st = _node_settings(node)
    for key in ('background_image', 'background_image_tablet', 'background_image_mobile'):
        bg = st.get(key)
        if isinstance(bg, dict) and (bg.get('url') or bg.get('id')):
            st[key] = {**bg, 'url': url}


def _first_image_in_subtree(node: dict) -> dict | None:
    if node.get('widgetType') == 'image':
        return node
    for ch in node.get('elements') or []:
        if isinstance(ch, dict) and (found := _first_image_in_subtree(ch)):
            return found
    return None


def _slug_in_subtree(node: dict) -> str | None:
    if node.get('widgetType') == 'heading':
        return _heading_slug((node.get('settings') or {}).get('title') or '')
    for ch in node.get('elements') or []:
        if isinstance(ch, dict) and (s := _slug_in_subtree(ch)):
            return s
    return None


def _has_background(st: dict) -> bool:
    for key in ('background_image', 'background_image_tablet', 'background_image_mobile'):
        bg = st.get(key)
        if isinstance(bg, dict) and (bg.get('url') or bg.get('id')):
            return True
    return False


# --- Sección por diplomado ----------------------------------------------------


@dataclass
class _WpSection:
    slug: str
    heading: dict | None = None
    fechas: list[dict] = field(default_factory=list)
    marketing_tag_node: dict | None = None
    enfoques_node: dict | None = None
    long_desc_nodes: list[dict] = field(default_factory=list)
    cta_button: dict | None = None
    image_nodes: list[dict] = field(default_factory=list)
    bg_nodes: list[dict] = field(default_factory=list)
    # Solo pull (widgets antes del título del bloque)
    pull_tag: str | None = None
    pull_fecha: datetime | None = None

    def attach_pending_fechas(self, pending: list[dict]) -> None:
        self.fechas.extend(pending)

    def register_image(self, node: dict) -> None:
        if node not in self.image_nodes:
            self.image_nodes.append(node)

    def register_background(self, node: dict) -> None:
        if node not in self.bg_nodes:
            self.bg_nodes.append(node)

    def to_pull_block(self) -> dict[str, Any]:
        name = ''
        if self.heading:
            name = (_node_settings(self.heading).get('title') or '').strip()
        start_date = self.pull_fecha
        for node in self.fechas:
            if dt := _parse_start_date_es((_node_settings(node).get('editor') or '')):
                start_date = dt
                break
        long_parts = [_strip_html((_node_settings(n).get('editor') or '')) for n in self.long_desc_nodes]
        long_description = '\n\n'.join(p for p in long_parts if p).strip() or None
        key_focuses = ideal_for = None
        if self.enfoques_node:
            plain = _strip_html((_node_settings(self.enfoques_node).get('editor') or ''))
            m_ef = re.search(r'enfoques clave:\s*(.+?)(?:ideal para:|$)', plain, re.I | re.S)
            m_id = re.search(r'ideal para:\s*(.+?)$', plain, re.I | re.S)
            if m_ef:
                key_focuses = m_ef.group(1).strip().rstrip('.')
            if m_id:
                ideal_for = m_id.group(1).strip().rstrip('.')
        cta_label = None
        if self.cta_button:
            cta_label = (_node_settings(self.cta_button).get('text') or '').strip() or None
        image_wp_landing = _first_media_url(self.image_nodes, self.bg_nodes)
        marketing_tag = self.pull_tag
        if not marketing_tag and self.marketing_tag_node:
            plain_tag = _strip_html((_node_settings(self.marketing_tag_node).get('editor') or ''))
            if plain_tag and len(plain_tag) < 80 and 'aprenderás' not in plain_tag.lower():
                marketing_tag = plain_tag
        return {
            'slug': self.slug,
            'name': name,
            'marketing_tag': marketing_tag,
            'start_date': start_date,
            'long_description': long_description,
            'key_focuses': key_focuses,
            'ideal_for': ideal_for,
            'cta_label': cta_label,
            'image_wp_landing': image_wp_landing,
        }

    def apply_program(self, program, *, media_base: str) -> None:
        from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

        if self.heading and program.name:
            _node_settings(self.heading)['title'] = program.name

        if program.start_date:
            html = _html_fecha(program.start_date)
            for node in self.fechas:
                _node_settings(node)['editor'] = html

        if self.enfoques_node:
            html = _html_enfoques(program.key_focuses, program.ideal_for)
            if html:
                _node_settings(self.enfoques_node)['editor'] = html

        if self.marketing_tag_node and program.marketing_tag:
            plain = _strip_html((_node_settings(self.marketing_tag_node).get('editor') or '')).lower()
            if len(plain) < 80 and 'aprenderás' not in plain:
                _node_settings(self.marketing_tag_node)['editor'] = f'<p>{program.marketing_tag}</p>'

        if program.long_description and self.long_desc_nodes:
            paras = [p.strip() for p in program.long_description.split('\n\n') if p.strip()]
            html = ''.join(f'<p>{p}</p>' for p in paras[:2])
            for node in self.long_desc_nodes:
                plain = _strip_html((_node_settings(node).get('editor') or '')).lower()
                if 'aprenderás' in plain or len(plain) > 90:
                    _node_settings(node)['editor'] = html

        if self.cta_button and program.cta_label:
            _node_settings(self.cta_button)['text'] = program.cta_label

        # Solo ① image_wp_landing — sin fallback a flyer/catálogo (evita pisar con URL WP vieja).
        landing_path = (getattr(program, 'image_wp_landing', None) or '').strip()
        landing_url = absolute_public_asset_url(landing_path, external_base=media_base) if landing_path else None
        if landing_url and '_qr' not in landing_url.lower():
            for node in self.image_nodes:
                _patch_image_widget(node, landing_url)
            for node in self.bg_nodes:
                _patch_background(node, landing_url)


def _first_media_url(image_nodes: list[dict], bg_nodes: list[dict]) -> str | None:
    for node in image_nodes:
        st = node.get('settings') or {}
        url = (st.get('image') or {}).get('url') if isinstance(st.get('image'), dict) else None
        if url and 'uploads' in str(url) and '_qr' not in str(url).lower():
            return str(url).strip()
    for node in bg_nodes:
        st = node.get('settings') or {}
        for key in ('background_image', 'background_image_tablet', 'background_image_mobile'):
            bg = st.get(key)
            if isinstance(bg, dict) and (u := (bg.get('url') or '').strip()) and 'uploads' in u:
                return u
    return None


def _index_row_images(data: list, sections: dict[str, _WpSection]) -> None:
    """Columna imagen hermana de la fila (layout 50/50 en pág. 212)."""

    def visit(nodes: list) -> None:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            children = [c for c in (node.get('elements') or []) if isinstance(c, dict)]
            # Fila 50/50: dos columnas contenedor (texto + imagen), no el bloque interno de widgets.
            if (
                node.get('elType') == 'container'
                and len(children) >= 2
                and all(c.get('elType') == 'container' for c in children)
            ):
                slug: str | None = None
                image_node: dict | None = None
                for ch in children:
                    if s := _slug_in_subtree(ch):
                        slug = s
                    if img := _first_image_in_subtree(ch):
                        image_node = img
                if slug and image_node and slug in sections:
                    sections[slug].register_image(image_node)
            visit(node.get('elements') or [])

    visit(data)


def _index_sections(data: list) -> dict[str, _WpSection]:
    sections: dict[str, _WpSection] = {}
    pending_fechas: list[dict] = []
    fechas_after: dict[str, int] = {}
    current_slug: str | None = None
    pull_tag: str | None = None
    pull_fecha: datetime | None = None

    flat: list[dict] = []
    _walk_nodes(data, flat)

    for node in flat:
        wt = node.get('widgetType') or ''
        st = _node_settings(node)

        if wt == 'heading':
            slug = _heading_slug((st.get('title') or '').strip())
            if not slug:
                continue
            if slug not in sections:
                sections[slug] = _WpSection(slug=slug, pull_tag=pull_tag, pull_fecha=pull_fecha)
            sec = sections[slug]
            sec.attach_pending_fechas(pending_fechas)
            pending_fechas = []
            sec.heading = node
            pull_tag = None
            pull_fecha = None
            fechas_after[slug] = 0
            current_slug = slug
            continue

        if wt == 'text-editor':
            html = st.get('editor') or ''
            plain = _strip_html(html)
            low = plain.lower()
            if _is_fecha_text(low):
                if current_slug and current_slug in sections and fechas_after.get(current_slug, 0) == 0:
                    sections[current_slug].fechas.append(node)
                    fechas_after[current_slug] = 1
                else:
                    pending_fechas.append(node)
                    if dt := _parse_start_date_es(html):
                        pull_fecha = dt
                continue
            if current_slug and current_slug in sections:
                sec = sections[current_slug]
                if 'enfoques clave' in low:
                    sec.enfoques_node = node
                elif 'aprenderás' in low or len(plain) > 90:
                    sec.long_desc_nodes.append(node)
                elif len(plain) < 80:
                    sec.marketing_tag_node = node
            elif len(plain) < 90 and 'enfoques clave' not in low and 'aprenderás' not in low:
                pull_tag = plain
            continue

        if current_slug and current_slug in sections:
            sec = sections[current_slug]
            if wt == 'button':
                sec.cta_button = node
            if _has_background(st):
                sec.register_background(node)

    _index_row_images(data, sections)
    for sec in sections.values():
        sec.image_nodes = [n for n in sec.image_nodes if not _image_is_qr(n)]
    return sections


def _image_is_qr(node: dict) -> bool:
    url = ((_node_settings(node).get('image') or {}).get('url') or '').lower()
    return '_qr' in url


class _DiplomadosElementorPage:
    def __init__(self, data: list | None = None) -> None:
        self.data = data if data is not None else _load_elementor_data()
        self.sections = _index_sections(self.data)

    def pull_blocks(self) -> list[dict[str, Any]]:
        return [self.sections[s].to_pull_block() for s in DIPLOMADO_SLUGS if s in self.sections]

    def push(self, programs: list) -> int:
        by_slug = {(p.slug or '').strip().lower(): p for p in programs}
        media_base = _apps_public_base()
        n = 0
        for slug, sec in self.sections.items():
            if slug in by_slug:
                sec.apply_program(by_slug[slug], media_base=media_base)
                n += 1
        self.save()
        return n

    def save(self) -> None:
        _save_elementor_data(self.data)


# --- API pública ------------------------------------------------------------


def pull_diplomados_from_wp(organization_id: int, db) -> tuple[int, list[str]]:
    from models.academic_program import AcademicProgram

    errors: list[str] = []
    page = _DiplomadosElementorPage()
    blocks = page.pull_blocks()
    if len(blocks) < 4:
        errors.append(f'Solo se detectaron {len(blocks)} bloques en WP (se esperan 4).')

    updated = 0
    for sort_idx, block in enumerate(blocks, start=1):
        slug = block.get('slug')
        if not slug:
            continue
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if not row:
            errors.append(f'No existe en apps: {slug}')
            continue
        row.catalog_sort_order = sort_idx
        if block.get('name'):
            row.name = block['name']
        if block.get('marketing_tag'):
            row.marketing_tag = block['marketing_tag']
        if block.get('start_date'):
            row.start_date = block['start_date']
        if block.get('long_description'):
            row.long_description = block['long_description']
        if block.get('key_focuses'):
            row.key_focuses = block['key_focuses']
        if block.get('ideal_for'):
            row.ideal_for = block['ideal_for']
        if block.get('cta_label'):
            row.cta_label = block['cta_label']
        if block.get('image_wp_landing'):
            row.image_wp_landing = block['image_wp_landing']
        updated += 1

    db.session.commit()
    return updated, errors


def push_program_slug_to_wp(organization_id: int, slug: str) -> tuple[bool, str | None]:
    from models.academic_program import AcademicProgram

    slug = (slug or '').strip().lower()
    if slug not in DIPLOMADO_SLUGS:
        return False, 'Este programa no está en la página WP de diplomados (solo los 4 neuro).'
    row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
    if row is None:
        return False, f'No existe el programa «{slug}» en apps.'
    _DiplomadosElementorPage().push([row])
    return True, None


def push_diplomados_to_wp(organization_id: int) -> tuple[int, list[str]]:
    from models.academic_program import AcademicProgram

    errors: list[str] = []
    programs = []
    for slug in DIPLOMADO_SLUGS:
        row = AcademicProgram.query.filter_by(organization_id=int(organization_id), slug=slug).first()
        if row:
            programs.append(row)
        else:
            errors.append(f'Falta en apps: {slug}')
    if not programs:
        return 0, errors
    n = _DiplomadosElementorPage().push(programs)
    return n, errors
