"""Scaffold de apps nativas de plataforma — Etapa 9."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_APP_ID_RX = re.compile(r'^[a-z][a-z0-9_]{1,48}$')


@dataclass(frozen=True)
class ScaffoldSpec:
    app_id: str
    name: str
    saas_code: str
    nav_area_id: str
    lifecycle: str = 'planned'
    depends_on: tuple[str, ...] = ('contacts',)

    @property
    def module_pkg(self) -> str:
        return f'nodeone.modules.{self.app_id}'

    @property
    def register_fn(self) -> str:
        return f'register_{self.app_id}_blueprints'

    @property
    def blueprint_name(self) -> str:
        return self.app_id

    @property
    def home_endpoint(self) -> str:
        return f'{self.app_id}.{self.app_id}_home'


def normalize_app_id(raw: str) -> str:
    app_id = (raw or '').strip().lower().replace('-', '_')
    if not _APP_ID_RX.match(app_id):
        raise ValueError('app_id inválido: use minúsculas, números o _ (2–49 chars, empieza con letra)')
    return app_id


def build_scaffold_spec(
    *,
    app_id: str,
    name: str | None = None,
    saas_code: str | None = None,
    nav_area_id: str | None = None,
    lifecycle: str = 'planned',
    depends_on: tuple[str, ...] | None = None,
) -> ScaffoldSpec:
    aid = normalize_app_id(app_id)
    lc = (lifecycle or 'planned').strip().lower()
    if lc not in ('planned', 'active'):
        raise ValueError('lifecycle debe ser planned o active')
    dep = depends_on if depends_on is not None else ('contacts',)
    display = (name or aid.replace('_', ' ').title()).strip()
    saas = (saas_code or aid).strip().lower()
    nav = (nav_area_id or aid).strip().lower()
    return ScaffoldSpec(
        app_id=aid,
        name=display,
        saas_code=saas,
        nav_area_id=nav,
        lifecycle=lc,
        depends_on=dep,
    )


def _manifest_py(spec: ScaffoldSpec) -> str:
    dep_repr = repr(spec.depends_on)
    lines = [
        f'"""{spec.name} — app nativa de plataforma (scaffold Etapa 9)."""',
        '',
        'MODULE = {',
        f"    'id': '{spec.app_id}',",
        f"    'name': '{spec.name}',",
        f"    'saas_codes': ('{spec.saas_code}',),",
        f"    'nav_area_id': '{spec.nav_area_id}',",
        f"    'depends_on': {dep_repr},",
        "    'native_platform': True,",
        f"    'lifecycle': '{spec.lifecycle}',",
        f"    'register': '{spec.module_pkg}.register.{spec.register_fn}',",
        f"    'zone_blueprints': ('{spec.blueprint_name}',),",
        f"    'zone_path_prefixes': ('/admin/{spec.app_id}',),",
        f"    'zone_endpoints': ('{spec.home_endpoint}',),",
        "    'notes': (",
        "        'App nativa Carril 2 — solo Core; sin importar otras apps de negocio.',",
        "        'Publicar cambios de dominio vía bus de eventos (Etapa 8).',",
        '    ),',
        '}',
        '',
    ]
    return '\n'.join(lines)


def _register_py(spec: ScaffoldSpec) -> str:
    skip_env = f'NODEONE_SKIP_{spec.app_id.upper()}_MODULE'
    return f'''"""Registro de blueprints {spec.name}."""

from __future__ import annotations

import os


def {spec.register_fn}(app) -> None:
    if os.environ.get('{skip_env}', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from {spec.module_pkg}.routes import {spec.blueprint_name}_bp
        from saas_features import register_simple_saas_guard

        if '{spec.blueprint_name}' not in app.blueprints:
            register_simple_saas_guard({spec.blueprint_name}_bp, '{spec.saas_code}')
            app.register_blueprint({spec.blueprint_name}_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar {spec.blueprint_name}_bp: {{e}}')
'''


def _routes_py(spec: ScaffoldSpec) -> str:
    return f'''"""Rutas HTML de {spec.name} (app nativa — scaffold)."""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

{spec.blueprint_name}_bp = Blueprint('{spec.blueprint_name}', __name__, url_prefix='/admin/{spec.app_id}')


@{spec.blueprint_name}_bp.route('/')
@login_required
def {spec.app_id}_home():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    return render_template('{spec.app_id}/home.html')
'''


def _init_py(spec: ScaffoldSpec) -> str:
    return f'"""Paquete {spec.name} — app nativa de plataforma."""\n'


def _home_html(spec: ScaffoldSpec) -> str:
    return f'''{{% extends "base.html" %}}

{{% block title %}}{spec.name} | {{{{ get_nav_brand_name() }}}}{{% endblock %}}

{{% block page_content %}}
<div class="container-fluid py-3">
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <div>
            <h1 class="h4 mb-1">{spec.name}</h1>
            <p class="text-muted small mb-0">App nativa EasyNodeOne Platform — scaffold Etapa 9.</p>
        </div>
    </div>
    <div class="card border-0 shadow-sm">
        <div class="card-body">
            <h2 class="h6 text-uppercase text-muted mb-3">En construcción</h2>
            <p class="mb-0 text-muted small">
                Módulo SaaS <code>{spec.saas_code}</code>. Completar checklist en
                <code>/api/platform/apps/manifests/{spec.app_id}/checklist</code>.
            </p>
        </div>
    </div>
</div>
{{% endblock %}}
'''


def _test_py(spec: ScaffoldSpec) -> str:
    return f'''"""Tests {spec.name} — scaffold Etapa 9."""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class Test{spec.name.replace(" ", "")}Manifest(unittest.TestCase):
    def test_manifest_valid(self):
        from nodeone.core.platform.manifest_registry import load_manifest, validate_manifest

        m = load_manifest('{spec.module_pkg}.manifest')
        self.assertEqual(m['id'], '{spec.app_id}')
        self.assertEqual(validate_manifest(m), [])


if __name__ == '__main__':
    unittest.main()
'''


def scaffold_file_map(spec: ScaffoldSpec, *, app_root: Path) -> dict[Path, str]:
    backend = app_root / 'backend'
    module_dir = backend / 'nodeone' / 'modules' / spec.app_id
    return {
        module_dir / '__init__.py': _init_py(spec),
        module_dir / 'manifest.py': _manifest_py(spec),
        module_dir / 'register.py': _register_py(spec),
        module_dir / 'routes.py': _routes_py(spec),
        app_root / 'templates' / spec.app_id / 'home.html': _home_html(spec),
        backend / 'tests' / 'platform' / f'test_{spec.app_id}.py': _test_py(spec),
    }


def post_scaffold_instructions(spec: ScaffoldSpec) -> list[str]:
    manifest_path = f"nodeone.modules.{spec.app_id}.manifest"
    return [
        f"1. PLATFORM_MANIFEST_MODULES → añadir '{manifest_path}'",
        f"2. app_registry.py → ApplicationDescriptor(id='{spec.app_id}', saas_codes=('{spec.saas_code}',), ...)",
        f"3. saas_catalog_defaults.py → SAAS_CATALOG_MODULES += ('{spec.saas_code}', '{spec.name}', '...', False)",
        f"4. launcher.py NAV_AREA_TO_PLATFORM_APP → '{spec.nav_area_id}': '{spec.app_id}'",
        f"5. features.py + register_platform_apps → {spec.register_fn}(app)",
        f"6. Verificar GET /api/platform/apps/manifests/{spec.app_id}/checklist",
    ]


def write_scaffold(
    spec: ScaffoldSpec,
    *,
    app_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    files = scaffold_file_map(spec, app_root=app_root)
    existing = [str(p.relative_to(app_root)) for p in files if p.exists()]
    if existing and not force:
        raise FileExistsError(f'Archivos existentes (use --force): {", ".join(existing)}')

    written: list[str] = []
    if not dry_run:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            written.append(str(path.relative_to(app_root)))

    return {
        'app_id': spec.app_id,
        'dry_run': dry_run,
        'files': written if not dry_run else [str(p.relative_to(app_root)) for p in files],
        'instructions': post_scaffold_instructions(spec),
    }
