from flask import Flask, render_template, request, jsonify
from datetime import datetime, date
import json
import os
import uuid

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "solicitudes.json")


def cargar_solicitudes():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def guardar_solicitudes(solicitudes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(solicitudes, f, ensure_ascii=False, indent=2)

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


@app.route("/api/solicitudes", methods=["POST"])
def crear_solicitud():
    """Confirma una cotización y la guarda como solicitud pendiente."""
    data = request.get_json(silent=True) or request.form

    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    tipo_mascota = data.get("tipo_mascota")
    cantidad = data.get("cantidad", 1)
    nombre_cliente = (data.get("nombre_cliente") or "").strip() or "Sin nombre"

    try:
        resultado = calcular_costo(fecha_inicio, fecha_fin, tipo_mascota, cantidad)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    nueva_solicitud = {
        "id": str(uuid.uuid4()),
        "nombre_cliente": nombre_cliente,
        "tipo_mascota": resultado["tipo_mascota"],
        "cantidad_mascotas": resultado["cantidad_mascotas"],
        "fecha_inicio": resultado["fecha_inicio"],
        "fecha_fin": resultado["fecha_fin"],
        "noches": resultado["noches"],
        "costo_total": resultado["costo_total"],
        "estado": "pendiente",  # pendiente | aceptado | rechazado
        "creado": datetime.now().isoformat(timespec="seconds"),
    }

    solicitudes = cargar_solicitudes()
    solicitudes.append(nueva_solicitud)
    guardar_solicitudes(solicitudes)

    return jsonify({"ok": True, "solicitud": nueva_solicitud})


@app.route("/animales")
def animales():
    solicitudes = cargar_solicitudes()
    solicitudes.sort(key=lambda s: s["creado"], reverse=True)
    total_pendientes = sum(1 for s in solicitudes if s["estado"] == "pendiente")
    total_aceptadas = sum(1 for s in solicitudes if s["estado"] == "aceptado")
    return render_template(
        "animales.html",
        solicitudes=solicitudes,
        total=len(solicitudes),
        total_pendientes=total_pendientes,
        total_aceptadas=total_aceptadas,
    )


@app.route("/api/solicitudes/<solicitud_id>/estado", methods=["POST"])
def actualizar_estado(solicitud_id):
    data = request.get_json(silent=True) or request.form
    nuevo_estado = data.get("estado")

    if nuevo_estado not in ("aceptado", "rechazado", "pendiente"):
        return jsonify({"ok": False, "error": "Estado no válido."}), 400

    solicitudes = cargar_solicitudes()
    for s in solicitudes:
        if s["id"] == solicitud_id:
            s["estado"] = nuevo_estado
            guardar_solicitudes(solicitudes)
            return jsonify({"ok": True, "solicitud": s})

    return jsonify({"ok": False, "error": "Solicitud no encontrada."}), 404


@app.route("/api/solicitudes/<solicitud_id>", methods=["DELETE"])
def eliminar_solicitud(solicitud_id):
    solicitudes = cargar_solicitudes()
    nuevas = [s for s in solicitudes if s["id"] != solicitud_id]

    if len(nuevas) == len(solicitudes):
        return jsonify({"ok": False, "error": "Solicitud no encontrada."}), 404

    guardar_solicitudes(nuevas)
    return jsonify({"ok": True})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
