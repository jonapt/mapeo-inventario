from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from models import db, Estante, Entrepano,Item
from sqlalchemy import func 
from flask_migrate import Migrate
from io import BytesIO
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from sqlalchemy.exc import IntegrityError
import io
from openpyxl import Workbook


app = Flask(__name__)
app.secret_key = "inventario-super-secreto"
NIVELES = ["A","B","C","D","E","F","G","H","J","K"]

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventario.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "inventario-super-secreto-123"
db.init_app(app)
migrate = Migrate(app, db)

def generar_ubicacion(item):
    return (
        f"{item.entrepano.estante.tipo_estante}"
        f"{item.entrepano.estante.nombre}"
        f"{item.entrepano.nivel}"
        f"{item.division:02d}"
    )

@app.context_processor
def utilidades():
    return dict(generar_ubicacion=generar_ubicacion)

from datetime import datetime

def nombre_exportacion(base, extension):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{base}_{timestamp}.{extension}"

def siguiente_division(entrepano_id):
    ultima = (
        db.session.query(db.func.max(Item.division))
        .filter_by(entrepano_id=entrepano_id)
        .scalar()
    )
    return 1 if ultima is None else ultima + 1

@app.route("/", methods=["GET", "POST"])
def estantes():

    TIPOS = ["P", "M", "R", "A"]

    if request.method == "POST":
        nombre = request.form["nombre"]
        total = int(request.form["total_entrepanos"])
        tipo_estante= request.form["tipo"]

        session["tipo_estante"] = tipo_estante

        estante = Estante(
            nombre=nombre,
            tipo_estante=tipo_estante
        )
        db.session.add(estante)
        db.session.flush()

        for nivel in NIVELES[:total]:
            entrepano = Entrepano(
                nivel=nivel,
                estante_id=estante.id
            )
            db.session.add(entrepano)

        db.session.commit()
        flash("✅ Estante creado correctamente", "success")
        return redirect(url_for("estantes"))


    tipo_actual = session.get("tipo_estante", "P")

    estantes = Estante.query.order_by(Estante.id).all()

    return render_template(
        "estantes.html",
        estantes=estantes,
        tipos=TIPOS,
        tipo_actual=tipo_actual
    )



@app.route("/estantes/<int:estante_id>")
def detalle_estante(estante_id):
    estante = Estante.query.get_or_404(estante_id)
    from sqlalchemy import func

    entrepanos = Entrepano.query.filter_by(estante_id=estante.id).all()

    divisiones_por_entrepano = {
        e.id: (
            db.session.query(func.count(func.distinct(Item.division)))
            .filter(Item.entrepano_id == e.id)
            .scalar()
        )
        for e in entrepanos
    }

    orden_niveles = NIVELES

    entrepanos_ordenados = sorted(
        estante.entrepanos,
        key=lambda e:  orden_niveles.index(e.nivel),
        reverse=False
    )

    return render_template(
        "detalle-estante.html",
        estante=estante,
        entrepanos=entrepanos,
        divisiones_por_entrepano=divisiones_por_entrepano
    )


@app.route("/entrepanos/<int:entrepano_id>", methods=["GET", "POST"])
def detalle_entrepano(entrepano_id):
    entrepano = Entrepano.query.get_or_404(entrepano_id)

    items = (
        Item.query
        .filter_by(entrepano_id=entrepano.id)
        .order_by(Item.division)
        .all()
    )


    return render_template(
    "detalle-entrepano.html",
    entrepano=entrepano,
    items=items
    )



@app.route("/estantes/<int:estante_id>/eliminar", methods=["POST"])
def eliminar_estante(estante_id):
    estante = Estante.query.get_or_404(estante_id)

    db.session.delete(estante)
    db.session.commit()

    return redirect(url_for("estantes"))

@app.route("/entrepanos/<int:entrepano_id>/eliminar", methods=["POST"])
def eliminar_entrepano(entrepano_id):
    entrepano = Entrepano.query.get_or_404(entrepano_id)

    estante_id = entrepano.estante.id  # para volver atrás

    db.session.delete(entrepano)
    db.session.commit()

    return redirect(url_for("detalle_estante", estante_id=estante_id))


@app.route("/items/<int:item_id>/eliminar", methods=["POST"])
def eliminar_item(item_id):
    item = Item.query.get_or_404(item_id)
    entrepano_id = item.entrepano.id

    db.session.delete(item)
    db.session.commit()

    flash("🗑️ Item eliminado", "warning")

    return redirect(
        url_for("detalle_entrepano", entrepano_id=entrepano_id)
    )



from sqlalchemy.exc import IntegrityError

