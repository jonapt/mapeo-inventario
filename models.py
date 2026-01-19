from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Estante(db.Model):
    __tablename__ = "estantes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False, unique=True)

    entrepanos = db.relationship(
        "Entrepano",
        backref="estante",
        cascade="all, delete-orphan"
    )


class Entrepano(db.Model):
    __tablename__ = "entrepanos"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(1), nullable=False)

    estante_id = db.Column(
        db.Integer,
        db.ForeignKey("estantes.id"),
        nullable=False
    )

    items = db.relationship(
        "Item",
        backref="entrepano",
        cascade="all, delete-orphan"
    )


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(7), nullable=False, unique=True)

    division = db.Column(db.Integer, nullable=False)

    maximo = db.Column(db.Integer, nullable=False)
    minimo = db.Column(db.Integer, nullable=False)

    entrepano_id = db.Column(
        db.Integer,
        db.ForeignKey("entrepanos.id"),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("entrepano_id", "division"),
    )
