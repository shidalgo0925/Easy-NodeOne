#!/usr/bin/env python3
"""Añade columna body_html a campañas de marketing. Ejecutar: python backend/migrate_marketing_body_html.py"""
import sqlite3
from pathlib import Path

for db_path in [
    Path(__file__).parent.parent / 'instance' / 'NodeOne.db',
    Path(__file__).parent / 'instance' / 'NodeOne.db',
]:
    if db_path.exists():
        break
else:
    print("No se encontró NodeOne.db")
    exit(1)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='marketing_campaigns' OR name='campaign')")
tables = [r[0] for r in cur.fetchall()]
for table in tables or ['marketing_campaigns']:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
    except Exception:
        continue
    if not rows:
        continue
    cols = [r[1] for r in rows]
    if 'body_html' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN body_html TEXT")
        print(f"+ {table}.body_html")
    if 'exclusion_emails' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN exclusion_emails TEXT")
        print(f"+ {table}.exclusion_emails")
    if 'from_name' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN from_name VARCHAR(200)")
        print(f"+ {table}.from_name")
    if 'reply_to' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN reply_to VARCHAR(200)")
        print(f"+ {table}.reply_to")
    if 'subject_b' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN subject_b VARCHAR(500)")
        print(f"+ {table}.subject_b")
    break
# campaign_recipients / campaign_recipient
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='campaign_recipients' OR name='campaign_recipient')")
rec_tables = [r[0] for r in cur.fetchall()]
for rtable in rec_tables or ['campaign_recipients']:
    try:
        cur.execute(f"PRAGMA table_info({rtable})")
        rrows = cur.fetchall()
    except Exception:
        continue
    if not rrows:
        continue
    rcols = [r[1] for r in rrows]
    if 'variant' not in rcols:
        cur.execute(f"ALTER TABLE {rtable} ADD COLUMN variant VARCHAR(1)")
        print(f"+ {rtable}.variant")
    break
else:
    print("No se encontró tabla de campañas (marketing_campaigns/campaign)")
conn.commit()
conn.close()
print("Migración body_html OK.")
