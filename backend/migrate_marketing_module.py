#!/usr/bin/env python3
"""Migración: User.email_marketing_status + tablas del módulo marketing. Ejecutar desde backend: python migrate_marketing_module.py"""
import sqlite3
import os
from pathlib import Path

for db_path in [
    Path(__file__).parent.parent / 'instance' / 'NodeOne.db',
    Path(__file__).parent / 'instance' / 'NodeOne.db',
]:
    if db_path.exists():
        break
else:
    print("No se encontró NodeOne.db en instance/")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. User.email_marketing_status
cur.execute("PRAGMA table_info(user)")
cols = [r[1] for r in cur.fetchall()]
if 'email_marketing_status' not in cols:
    cur.execute("ALTER TABLE user ADD COLUMN email_marketing_status VARCHAR(20) DEFAULT 'subscribed'")
    print("+ user.email_marketing_status")

# 2. Tablas marketing
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='segment'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE segment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        query_rules TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("+ table segment")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='marketing_email_template'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE marketing_email_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        html TEXT NOT NULL,
        variables TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("+ table marketing_email_template")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE campaign (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        subject VARCHAR(500) NOT NULL,
        template_id INTEGER NOT NULL REFERENCES marketing_email_template(id),
        segment_id INTEGER NOT NULL REFERENCES segment(id),
        status VARCHAR(20) DEFAULT 'draft',
        scheduled_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("+ table campaign")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign_recipient'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE campaign_recipient (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL REFERENCES campaign(id),
        user_id INTEGER NOT NULL REFERENCES user(id),
        tracking_id VARCHAR(64) UNIQUE NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        sent_at DATETIME,
        opened_at DATETIME,
        clicked_at DATETIME
    )
    """)
    print("+ table campaign_recipient")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_queue'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE email_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER REFERENCES campaign_recipient(id),
        campaign_id INTEGER REFERENCES campaign(id),
        payload TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("+ table email_queue")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='automation_flow'")
if cur.fetchone() is None:
    cur.execute("""
    CREATE TABLE automation_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        trigger_event VARCHAR(80) NOT NULL,
        template_id INTEGER REFERENCES marketing_email_template(id),
        delay_hours INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    )
    """)
    print("+ table automation_flow")

conn.commit()
conn.close()
print("Migración marketing OK.")
