"""Procesa campañas programadas (status=scheduled, scheduled_at <= now). Ejecutar por cron cada 5-15 min."""
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db, MarketingCampaign, SaasOrganization, has_saas_module_enabled

with app.app_context():
    enabled_orgs = {
        o.id for o in SaasOrganization.query.all() if has_saas_module_enabled(o.id, 'marketing_email')
    }
    if not enabled_orgs:
        print('Ninguna organización tiene marketing_email activo; no se procesan campañas programadas.')
        sys.exit(0)

    from _app.modules.marketing.service import start_campaign

    now = datetime.utcnow()
    pending = MarketingCampaign.query.filter(
        MarketingCampaign.status == 'scheduled',
        MarketingCampaign.scheduled_at.isnot(None),
        MarketingCampaign.scheduled_at <= now,
    ).all()
    for c in pending:
        if int(getattr(c, 'organization_id', None) or 1) not in enabled_orgs:
            print(f'Campaña {c.id} ({c.name}): omitida (marketing off para org {getattr(c, "organization_id", 1)})')
            continue
        _, err = start_campaign(c.id)
        if err:
            print(f'Campaña {c.id} ({c.name}): {err}')
        else:
            print(f'Campaña {c.id} ({c.name}): enviada')
    print(f'Listo. {len(pending)} campañas en ventana revisadas.')
