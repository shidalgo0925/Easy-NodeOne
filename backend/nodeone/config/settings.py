"""Configuración cargada desde el entorno (.env vía python-dotenv en wsgi / bootstrap)."""

import os
from pathlib import Path


def _base_dir() -> Path:
    raw = (os.getenv('BASE_DIR') or '').strip()
    if raw:
        return Path(raw).resolve()
    return Path('/var/www/nodeone').resolve()


class Settings:
    APP_NAME = (os.getenv('APP_NAME') or 'EasyNodeOne').strip() or 'EasyNodeOne'
    BASE_DIR = str(_base_dir())
    LICENSE_PATH = (os.getenv('LICENSE_PATH') or '/opt/nodeone/licenses').strip() or '/opt/nodeone/licenses'
    ENV = (os.getenv('ENV') or 'production').strip() or 'production'
    DATABASE_URL = (os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or '').strip()
    LOGO_BASENAME = (os.getenv('LOGO_BASENAME') or 'logo-primary').strip() or 'logo-primary'
    # CSV de nombres de org legados a normalizar (minúsculas); ej. tenant heredado de otra marca
    LEGACY_SAAS_ORG_NAMES = tuple(
        x.strip().lower() for x in (os.getenv('LEGACY_SAAS_ORG_NAMES') or '').split(',') if x.strip()
    )


settings = Settings()
