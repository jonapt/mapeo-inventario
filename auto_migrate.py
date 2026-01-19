import os
from app import app
from models import db

DB_FILE = "inventario.db"   # ajusta si tu archivo se llama distinto

def reset_database():
    # 1️⃣ Borrar archivo de base de datos si existe
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("🗑️ Base de datos eliminada")
    else:
        print("ℹ️ No existía base de datos")

    # 2️⃣ Crear tablas nuevamente
    with app.app_context():
        db.create_all()
        print("✅ Base de datos creada desde models.py")

if __name__ == "__main__":
    reset_database()
