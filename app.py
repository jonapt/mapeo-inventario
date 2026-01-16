from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from models import db, Estante, Entrepano,Item
from sqlalchemy import func 
from flask_migrate import Migrate
from io import BytesIO
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
app.secret_key = "inventario-super-secreto"
NIVELES = ["A","B","C","D","E","F","G","H","J","K"]

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventario.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
migrate = Migrate(app, db)

@app.route("/",methods=["GET","POST"])
def estantes():
    if request.method == "POST":
        numero = request.form["numero"]
        total = int(request.form["total_entrepanos"])
        estante = Estante(
            numero=numero,
            total_entrepanos=total
        )
        db.session.add(estante)
        db.session.flush()

        for nivel in NIVELES[:total]:
            entrepano=Entrepano(
                nivel=nivel,
                estante_id=estante.id
            )
            db.session.add(entrepano)
        db.session.commit()
        return redirect(url_for("estantes"))
    estantes = Estante.query.order_by(Estante.numero).all()
    return render_template("estantes.html", estantes=estantes)

@app.route("/estantes/<int:estante_id>")
def detalle_estante(estante_id):
    estante = Estante.query.get_or_404(estante_id)

    orden_niveles = NIVELES

    entrepanos_ordenados = sorted(
        estante.entrepano,
        key=lambda e:  orden_niveles.index(e.nivel),
        reverse=False
    )

    return render_template(
        "detalle-estante.html",
        estante=estante,
        entrepanos = entrepanos_ordenados
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
    entrepano_id = item.entrepano_id

    db.session.delete(item)
    db.session.commit()

    flash("🗑️ Item eliminado", "warning")

    return redirect(url_for("detalle_entrepano", entrepano_id=entrepano_id))


@app.route("/entrepanos/<int:entrepano_id>/items/nuevo", methods=["POST"])
def crear_item(entrepano_id):
    entrepano = Entrepano.query.get_or_404(entrepano_id)

    division = int(request.form["division"])

    ultima_division = (
        db.session.query(func.max(Item.division))
        .filter(Item.entrepano_id == entrepano.id)
        .scalar()
    )

    division_esperada = 1 if ultima_division is None else ultima_division + 1

    if division != division_esperada:
        flash(
            f"⚠️ La división debe ser consecutiva. Siguiente válida: {division_esperada}",
            "danger"
        )
        return redirect(url_for("detalle_entrepano", entrepano_id=entrepano.id))

    item = Item(
        codigo=request.form["codigo"],
        division=division,
        maximo=int(request.form["maximo"]),
        minimo=int(request.form["minimo"]),
        entrepano_id=entrepano.id
    )

    db.session.add(item)
    db.session.commit()

    flash("✅ Item agregado correctamente", "success")

    return redirect(url_for("detalle_entrepano", entrepano_id=entrepano.id))


@app.route("/items/<int:item_id>/editar", methods=["GET", "POST"])
def editar_item(item_id):
    item = Item.query.get_or_404(item_id)

    if request.method == "POST":
        item.codigo = request.form["codigo"]
        item.maximo = int(request.form["maximo"])
        item.minimo = int(request.form["minimo"])

        db.session.commit()

        flash("✏️ Item actualizado", "success")

        return redirect(
            url_for(
                "detalle_entrepano",
                entrepano_id=item.entrepano.id
            )
        )

    return render_template("editar-item.html", item=item)




@app.route("/exportar/excel")
def exportar_excel():

    filas = []

    items = Item.query.all()

    for item in items:
        division = item.division
        entrepano = division.entrepano
        estante = entrepano.estante

        filas.append({
            "Codigo": item.codigo,
            "Ubicacion": f"P{estante.numero}{entrepano.nivel}{division.numero}",
            "Estante": estante.numero,
            "Entrepano": entrepano.nivel,
            "Division": division.numero,
            "Descripcion": item.descripcion
        })

    df = pd.DataFrame(filas)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")

    output.seek(0)

    return send_file(
        output,
        download_name="inventario_ubicaciones.xlsx",
        as_attachment=True
    )

@app.route("/exportar/pdf")
def exportar_pdf():

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elementos = []

    # Encabezados
    data = [[
        "Codigo",
        "Ubicacion",
        "Estante",
        "Entrepano",
        "Division",
        "Descripcion"
        
    ]]

    items = Item.query.all()

    for item in items:
        division = item.division
        entrepano = division.entrepano
        estante = entrepano.estante

        data.append([
            item.codigo,
            f"P{estante.numero}{entrepano.nivel}{division.numero}",
            str(estante.numero),
            entrepano.nivel,
            str(division.numero),
            item.descripcion or ""
        ])

    tabla = Table(data, repeatRows=1)

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    buffer.seek(0)

    return send_file(
        buffer,
        download_name="inventario_ubicaciones.pdf",
        as_attachment=True
    )

def siguiente_division(entrepano_id):
    ultima = (
        db.session.query(db.func.max(Item.division))
        .filter_by(entrepano_id=entrepano_id)
        .scalar()
    )
    return 1 if ultima is None else ultima + 1

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=5001)