@app.route("/items/crear/<int:entrepano_id>", methods=["POST"])
def crear_item(entrepano_id):
    entrepano = Entrepano.query.get_or_404(entrepano_id)

    codigo_raw = request.form.get("codigo", "").strip()

    # 👇 convertir vacío en None
    codigo = codigo_raw if codigo_raw else None

    maximo = int(request.form["maximo"])
    minimo = int(request.form["minimo"])
    division = int(request.form["division"])


    # 🔎 SOLO validar si el código NO es NULL
    if codigo is not None:
        existente = Item.query.filter_by(codigo=codigo).first()
        if existente:
            flash(
                f"⚠️ El código ya existe en "
                f"Estante {existente.entrepano.estante.nombre} "
                f"Nivel {existente.entrepano.nivel} "
                f"División {existente.division:02d}",
                "danger"
            )
            return redirect(
                url_for("detalle_entrepano", entrepano_id=entrepano.id)
            )

    if maximo < minimo:
        flash("⚠️ El valor máximo no puede ser menor que el mínimo", "danger")
        return redirect(
            url_for("detalle_entrepano", entrepano_id=entrepano_id)
        )

    # ✅ Crear item
    item = Item(
        codigo=codigo,
        division=division,
        maximo=maximo,
        minimo=minimo,
        entrepano_id=entrepano.id
    )

    try:
        db.session.add(item)
        db.session.commit()
        flash("✅ Item creado correctamente", "success")

    except IntegrityError:
        db.session.rollback()
        flash("❌ Error inesperado al guardar el item", "danger")

    return redirect(
        url_for("detalle_entrepano", entrepano_id=entrepano.id)
    )




from sqlalchemy.exc import IntegrityError

@app.route("/item/<int:item_id>/editar", methods=["GET", "POST"])
def editar_item(item_id):
    item = Item.query.get_or_404(item_id)

    if request.method == "POST":
        codigo = request.form["codigo"].strip() or None
        division = request.form["division"].strip()
        maximo = int(request.form.get("maximo"))
        minimo = int(request.form.get("minimo"))

        if maximo < minimo:
            flash("⚠️ El valor máximo no puede ser menor que el mínimo", "danger")
            return redirect(
                url_for("editar_item", item_id=item.id)
            )

        item.division = division
        item.codigo = codigo
        item.maximo = maximo
        item.minimo = minimo

        try:
            db.session.commit()
            flash("✅ Item actualizado correctamente", "success")
            return redirect(
                url_for(
                    "detalle_entrepano",
                    entrepano_id=item.entrepano.id
                )
            )

        except IntegrityError:
            db.session.rollback()

            if codigo:
                existente = Item.query.filter(
                    Item.codigo == codigo,
                    Item.id != item.id
                ).first()

                flash(
                    f"⚠️ El código ya existe en "
                    f"Estante {existente.entrepano.estante.nombre} "
                    f"Nivel {existente.entrepano.nivel} "
                    f"División {existente.division}",
                    "danger"
                )
            else:
                flash(
                    "❌ Error al guardar el item",
                    "danger"
                )

    return render_template("editar-item.html", item=item)







from openpyxl import Workbook

@app.route("/exportar/excel")
def exportar_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"

    ws.append(["Código", "Ubicación", "Tipo estante","Estante", "Entrepaño", "División"])

    items = (
        Item.query
        .join(Entrepano)
        .join(Estante)
        .order_by(
            Estante.tipo_estante,
            Estante.nombre,
            Entrepano.nivel,
            Item.division
        )
        .all()
    )

    for item in items:
        division_str = str(item.division).zfill(2)
        ubicacion = generar_ubicacion(item)


        ws.append([
            item.codigo,
            ubicacion,
            item.entrepano.estante.tipo_estante,
            item.entrepano.estante.nombre,
            item.entrepano.nivel,
            division_str
        ])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=nombre_exportacion("mapeo","xlsx"),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )




from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import letter


@app.route("/exportar/pdf")
def exportar_pdf():
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)

    data = [
        ["Código", "Ubicación","Tipo estante","Estante", "Entrepaño", "División"]
    ]

    items = (
        Item.query
        .join(Entrepano)
        .join(Estante)
        .order_by(
            Estante.tipo_estante,
            Estante.nombre,
            Entrepano.nivel,
            Item.division
        )
        .all()
    )

    for item in items:
        division_str = str(item.division).zfill(2)
        ubicacion = generar_ubicacion(item)

        data.append([
            item.codigo,
            ubicacion,
            item.entrepano.estante.tipo_estante,
            item.entrepano.estante.nombre,
            item.entrepano.nivel,
            division_str
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    doc.build([table])
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_exportacion("mapeo","pdf"),
        mimetype="application/pdf"
    )



if __name__ == "__main__":
    app.run(debug=False,host="0.0.0.0",port=5001)