"""Regionalización y formatos por organización (presentación). No es configuración fiscal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from nodeone.core.timezone_service import COMMON_IANA_TIMEZONES, TimeZoneService

DATE_FORMATS = ('DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD')
TIME_FORMATS = ('12h', '24h')
WEEK_STARTS = ('monday', 'sunday')
NUMBER_FORMATS = ('1,234.56', '1.234,56')
SYMBOL_POSITIONS = ('before', 'after')
PAPER_SIZES = ('letter', 'a4')
ALLOWED_CURRENCIES = ('USD', 'PAB', 'EUR')
COUNTRY_CODES = (
    ('', '— (sin definir)'),
    ('PA', 'Panamá'),
    ('CO', 'Colombia'),
    ('MX', 'México'),
    ('US', 'Estados Unidos'),
    ('ES', 'España'),
    ('AR', 'Argentina'),
    ('PE', 'Perú'),
    ('CL', 'Chile'),
    ('CR', 'Costa Rica'),
    ('DO', 'República Dominicana'),
)

_SYMBOL_BY_CURRENCY = {'USD': '$', 'PAB': 'B/.', 'EUR': '€'}

# Perfil razonable solo cuando el usuario elige PA (no se aplica a todas las orgs).
PANAMA_PROFILE = {
    'country_code': 'PA',
    'timezone': 'America/Panama',
    'date_format': 'DD/MM/YYYY',
    'time_format': '24h',
    'week_start': 'monday',
    'number_format': '1,234.56',
    'money_decimals': 2,
    'qty_decimals': 2,
    'currency_code': 'USD',
    'currency_symbol': '$',
    'symbol_position': 'before',
    'locale': 'es_PA',
    'paper_size': 'letter',
}


@dataclass(frozen=True)
class RegionalSettingsDTO:
    organization_id: int
    country_code: str | None
    timezone: str
    date_format: str
    time_format: str
    week_start: str
    number_format: str
    money_decimals: int
    qty_decimals: int
    currency_code: str
    currency_symbol: str
    symbol_position: str
    locale: str
    paper_size: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'organization_id': self.organization_id,
            'country_code': self.country_code,
            'timezone': self.timezone,
            'date_format': self.date_format,
            'time_format': self.time_format,
            'week_start': self.week_start,
            'number_format': self.number_format,
            'money_decimals': self.money_decimals,
            'qty_decimals': self.qty_decimals,
            'currency_code': self.currency_code,
            'currency_symbol': self.currency_symbol,
            'symbol_position': self.symbol_position,
            'locale': self.locale,
            'paper_size': self.paper_size,
        }


def parse_localized_number(text: str, number_format: str = '1,234.56') -> float | None:
    """Interpreta un número escrito según el formato de la org. No cambia el valor contable."""
    raw = (text or '').strip()
    if not raw:
        return None
    for token in ('B/.', 'USD', 'PAB', 'EUR', '$', '€'):
        raw = raw.replace(token, '')
    raw = raw.replace('\xa0', '').replace(' ', '')
    if not raw or raw in {'.', ',', '-', '+'}:
        return None
    nf = (number_format or '1,234.56').strip()
    try:
        if nf == '1.234,56':
            if ',' in raw:
                raw = raw.replace('.', '').replace(',', '.')
            elif raw.count('.') > 1:
                raw = raw.replace('.', '')
            elif raw.count('.') == 1:
                left, right = raw.split('.')
                if len(right) == 3 and left.isdigit():
                    raw = left + right
        else:
            if raw.count(',') == 1 and raw.count('.') == 0:
                raw = raw.replace(',', '.')
            else:
                raw = raw.replace(',', '')
        return float(raw)
    except ValueError:
        return None


def default_regional_dict() -> dict[str, Any]:
    return {
        'country_code': None,
        'timezone': 'America/Panama',
        'date_format': 'DD/MM/YYYY',
        'time_format': '24h',
        'week_start': 'monday',
        'number_format': '1,234.56',
        'money_decimals': 2,
        'qty_decimals': 2,
        'currency_code': 'USD',
        'currency_symbol': '$',
        'symbol_position': 'before',
        'locale': 'es',
        'paper_size': 'a4',
    }


def format_plain_number(
    value: Any,
    *,
    number_format: str = '1,234.56',
    decimals: int = 2,
) -> str:
    """Presenta un número. No altera el valor almacenado."""
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        n = 0.0
    d = min(6, max(0, int(decimals)))
    sign = '-' if n < 0 else ''
    q = f'{abs(n):.{d}f}'
    if d == 0:
        intp, frac = q, ''
    else:
        intp, _, frac = q.partition('.')
    groups: list[str] = []
    while intp:
        groups.append(intp[-3:])
        intp = intp[:-3]
    nf = (number_format or '1,234.56').strip()
    if nf == '1.234,56':
        sep_t, sep_d = '.', ','
    else:
        sep_t, sep_d = ',', '.'
    joined = sep_t.join(reversed(groups)) if groups else '0'
    if d:
        return f'{sign}{joined}{sep_d}{frac}'
    return f'{sign}{joined}'


def format_money(
    value: Any,
    *,
    number_format: str = '1,234.56',
    decimals: int = 2,
    symbol: str = '$',
    symbol_position: str = 'before',
) -> str:
    num = format_plain_number(value, number_format=number_format, decimals=decimals)
    sy = (symbol or '$').strip() or '$'
    if (symbol_position or 'before') == 'after':
        return f'{num} {sy}'
    return f'{sy} {num}'


def format_money_from_cfg(value: Any, cfg: dict[str, Any] | None) -> str:
    c = dict(default_regional_dict())
    if isinstance(cfg, dict):
        c.update(cfg)
    return format_money(
        value,
        number_format=str(c.get('number_format') or '1,234.56'),
        decimals=int(c.get('money_decimals') if c.get('money_decimals') is not None else 2),
        symbol=str(c.get('currency_symbol') or '$'),
        symbol_position=str(c.get('symbol_position') or 'before'),
    )


def format_date_from_cfg(value: Any, cfg: dict[str, Any] | None) -> str:
    """Presenta fecha según date_format de la org. No convierte zona horaria de persistencia."""
    if value is None or value == '':
        return ''
    dt = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ''
        try:
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return raw
    d = dt.date() if isinstance(dt, datetime) else dt
    c = dict(default_regional_dict())
    if isinstance(cfg, dict):
        c.update(cfg)
    fmt = str(c.get('date_format') or 'DD/MM/YYYY')
    if fmt == 'MM/DD/YYYY':
        return f'{d.month:02d}/{d.day:02d}/{d.year:04d}'
    if fmt == 'YYYY-MM-DD':
        return f'{d.year:04d}-{d.month:02d}-{d.day:02d}'
    return f'{d.day:02d}/{d.month:02d}/{d.year:04d}'


def format_datetime_from_cfg(value: Any, cfg: dict[str, Any] | None) -> str:
    """Fecha + hora según regional (date_format + time_format)."""
    if value is None or value == '':
        return ''
    dt = value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ''
        try:
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return raw
    if not isinstance(dt, datetime):
        return format_date_from_cfg(dt, cfg)
    date_s = format_date_from_cfg(dt, cfg)
    c = dict(default_regional_dict())
    if isinstance(cfg, dict):
        c.update(cfg)
    if str(c.get('time_format') or '24h') == '12h':
        h = dt.hour % 12 or 12
        ampm = 'a. m.' if dt.hour < 12 else 'p. m.'
        return f'{date_s} {h}:{dt.minute:02d} {ampm}'
    return f'{date_s} {dt.hour:02d}:{dt.minute:02d}'


def _to_dto(row) -> RegionalSettingsDTO:
    cc = (getattr(row, 'country_code', None) or '').strip() or None
    return RegionalSettingsDTO(
        organization_id=int(row.organization_id),
        country_code=cc,
        timezone=TimeZoneService.validate_iana(row.timezone),
        date_format=str(row.date_format or 'DD/MM/YYYY'),
        time_format=str(row.time_format or '24h'),
        week_start=str(row.week_start or 'monday'),
        number_format=str(row.number_format or '1,234.56'),
        money_decimals=int(row.money_decimals if row.money_decimals is not None else 2),
        qty_decimals=int(row.qty_decimals if row.qty_decimals is not None else 2),
        currency_code=str(row.currency_code or 'USD').upper(),
        currency_symbol=str(row.currency_symbol or '$'),
        symbol_position=str(row.symbol_position or 'before'),
        locale=str(row.locale or 'es'),
        paper_size=str(row.paper_size or 'a4'),
    )


class RegionalFormatService:
    @staticmethod
    def get(organization_id: int) -> RegionalSettingsDTO | None:
        from models.org_regional import OrganizationRegionalSettings

        row = OrganizationRegionalSettings.query.filter_by(organization_id=int(organization_id)).first()
        return _to_dto(row) if row is not None else None

    @staticmethod
    def get_or_create(organization_id: int, *, commit: bool = True) -> RegionalSettingsDTO:
        from models.org_regional import OrganizationRegionalSettings
        from models.saas import SaasOrganization
        from nodeone.core.db import db
        from nodeone.services.org_regional_schema import ensure_organization_regional_settings_schema

        ensure_organization_regional_settings_schema(db, db.engine)
        oid = int(organization_id)
        row = OrganizationRegionalSettings.query.filter_by(organization_id=oid).first()
        if row is not None:
            return _to_dto(row)
        org = SaasOrganization.query.get(oid)
        tz = TimeZoneService.org_timezone_name(org)
        currency = 'USD'
        try:
            from models.eposone_settings import EposoneSettings

            erow = EposoneSettings.query.filter_by(organization_id=oid).first()
            if erow and erow.default_currency:
                currency = str(erow.default_currency).upper()
        except Exception:
            pass
        if currency not in ALLOWED_CURRENCIES:
            currency = 'USD'
        row = OrganizationRegionalSettings(
            organization_id=oid,
            country_code=None,
            timezone=tz,
            date_format='DD/MM/YYYY',
            time_format='24h',
            week_start='monday',
            number_format='1,234.56',
            money_decimals=2,
            qty_decimals=2,
            currency_code=currency,
            currency_symbol=_SYMBOL_BY_CURRENCY.get(currency, '$'),
            symbol_position='before',
            locale='es',
            paper_size='a4',
        )
        db.session.add(row)
        if commit:
            db.session.commit()
        return _to_dto(row)

    @staticmethod
    def apply_payload(organization_id: int, data: dict[str, Any]) -> RegionalSettingsDTO:
        from models.org_regional import OrganizationRegionalSettings
        from models.saas import SaasOrganization
        from nodeone.core.db import db
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        dto = RegionalFormatService.get_or_create(organization_id, commit=False)
        oid = int(organization_id)
        row = OrganizationRegionalSettings.query.filter_by(organization_id=oid).first()
        if row is None:
            raise RuntimeError('regional settings missing')

        cc = str(data.get('country_code') or '').strip().upper()[:8]
        row.country_code = cc or None
        row.timezone = TimeZoneService.validate_iana(data.get('timezone'))
        df = str(data.get('date_format') or '').strip()
        row.date_format = df if df in DATE_FORMATS else 'DD/MM/YYYY'
        tf = str(data.get('time_format') or '').strip()
        row.time_format = tf if tf in TIME_FORMATS else '24h'
        ws = str(data.get('week_start') or '').strip()
        row.week_start = ws if ws in WEEK_STARTS else 'monday'
        nf = str(data.get('number_format') or '').strip()
        row.number_format = nf if nf in NUMBER_FORMATS else '1,234.56'
        try:
            md = int(data.get('money_decimals'))
        except (TypeError, ValueError):
            md = 2
        try:
            qd = int(data.get('qty_decimals'))
        except (TypeError, ValueError):
            qd = 2
        row.money_decimals = min(6, max(0, md))
        row.qty_decimals = min(6, max(0, qd))
        cur = str(data.get('currency_code') or 'USD').strip().upper()[:8]
        row.currency_code = cur if cur in ALLOWED_CURRENCIES else 'USD'
        sym = str(data.get('currency_symbol') or '').strip()[:16]
        row.currency_symbol = sym or _SYMBOL_BY_CURRENCY.get(row.currency_code, '$')
        sp = str(data.get('symbol_position') or '').strip()
        row.symbol_position = sp if sp in SYMBOL_POSITIONS else 'before'
        loc = str(data.get('locale') or '').strip()[:16]
        row.locale = loc or ('es_PA' if row.country_code == 'PA' else 'es')
        paper = str(data.get('paper_size') or '').strip().lower()
        row.paper_size = paper if paper in PAPER_SIZES else 'a4'
        row.updated_at = datetime.utcnow()

        org = SaasOrganization.query.get(oid)
        if org is not None:
            org.timezone = row.timezone
        try:
            EposoneSettingsService.update_settings(oid, default_currency=row.currency_code)
        except Exception:
            pass
        db.session.commit()
        return _to_dto(row)

    @staticmethod
    def sync_ops(organization_id: int, *, timezone: str | None = None, currency: str | None = None) -> None:
        """Cuando EPosOne/plataforma cambia TZ o moneda, alinea la fila regional si existe."""
        from models.org_regional import OrganizationRegionalSettings
        from nodeone.core.db import db

        row = OrganizationRegionalSettings.query.filter_by(organization_id=int(organization_id)).first()
        if row is None:
            return
        if timezone:
            row.timezone = TimeZoneService.validate_iana(timezone)
        if currency:
            cur = str(currency).strip().upper()
            if cur in ALLOWED_CURRENCIES:
                row.currency_code = cur
                if not (row.currency_symbol or '').strip():
                    row.currency_symbol = _SYMBOL_BY_CURRENCY.get(cur, '$')
        row.updated_at = datetime.utcnow()
        db.session.flush()
