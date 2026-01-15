from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Estante(db.Model):
    __tablename__ = "estantes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False, unique=True)
    total_entrepanos= db.Column(db.Integer,nullable=False)

    entrepano = db.relationship(
        "Entrepano",
        backref="estante",
        cascade="all, delete-orphan"
    )

class Entrepano(db.Model):
    __tablename__ = "entrepanos"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(1),nullable=False)
    estante_id =db.Column(
        db.Integer,
        db.ForeignKey("estantes.id"),
        nullable=False
    )

    division = db.relationship(
        "Division",
        backref="entrepano",
        cascade="all, delete-orphan"
    )

class Division(db.Model):
    __tablename__ = "divisiones"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)

    entrepano_id = db.Column(
        db.Integer,
        db.ForeignKey("entrepanos.id"),
        nullable=False
    )

    items = db.relationship(
        "Item",
        backref="division",
        cascade="all, delete-orphan"
    )


    
class Item(db.Model):
    __tablename__="items"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50),nullable=False)
    descripcion = db.Column(db.String(250))
    maximo=db.Column(db.Integer)
    minimo=db.Column(db.Integer)

    division_id=db.Column(
        db.Integer,
        db.ForeignKey("divisiones.id"),
        nullable=False
    )

    @property
    def ubicacion(self):
        estante=self.division.entrepano.estante.numero
        nivel=self.division.entrepano.nivel
        division = self.division.numero
        return(f"P{estante}{nivel}{division}")

