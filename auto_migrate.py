from app import app
from models import db
import os

DB_PATH = "instance/app.db"

with app.app_context():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️ Base de datos eliminada")

    db.create_all()
    print("✅ Base de datos creada nuevamente")
# reset_db.py
from app import app, db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Base de datos recreada correctamente")
