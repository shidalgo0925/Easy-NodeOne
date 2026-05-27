#!/usr/bin/env python3
"""Restaura Cursos de Arte: Apps (4 curso-en-*) + recableo WP #Cursos_arte (sin tocar otras secciones)."""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodeone.modules.academic_enrollment.catalog_public import (
    ARTE_CATEGORY,
    ARTE_SLUGS,
    ARTE_WP_CONTAINER_IDS,
    ARTE_WP_SECTION_TITLES,
)
from nodeone.modules.academic_enrollment.wp_cursos_sync import (
    _load_elementor_data,
    _node_settings,
    _save_elementor_data,
)
from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
    _apps_public_base,
    _patch_image_widget,
    _strip_html,
    _walk_nodes,
)


def _normalize_element_id(raw: str | None) -> str:
    import re

    return re.sub(r'[^a-z0-9]+', '_', (raw or '').strip().lower()).strip('_')


def _inscripcion_url(slug: str) -> str:
    return f'{_apps_public_base()}/inscripcion/{slug.strip().lower()}'


def _collect_arte_slots(data: list) -> list[dict]:
    """Tarjetas imagen+texto+botón dentro del contenedor Cursos_arte, en orden DOM."""
    flat: list[dict] = []
    _walk_nodes(data, flat)
    in_arte = False
    pending_image: dict | None = None
    pending_text: dict | None = None
    slots: list[dict] = []

    for node in flat:
        el = node.get('elType') or ''
        wt = node.get('widgetType') or ''
        st = _node_settings(node)
        eid = _normalize_element_id(st.get('_element_id'))

        if el in ('container', 'section') and eid in ARTE_WP_CONTAINER_IDS:
            in_arte = True
            pending_image = pending_text = None
            continue

        if wt == 'heading':
            title = (st.get('title') or '').strip()
            if title in ARTE_WP_SECTION_TITLES:
                in_arte = True
                pending_image = pending_text = None
            elif title in (
                'Cursos de Negocios',
                'Cursos en Ciencia',
                'Cursos en Espiritualidad',
                'Catálogo de Cursos y Programas',
                'Talleres',
            ):
                in_arte = False
            continue

        if not in_arte:
            continue

        if wt == 'image':
            url = (st.get('image') or {}).get('url') or ''
            if url and 'uploads' in url:
                pending_image = node
            continue

        if wt == 'text-editor':
            plain = _strip_html(st.get('editor') or '')
            if plain:
                pending_text = node
            continue

        if wt == 'button':
            slots.append(
                {
                    'image_node': pending_image,
                    'text_node': pending_text,
                    'button_node': node,
                }
            )
            pending_image = pending_text = None

    return slots


def _apply_program_to_slot(program, slot: dict, *, media_base: str) -> None:
    from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

    slug = (program.slug or '').strip().lower()
    if slot.get('text_node') and program.short_description:
        _node_settings(slot['text_node'])['editor'] = f'<p>{program.short_description.strip()}</p>'

    img_path = (program.image_url or '').strip()
    img_url = absolute_public_asset_url(img_path, external_base=media_base) if img_path else None
    if img_url and slot.get('image_node') and '_qr' not in img_url.lower():
        _patch_image_widget(slot['image_node'], img_url)

    btn = slot.get('button_node')
    if btn:
        st = _node_settings(btn)
        st['text'] = (program.cta_label or 'Ver más').strip() or 'Ver más'
        link = st.get('link')
        if not isinstance(link, dict):
            link = {}
            st['link'] = link
        link['url'] = _inscripcion_url(slug)


def main() -> int:
    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # 1) Apps
    subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'seed_iius_arte_slugs_apps.py'), str(org_id), '--force-images'],
        check=True,
    )

    from app import app, db
    from models.academic_program import AcademicProgram

    with app.app_context():
        programs = []
        for slug in ARTE_SLUGS:
            row = AcademicProgram.query.filter_by(organization_id=org_id, slug=slug, status='published').first()
            if not row:
                print(f'ERROR Apps: falta {slug}')
                return 1
            row.category = ARTE_CATEGORY
            row.program_type = 'curso'
            programs.append(row)
        db.session.commit()

        # Quitar basura en categoría Arte (slugs que no son los 4 canónicos)
        stray = [
            r
            for r in AcademicProgram.query.filter_by(organization_id=org_id, category=ARTE_CATEGORY).all()
            if (r.slug or '') not in ARTE_SLUGS
        ]
        for row in stray:
            print(f'Archivando fuera de catálogo arte: {row.slug}')
            row.status = 'archived'
            row.category = None
        db.session.commit()

        print('\n--- Apps (4 cursos de arte) ---')
        for p in sorted(programs, key=lambda x: x.catalog_sort_order):
            print(f'  {p.catalog_sort_order}. {p.name} | {p.slug}')

        # 2) WP solo bloque Cursos_arte
        data = _load_elementor_data()
        slots = _collect_arte_slots(data)
        print(f'\n--- WP: {len(slots)} tarjetas en #Cursos_arte ---')
        if len(slots) < 4:
            print(f'ERROR: se esperan 4 tarjetas en Elementor, hay {len(slots)}. Revisá el Div Cursos_arte.')
            return 1

        media_base = _apps_public_base()
        for i, slug in enumerate(ARTE_SLUGS):
            _apply_program_to_slot(programs[i], slots[i], media_base=media_base)
            btn_url = (_node_settings(slots[i]['button_node']).get('link') or {}).get('url', '')
            print(f'  {i + 1}. {programs[i].name} → {btn_url[-55:]}')

        _save_elementor_data(data)
        print('\nWP página 2006 actualizada (solo sección arte). Ctrl+F5 en /cursos-detalle/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
