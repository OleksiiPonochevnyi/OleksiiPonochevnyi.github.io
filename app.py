from flask import Flask, render_template, request, jsonify
from datetime import datetime, date

app = Flask(__name__)

# Precio por noche según tipo de mascota
PRECIOS_POR_NOCHE = {
    "perro_pequeno": 10,
    "perro_mediano": 13,
    "perro_grande": 16,
    "gato": 9,
    "otro": 8,
}

NOMBRES_MASCOTA = {
    "perro_pequeno": "Perro pequeño",
    "perro_mediano": "Perro mediano",
    "perro_grande": "Perro grande",
    "gato": "Gato",
    "otro": "Otro animal",
}


def calcular_costo(fecha_inicio_str, fecha_fin_str, tipo_mascota, cantidad):
    """Calcula el número de noches y el costo total. Lanza ValueError si algo es inválido."""
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("Formato de fecha inválido. Usa AAAA-MM-DD.")

    if fecha_fin <= fecha_inicio:
        raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio.")

    if fecha_inicio < date.today():
        raise ValueError("La fecha de inicio no puede estar en el pasado.")

    if tipo_mascota not in PRECIOS_POR_NOCHE:
        raise ValueError("Tipo de mascota no válido.")

    try:
        cantidad = int(cantidad)
        if cantidad < 1:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("La cantidad de mascotas debe ser un número mayor a 0.")

    noches = (fecha_fin - fecha_inicio).days
    precio_noche = PRECIOS_POR_NOCHE[tipo_mascota]
    costo_total = noches * precio_noche * cantidad

    return {
        "noches": noches,
        "precio_por_noche": precio_noche,
        "cantidad_mascotas": cantidad,
        "tipo_mascota": NOMBRES_MASCOTA[tipo_mascota],
        "costo_total": costo_total,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),
    }


@app.route("/")
def index():
    return render_template("index.html", precios=PRECIOS_POR_NOCHE, nombres=NOMBRES_MASCOTA)


@app.route("/api/cotizar", methods=["POST"])
def cotizar():
    data = request.get_json(silent=True) or request.form

    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    tipo_mascota = data.get("tipo_mascota")
    cantidad = data.get("cantidad", 1)

    try:
        resultado = calcular_costo(fecha_inicio, fecha_fin, tipo_mascota, cantidad)
        return jsonify({"ok": True, **resultado})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
