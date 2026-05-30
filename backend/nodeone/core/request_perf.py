"""Medición ligera de performance por request (solo dev / flag explícito)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger('en1.request_perf')

_PERF_PATHS = frozenset({
    '/login',
    '/dashboard',
    '/admin',
    '/admin/crm',
    '/admin/payments',
    '/admin/academic-enrollment/programs',
})


def perf_logging_enabled() -> bool:
    flag = (os.environ.get('EN1_PERF_LOG') or os.environ.get('EN1_PERF_DEBUG') or '').strip().lower()
    return flag in ('1', 'true', 'yes', 'on')


def _path_matches(path: str) -> bool:
    p = (path or '').split('?', 1)[0].rstrip('/') or '/'
    for prefix in _PERF_PATHS:
        base = prefix.rstrip('/') or '/'
        if p == base or p.startswith(base + '/'):
            return True
    return False


def register_request_perf(app) -> None:
    if not perf_logging_enabled():
        return

    from flask import g, has_request_context, request
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, 'before_cursor_execute')
    def _count_sql(conn, cursor, statement, parameters, context, executemany):
        if has_request_context():
            g._en1_sql_query_count = int(getattr(g, '_en1_sql_query_count', 0) or 0) + 1

    @app.before_request
    def _perf_start():
        g._en1_request_started_at = time.perf_counter()
        g._en1_sql_query_count = 0

    @app.after_request
    def _perf_log(response):
        try:
            if not _path_matches(request.path):
                return response
            elapsed_ms = (time.perf_counter() - getattr(g, '_en1_request_started_at', time.perf_counter())) * 1000
            sql_count = int(getattr(g, '_en1_sql_query_count', 0) or 0)
            from flask_login import current_user

            logged_in = bool(getattr(current_user, 'is_authenticated', False))
            org_id = None
            try:
                from utils.organization import get_current_organization_id

                org_id = get_current_organization_id()
            except Exception:
                pass
            saas_stats: dict[str, Any] = {}
            try:
                from nodeone.services.saas_module_cache import saas_cache_stats

                saas_stats = saas_cache_stats()
            except Exception:
                pass
            logger.info(
                'perf path=%s method=%s status=%s ms=%.1f sql=%s logged_in=%s org_id=%s saas_cache=%s',
                request.path,
                request.method,
                response.status_code,
                elapsed_ms,
                sql_count,
                logged_in,
                org_id,
                saas_stats,
            )
        except Exception:
            pass
        return response
