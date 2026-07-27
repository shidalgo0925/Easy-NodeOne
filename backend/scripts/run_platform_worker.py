#!/usr/bin/env python3
"""Worker de plataforma — despacho outbox + cola sync offline (cron / systemd)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault('NODEONE_ROOT', str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

from dotenv import load_dotenv

load_dotenv(ROOT.parent / '.env')
load_dotenv(ROOT / '.env')

from app import app, bootstrap_runtime_schema_and_email
from nodeone.core.platform.worker import run_platform_worker_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description='Easy NodeOne — worker outbox y sync offline')
    parser.add_argument('--event-limit', type=int, default=100, help='Máx. eventos por ciclo')
    parser.add_argument('--sync-limit', type=int, default=50, help='Máx. operaciones sync por ciclo')
    parser.add_argument('--organization-id', type=int, default=None, help='Filtrar por organización')
    parser.add_argument('--no-retry-failed', action='store_true', help='No reencolar eventos failed')
    parser.add_argument('--no-sync', action='store_true', help='Omitir cola sync offline')
    parser.add_argument('--json', action='store_true', help='Salida JSON')
    args = parser.parse_args()

    with app.app_context():
        bootstrap_runtime_schema_and_email()
        result = run_platform_worker_cycle(
            event_limit=max(1, int(args.event_limit)),
            sync_limit=max(1, int(args.sync_limit)),
            organization_id=args.organization_id,
            retry_failed=not args.no_retry_failed,
            process_sync=not args.no_sync,
        )
        print(json.dumps(result.to_dict()))
    else:
        print(
            f"events_dispatched={result.events_dispatched} "
            f"events_retried={result.events_retried} "
            f"sync_processed={result.sync_processed}"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
