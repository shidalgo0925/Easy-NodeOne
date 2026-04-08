"""Instancia SQLAlchemy compartida (FASE 4b). Inicializar con db.init_app(app) en app.py."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
