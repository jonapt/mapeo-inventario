from flask import Flask, render_template, request, redirect, url_for, send_file
from models import db, Estante, Entrepano,Division,Item
from sqlalchemy import func
from flask_migrate import Migrate
from io import BytesIO
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
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

    if request.method == "POST":

        # 1️⃣ calcular número de división
        ultimo_numero = (
            db.session.query(func.max(Division.numero))
            .filter_by(entrepano_id=entrepano.id)
            .scalar()
        )
        nuevo_numero = 1 if ultimo_numero is None else ultimo_numero + 1

        # 2️⃣ crear división
        division = Division(
            numero=nuevo_numero,
            entrepano_id=entrepano.id
        )
        db.session.add(division)
        db.session.flush()  # 👈 NECESARIO para obtener division.id

        # 3️⃣ crear item (ESTO ERA LO QUE FALLABA)
        item = Item(
            codigo=request.form["codigo"],
            descripcion=request.form["descripcion"],
            maximo=int(request.form["maximo"]),
            minimo=int(request.form["minimo"]),
            division_id=division.id
        )

        db.session.add(item)
        db.session.commit()

        return redirect(url_for("detalle_entrepano", entrepano_id=entrepano.id))

    divisiones = (
        Division.query
        .filter_by(entrepano_id=entrepano.id)
        .order_by(Division.numero)
        .all()
    )

    return render_template(
        "detalle-entrepano.html",
        entrepano=entrepano,
        divisiones=divisiones
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

    division = item.division
    entrepano_id = division.entrepano.id


    db.session.delete(item)


    db.session.delete(division)

    db.session.commit()

    return redirect(
        url_for("detalle_entrepano", entrepano_id=entrepano_id)
    )


@app.route("/exportar/excel")
def exportar_excel():

    filas = []

    items = Item.query.all()

    for item in items:
        division = item.division
        entrepano = division.entrepano
        estante = entrepano.estante

        filas.append({
            "Ubicacion": f"P{estante.numero}{entrepano.nivel}{division.numero}",
            "Estante": estante.numero,
            "Entrepano": entrepano.nivel,
            "Division": division.numero,
            "Codigo": item.codigo,
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
        "Ubicacion",
        "Estante",
        "Entrepano",
        "Division",
        "Codigo",
        "Descripcion"
        
    ]]

    items = Item.query.all()

    for item in items:
        division = item.division
        entrepano = division.entrepano
        estante = entrepano.estante

        data.append([
            f"P{estante.numero}{entrepano.nivel}{division.numero}",
            str(estante.numero),
            entrepano.nivel,
            str(division.numero),
            item.codigo,
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

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=5001)