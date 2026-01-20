from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



class Estante(db.Model):
    __tablename__ = "estante"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    tipo_estante = db.Column(db.String(1),nullable=False,server_default="P")
    
    entrepanos = db.relationship(
        "Entrepano",
        backref="estante",
        cascade="all, delete-orphan"
    )

    @property
    def total_entrepanos(self):
        return len(self.entrepanos)

# =========================
# ENTREPAÑO
# =========================
class Entrepano(db.Model):
    __tablename__ = "entrepanos"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(2), nullable=False)

    estante_id = db.Column(
        db.Integer,
        db.ForeignKey("estante.id"),
        nullable=False
    )

    items = db.relationship(
        "Item",
        backref="entrepano",
        cascade="all, delete-orphan"
    )



# =========================
# ITEM
# =========================
class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(7), nullable=True, unique=True)
    division = db.Column(db.Integer, nullable=False)
    maximo = db.Column(db.Integer, nullable=False)
    minimo = db.Column(db.Integer, nullable=False)

    entrepano_id = db.Column(
        db.Integer,
        db.ForeignKey("entrepanos.id"),
        nullable=False
    )


    @property
    def ubicacion(self):
        """
        Formato 2 dígitos: 01, 02, ..., 15
        """
        return f"{self.division:02d}"
