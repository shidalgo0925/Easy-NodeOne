#!/usr/bin/env python3
"""Extiende taxes (computation, amount_fixed, price_included, created_at) y service.default_tax_id."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app import app
from nodeone.core.db import db


def _try(sql: str, ok_note: str) -> None:
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print(ok_note)
    except Exception as e:
        db.session.rollback()
        msg = str(e).lower()
        if 'duplicate column' in msg or 'already exists' in msg:
            print(f'Ya existía (skip): {ok_note}')
        else:
            raise


def main() -> None:
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)

        _try(
            "ALTER TABLE taxes ADD COLUMN computation VARCHAR(20) NOT NULL DEFAULT 'percent'",
            'taxes.computation',
        )
        _try('ALTER TABLE taxes ADD COLUMN amount_fixed FLOAT NOT NULL DEFAULT 0', 'taxes.amount_fixed')
        _try('ALTER TABLE taxes ADD COLUMN price_included BOOLEAN NOT NULL DEFAULT 0', 'taxes.price_included')
        _try('ALTER TABLE taxes ADD COLUMN created_at DATETIME', 'taxes.created_at')

        try:
            db.session.execute(text("UPDATE taxes SET price_included = 1 WHERE type = 'included'"))
            db.session.execute(text("UPDATE taxes SET created_at = datetime('now') WHERE created_at IS NULL"))
            db.session.commit()
            print('taxes: backfill price_included / created_at')
        except Exception as e:
            db.session.rollback()
            print('Backfill taxes:', e)

        _try(
            'ALTER TABLE service ADD COLUMN default_tax_id INTEGER REFERENCES taxes(id) ON DELETE SET NULL',
            'service.default_tax_id',
        )


if __name__ == '__main__':
    main()
