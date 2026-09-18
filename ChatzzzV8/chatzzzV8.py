import os
import sys
import random
import socket
import json
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

app = Flask(__name__)
app.secret_key = "clave_secreta_fija_para_sesiones_chat_2026"
app.permanent_session_lifetime = timedelta(days=30)

TIEMPO_INICIO = time.time()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_UPLOADS = os.path.join(BASE_DIR, 'Archivos_Chat')
os.makedirs(CARPETA_UPLOADS, exist_ok=True)

ARCHIVO_NOMBRES = os.path.join(BASE_DIR, 'nombres.json')
ARCHIVO_NOMBRES_REALES = os.path.join(BASE_DIR, 'nombres_reales.json')
ARCHIVO_PRO = os.path.join(BASE_DIR, 'pro.json')
ARCHIVO_PENDIENTES = os.path.join(BASE_DIR, 'pendientes.json')
ARCHIVO_REGISTRO = os.path.join(BASE_DIR, 'registro.json')
ARCHIVO_ANTIGUAS = os.path.join(BASE_DIR, 'cuentas_antiguas.json')
ARCHIVO_FOTOS = os.path.join(BASE_DIR, 'fotos.json')
CARPETA_FOTOS = os.path.join(BASE_DIR, 'Fotos_Perfil')
os.makedirs(CARPETA_FOTOS, exist_ok=True)

MAX_SUBIDA = 20 * 1024 * 1024        # tope por archivo enviado al chat
DIAS_ARCHIVO_VIEJO = 30              # a partir de aqui el panel los considera "viejos"

usuarios_activos = {}

# A quién se le pedirá el PIN la próxima vez que entre.
# Va por apodo (no por sesión) para poder marcarlo con el usuario desconectado.
pendientes_pin = set()
if os.path.exists(ARCHIVO_PENDIENTES):
    try:
        with open(ARCHIVO_PENDIENTES, 'r', encoding='utf-8') as f:
            pendientes_pin = set(json.load(f).get("pin", []))
    except Exception:
        pendientes_pin = set()

def guardar_pendientes():
    with open(ARCHIVO_PENDIENTES, 'w', encoding='utf-8') as f:
        json.dump({"pin": list(pendientes_pin)}, f, ensure_ascii=False)

# Apodo -> nombre real, para poder identificar a los registrados aunque no estén conectados
REGISTRO_NOMBRES = {}
if os.path.exists(ARCHIVO_REGISTRO):
    try:
        with open(ARCHIVO_REGISTRO, 'r', encoding='utf-8') as f:
            REGISTRO_NOMBRES = json.load(f)
    except Exception:
        REGISTRO_NOMBRES = {}

def guardar_registro():
    with open(ARCHIVO_REGISTRO, 'w', encoding='utf-8') as f:
        json.dump(REGISTRO_NOMBRES, f, ensure_ascii=False)

# Al eliminar una cuenta se guarda aquí lo que tenía (PRO, color, emoji),
# para poder traspasárselo más tarde a la cuenta nueva de esa persona
CUENTAS_ANTIGUAS = {}
if os.path.exists(ARCHIVO_ANTIGUAS):
    try:
        with open(ARCHIVO_ANTIGUAS, 'r', encoding='utf-8') as f:
            CUENTAS_ANTIGUAS = json.load(f)
    except Exception:
        CUENTAS_ANTIGUAS = {}

def guardar_antiguas():
    with open(ARCHIVO_ANTIGUAS, 'w', encoding='utf-8') as f:
        json.dump(CUENTAS_ANTIGUAS, f, ensure_ascii=False)

def puede_escribir_en(destinatario):
    return destinatario == "todos" or destinatario in nombres_registrados

# Foto de perfil de cada usuario PRO: {apodo: nombre de archivo}
FOTOS_PERFIL = {}
if os.path.exists(ARCHIVO_FOTOS):
    try:
        with open(ARCHIVO_FOTOS, 'r', encoding='utf-8') as f:
            FOTOS_PERFIL = json.load(f)
    except Exception:
        FOTOS_PERFIL = {}

def guardar_fotos():
    with open(ARCHIVO_FOTOS, 'w', encoding='utf-8') as f:
        json.dump(FOTOS_PERFIL, f, ensure_ascii=False)

modo_silencio = False
puertas_cerradas = False

APODO_CREADOR = "PON_AQUI_TU_APODO"
CLAVE_ADMIN = "Aleksey3110."

USUARIOS_PRO = set()
if os.path.exists(ARCHIVO_PRO):
    try:
        with open(ARCHIVO_PRO, 'r', encoding='utf-8') as f:
            USUARIOS_PRO = set(json.load(f))
    except Exception:
        USUARIOS_PRO = set()

ARCHIVO_COLORES = os.path.join(BASE_DIR, 'colores.json')
COLORES_USUARIOS = {}
if os.path.exists(ARCHIVO_COLORES):
    try:
        with open(ARCHIVO_COLORES, 'r', encoding='utf-8') as f:
            COLORES_USUARIOS = json.load(f)
    except Exception:
        COLORES_USUARIOS = {}

COLORES_PERMITIDOS = ["#eab308", "#22d3ee", "#f472b6", "#a78bfa", "#4ade80", "#f87171"]

def guardar_colores():
    with open(ARCHIVO_COLORES, 'w', encoding='utf-8') as f:
        json.dump(COLORES_USUARIOS, f, ensure_ascii=False)

ARCHIVO_EMOJIS = os.path.join(BASE_DIR, 'emojis.json')
EMOJIS_USUARIOS = {}
if os.path.exists(ARCHIVO_EMOJIS):
    try:
        with open(ARCHIVO_EMOJIS, 'r', encoding='utf-8') as f:
            EMOJIS_USUARIOS = json.load(f)
    except Exception:
        EMOJIS_USUARIOS = {}

EMOJIS_PERMITIDOS = ["⭐", "👑", "😎", "🚀", "💎", "🔥"]

def guardar_emojis():
    with open(ARCHIVO_EMOJIS, 'w', encoding='utf-8') as f:
        json.dump(EMOJIS_USUARIOS, f, ensure_ascii=False)

def guardar_pro():
    with open(ARCHIVO_PRO, 'w', encoding='utf-8') as f:
        json.dump(list(USUARIOS_PRO), f, ensure_ascii=False)

def es_pro(apodo):
    return apodo == APODO_CREADOR or apodo in USUARIOS_PRO

nombres_registrados = set()
if os.path.exists(ARCHIVO_NOMBRES):
    try:
        with open(ARCHIVO_NOMBRES, 'r', encoding='utf-8') as f:
            nombres_registrados = set(json.load(f))
    except Exception:
        nombres_registrados = set()

nombres_reales_registrados = set()
if os.path.exists(ARCHIVO_NOMBRES_REALES):
    try:
        with open(ARCHIVO_NOMBRES_REALES, 'r', encoding='utf-8') as f:
            nombres_reales_registrados = set(json.load(f))
    except Exception:
        nombres_reales_registrados = set()

def guardar_nombres():
    with open(ARCHIVO_NOMBRES, 'w', encoding='utf-8') as f:
        json.dump(list(nombres_registrados), f, ensure_ascii=False)

def guardar_nombres_reales():
    with open(ARCHIVO_NOMBRES_REALES, 'w', encoding='utf-8') as f:
        json.dump(list(nombres_reales_registrados), f, ensure_ascii=False)

PUERTO_CHAT = 8492
CLAVE_SALA = "0000"
PIN_DESBLOQUEO = str(random.randint(1000, 9999))
ARCHIVO_MENSAJES = os.path.join(BASE_DIR, 'mensajes.json')
ARCHIVO_BD = os.path.join(BASE_DIR, 'chat.db')

def conectar_bd():
    # Una conexión por petición: Flask atiende a varios a la vez y no se pueden compartir
    con = sqlite3.connect(ARCHIVO_BD, timeout=10)
    con.row_factory = sqlite3.Row
    return con

def preparar_bd():
    con = conectar_bd()
    # WAL deja escribir a uno mientras otros leen, sin que se pisen
    con.execute("PRAGMA journal_mode=WAL")
    with con:
        con.execute("""CREATE TABLE IF NOT EXISTS mensajes (
            orden INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            texto TEXT,
            archivo TEXT,
            pro INTEGER DEFAULT 0,
            color TEXT DEFAULT '',
            emoji TEXT DEFAULT '⭐',
            hora TEXT DEFAULT '',
            destinatario TEXT DEFAULT 'todos',
            eliminado INTEGER DEFAULT 0
        )""")
    con.close()

def importar_mensajes_viejos():
    """Pasa los mensajes del antiguo mensajes.json a la base de datos, una sola vez."""
    if not os.path.exists(ARCHIVO_MENSAJES):
        return
    try:
        with open(ARCHIVO_MENSAJES, 'r', encoding='utf-8') as f:
            viejos = json.load(f)
    except Exception:
        print("⚠️ No se ha podido leer mensajes.json, se deja como está")
        return

    con = conectar_bd()
    with con:
        for m in viejos:
            con.execute(
                """INSERT OR IGNORE INTO mensajes
                   (id, nombre, texto, archivo, pro, color, emoji, hora, destinatario, eliminado)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (m.get("id") or os.urandom(8).hex(), m.get("nombre", ""), m.get("texto"),
                 m.get("archivo"), 1 if m.get("pro") else 0, m.get("color", ""),
                 m.get("emoji", "⭐"), m.get("hora", ""), m.get("destinatario", "todos"),
                 1 if m.get("eliminado") else 0))
    con.close()

    # Se guarda el original por si acaso, y con otro nombre para no reimportarlo
    os.rename(ARCHIVO_MENSAJES, ARCHIVO_MENSAJES + ".importado")
    print(f"📦 {len(viejos)} mensajes pasados a la base de datos (copia en mensajes.json.importado)")

preparar_bd()
importar_mensajes_viejos()

def fila_a_mensaje(fila):
    return {
        "id": fila["id"],
        "nombre": fila["nombre"],
        "texto": fila["texto"],
        "archivo": fila["archivo"],
        "pro": bool(fila["pro"]),
        "color": fila["color"],
        "emoji": fila["emoji"],
        "hora": fila["hora"],
        "destinatario": fila["destinatario"],
        "eliminado": bool(fila["eliminado"])
    }

def guardar_mensaje(nombre, texto, archivo, destinatario):
    con = conectar_bd()
    with con:
        con.execute(
            """INSERT INTO mensajes
               (id, nombre, texto, archivo, pro, color, emoji, hora, destinatario)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (os.urandom(8).hex(), nombre, texto, archivo, 1 if es_pro(nombre) else 0,
             COLORES_USUARIOS.get(nombre, ""), EMOJIS_USUARIOS.get(nombre, "⭐"),
             datetime.now().strftime("%H:%M"), destinatario))
    con.close()

def contar_mensajes():
    con = conectar_bd()
    total = con.execute("SELECT COUNT(*) FROM mensajes").fetchone()[0]
    con.close()
    return total

def mensajes_por_autor():
    con = conectar_bd()
    filas = con.execute("SELECT nombre, COUNT(*) AS n FROM mensajes GROUP BY nombre").fetchall()
    con.close()
    return {f["nombre"]: f["n"] for f in filas}

TITULO_PAGINA = "NCA_ESO_2_ING: ING.ESO2.IN01.ENG.Exchange_Programs_Dialogue.pdf | Sallenet"

def generar_nuevo_pin():
    global PIN_DESBLOQUEO
    PIN_DESBLOQUEO = str(random.randint(1000, 9999))
    print(f"\n🔄 ¡NUEVO PIN DE ADMINISTRADOR: {PIN_DESBLOQUEO}!\n")

def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def obtener_tiempo_activo():
    segundos = int(time.time() - TIEMPO_INICIO)
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    minutos = (segundos % 3600) // 60
    secs = segundos % 60
    if dias > 0:
        return f"{dias}d {horas}h {minutos}m"
    elif horas > 0:
        return f"{horas}h {minutos}m {secs}s"
    elif minutos > 0:
        return f"{minutos}m {secs}s"
    return f"{secs}s"

@app.before_request
def interceptar_bloqueados():
    apodo = session.get("apodo")
    if request.endpoint in ['desbloquear_apodo', 'logout', 'favicon', 'validar_pin', 'panel_admin_secreto']:
        return

    # Si le han borrado el registro, su sesión ya no vale: sigue como alguien sin registrar
    if apodo and session.get("acceso_concedido") and apodo not in nombres_registrados:
        session.pop("apodo", None)
        session.pop("nombre_real", None)
        session.pop("acceso_concedido", None)
        apodo = None

    if apodo and apodo in pendientes_pin:
        if request.path in ['/mensajes', '/estado_sesion', '/enviar', '/subir', '/estado_pro', '/color', '/emoji', '/desconectar']:
            return jsonify({"error": "bloqueado"}), 403
        
        if request.method == 'GET' and request.path != '/adminpanel':
            return render_template_string(HTML_PIN_APODO, error=request.args.get('error'))

@app.before_request
def rastrear_conexiones_automaticas():
    session.permanent = True
    # Mirar el panel de admin no es estar en el chat, y el aviso de marcharse
    # tampoco puede contar como señal de vida, o nunca te desconectarías
    if request.endpoint in ['logout', 'panel_admin_secreto', 'desconectar']:
        return
    if request.path.startswith('/api_admin/'):
        return

    if session.get("sala_autorizada"):
        if "id_sesion" not in session:
            session["id_sesion"] = os.urandom(6).hex()
        
        sid = session["id_sesion"]
        apodo_actual = session.get("apodo", "Sin apodo")
        nombre_real_actual = session.get("nombre_real", "No ingresado")
        ahora = time.time()
        
        es_nuevo = sid not in usuarios_activos
        usuarios_activos[sid] = {
            "apodo": apodo_actual,
            "nombre_real": nombre_real_actual,
            "last_seen": ahora
        }

        if session.get("apodo") and session.get("nombre_real") and REGISTRO_NOMBRES.get(apodo_actual) != nombre_real_actual:
            REGISTRO_NOMBRES[apodo_actual] = nombre_real_actual
            guardar_registro()

        if es_nuevo:
            total = len(usuarios_activos)
            print(f"🟢 [CONECTADO] \"{apodo_actual}\" | 👥 Total en línea: {total}")

def monitor_desconexiones():
    while True:
        time.sleep(2)
        ahora = time.time()
        desconectados = []
        
        for sid, info in list(usuarios_activos.items()):
            if ahora - info["last_seen"] > 15: 
                desconectados.append((sid, info["apodo"], info["nombre_real"]))
                
        for sid, apodo, nombre_real in desconectados:
            if sid in usuarios_activos:
                del usuarios_activos[sid]
                print(f"🔴 [DESCONECTADO] \"{apodo}\" | 👥 Total en línea: {len(usuarios_activos)}")

threading.Thread(target=monitor_desconexiones, daemon=True).start()

# -------------------------------------------------------------
# PLANTILLAS HTML
# -------------------------------------------------------------
HTML_LOGIN_ADMIN = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>body { background-color: #0f172a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }.card { background: #1e293b; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 360px; border: 1px solid #334155; text-align: center; }h2 { color: #38bdf8; margin-top: 0; margin-bottom: 10px; font-size: 20px; }p { color: #94a3b8; font-size: 13px; margin-bottom: 20px; }.form-group { display: flex; flex-direction: column; gap: 12px; }input { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #334155; color: #ffffff; font-size: 14px; outline: none; }input:focus { border-color: #38bdf8; }button { padding: 12px; border-radius: 8px; border: none; background: #38bdf8; color: #0f172a; font-weight: bold; cursor: pointer; font-size: 14px; }button:hover { background: #7dd3fc; }</style></head><body><div class="card"><h2>🔑 Panel de Administración</h2><p>Introduce la contraseña para acceder.</p><form class="form-group" action="/adminpanel" method="POST"><input type="password" name="clave" placeholder="Contraseña de Admin..." required autofocus><button type="submit">Entrar</button></form></div></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)
HTML_PIN_APODO = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>body { background-color: #0f172a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }.card { background: #1e293b; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; border: 1px solid #334155; text-align: center; }h2 { color: #eab308; margin-top: 0; margin-bottom: 10px; font-size: 22px; }p { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }.form-group { display: flex; flex-direction: column; gap: 12px; }input { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #334155; color: #ffffff; font-size: 14px; outline: none; }input:focus { border-color: #eab308; }button { padding: 12px; border-radius: 8px; border: none; background: #eab308; color: #000; font-weight: bold; cursor: pointer; font-size: 15px; margin-top: 5px; }button:hover { background: #facc15; }.error { color: #f87171; font-size: 13px; margin-top: 10px; }</style></head><body><div class="card"><h2>⚠️ Atención Requerida</h2><p>El administrador requiere que te identifiques con el <b>PIN de Apodo</b> para continuar.</p><form class="form-group" action="/desbloquear_apodo" method="POST"><input type="password" name="pin" placeholder="Introduce el PIN de Apodo..." required autofocus><button type="submit">Desbloquear y Volver</button></form>{% if error %}<div class="error">❌ PIN incorrecto. Pídeselo al administrador.</div>{% endif %}</div></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)
HTML_ERROR_CHROME = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>body { background-color: #202124; color: #e8eaed; font-family: 'Segoe UI', Tahoma, Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; width: 100vw; overflow: hidden; }.chrome-error-container { text-align: left; max-width: 420px; width: 90%; padding: 20px; }.chrome-icon { width: 72px; height: 72px; background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="%239aa0a6"><path d="M44 24c0 11.045-8.955 20-20 20S4 35.045 4 24 4s20 8.955 20 20zM24 18c-3.31 0-6 2.69-6 6s2.69 6 6 6-2.69 6-6-6zm16.93 3c-.92-5.13-4.2-9.43-8.81-11.72L26.6 21h14.33zm-19.3-8.89C16.81 12.87 12.96 16.5 11.13 21h12.81l-2.31-8.89zM10.16 27c.48 5.2 3.6 9.61 8.07 12.02L24.6 27H10.16zm20.8 11.89c4.83-1.76 8.61-5.46 10.32-10.11H28.46l2.5 10.11z"/></svg>'); background-size: contain; background-repeat: no-repeat; margin-bottom: 40px; }.chrome-h1 { font-size: 24px; font-weight: 500; margin-top: 0; margin-bottom: 10px; line-height: 1.25; color: #e8eaed; }.chrome-p { font-size: 15px; line-height: 1.6; margin-top: 0; margin-bottom: 15px; color: #9aa0a6; }.chrome-error-code { font-family: monospace; font-size: 13px; color: #9aa0a6; margin-bottom: 25px; text-transform: uppercase; }.login-form { display: flex; flex-direction: column; gap: 12px; }.chrome-input { background-color: #202124; border: 1px solid #5f6368; color: #e8eaed; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 14px; padding: 10px 14px; border-radius: 4px; outline: none; width: 100%; box-sizing: border-box; }.chrome-input:focus { border-color: #8ab4f8; }.chrome-input::placeholder { color: #5f6368; }.chrome-button { background-color: #8ab4f8; color: #202124; border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: 500; cursor: pointer; align-self: flex-start; }.chrome-button:hover { background-color: #9bbbe8; }.error-message { color: #f28b82; font-size: 13px; margin-top: 5px; }</style></head><body><div class="chrome-error-container"><div class="chrome-icon"></div><h1 class="chrome-h1">No se puede acceder a este sitio web</h1><p class="chrome-p">La página web en la dirección dada puede estar temporalmente inactiva o se ha trasladado permanentemente a una nueva dirección web.</p><div class="chrome-error-code">ERR_CONNECTION_REFUSED</div>{% if not cerrado %}<form class="login-form" action="/login_sala" method="POST"><input type="password" name="clave" class="chrome-input" placeholder="Introduce el PIN de acceso..." required autofocus><button type="submit" class="chrome-button">Cargar de nuevo</button></form>{% endif %}{% if error %}<div class="error-message">⚠️ Error al conectar. Código PIN incorrecto.</div>{% endif %}</div></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)
HTML_SOLICITUD = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>body { background-color: #0f172a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }.card { background: #1e293b; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; border: 1px solid #334155; }h2 { color: #38bdf8; margin-top: 0; margin-bottom: 10px; font-size: 22px; }p { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }.form-group { display: flex; flex-direction: column; gap: 12px; }input { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #334155; color: #ffffff; font-size: 14px; outline: none; }input:focus { border-color: #38bdf8; }button { padding: 12px; border-radius: 8px; border: none; background: #38bdf8; color: #0f172a; font-weight: bold; cursor: pointer; font-size: 15px; margin-top: 5px; }button:hover { background: #7dd3fc; }.error { color: #f87171; font-size: 13px; margin-top: 10px; text-align: center; }</style></head><body><div class="card"><h2>Identificación requerida</h2><p>Introduce tus datos para solicitar acceso a la sala.</p><form class="form-group" action="/procesar_solicitud" method="POST"><input type="text" name="nombre_real" placeholder="Tu Nombre Real..." required autofocus><input type="text" name="apodo" placeholder="Tu Apodo Público (No pongas tu nombre real)..." required><button type="submit">Solicitar Acceso</button></form>{% if error == "denegado" %}<div class="error">❌ El administrador ha denegado tu acceso.</div>{% elif error == "ocupado" %}<div class="error">⚠️ Ese nombre real o apodo ya está en uso. Prueba con otros.</div>{% endif %}</div></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_CHAT = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>:root { --bg-color: #0f172a; --sidebar-bg: #1e293b; --chat-bg: #0f172a; --text-color: #ffffff; --accent-color: #38bdf8; --user-color: #facc15; --msg-bg: #1e293b; --msg-own-bg: #0369a1; --border-color: #334155; --input-bg: #334155; --input-text: #ffffff; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; --chat-font-size: 14px; } 
body.theme-hacker { --bg-color: #000; --sidebar-bg: #050505; --chat-bg: #000; --text-color: #00ff00; --accent-color: #00ff00; --user-color: #00cc00; --msg-bg: #001100; --msg-own-bg: #003300; --border-color: #00ff00; --input-bg: #001100; --input-text: #00ff00; --font-family: "Courier New", Courier, monospace; } 
body.theme-cyberpunk { --bg-color: #120458; --sidebar-bg: #1f024c; --chat-bg: #120458; --text-color: #ff007f; --accent-color: #00f6ff; --user-color: #ffea00; --msg-bg: #2d006b; --msg-own-bg: #610094; --border-color: #ff007f; --input-bg: #2d006b; --input-text: #ff007f; --font-family: "Trebuchet MS", sans-serif; } 
body.theme-dracula { --bg-color: #282a36; --sidebar-bg: #44475a; --chat-bg: #282a36; --text-color: #f8f8f2; --accent-color: #bd93f9; --user-color: #50fa7b; --msg-bg: #44475a; --msg-own-bg: #6272a4; --border-color: #bd93f9; --input-bg: #282a36; --input-text: #f8f8f2; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-light { --bg-color: #e2e8f0; --sidebar-bg: #ffffff; --chat-bg: #f8fafc; --text-color: #0f172a; --accent-color: #2563eb; --user-color: #d97706; --msg-bg: #ffffff; --msg-own-bg: #dbeafe; --border-color: #cbd5e1; --input-bg: #ffffff; --input-text: #0f172a; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-forest { --bg-color: #1c2e24; --sidebar-bg: #273e31; --chat-bg: #1c2e24; --text-color: #e2fbe8; --accent-color: #4ade80; --user-color: #fde047; --msg-bg: #273e31; --msg-own-bg: #166534; --border-color: #40634e; --input-bg: #355241; --input-text: #e2fbe8; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-solarized { --bg-color: #002b36; --sidebar-bg: #073642; --chat-bg: #002b36; --text-color: #839496; --accent-color: #2aa198; --user-color: #b58900; --msg-bg: #073642; --msg-own-bg: #005f73; --border-color: #586e75; --input-bg: #073642; --input-text: #93a1a1; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-candy { --bg-color: #2b1b36; --sidebar-bg: #3d254f; --chat-bg: #2b1b36; --text-color: #ffd1dc; --accent-color: #ff77a9; --user-color: #ffe66d; --msg-bg: #3d254f; --msg-own-bg: #702670; --border-color: #6b418c; --input-bg: #53336c; --input-text: #ffd1dc; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-ocean { --bg-color: #04293a; --sidebar-bg: #06384f; --chat-bg: #04293a; --text-color: #d6f6ff; --accent-color: #22d3ee; --user-color: #7dd3fc; --msg-bg: #06384f; --msg-own-bg: #0e7490; --border-color: #22d3ee; --input-bg: #0a4a68; --input-text: #d6f6ff; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-sunset { --bg-color: #2e1a1a; --sidebar-bg: #40241f; --chat-bg: #2e1a1a; --text-color: #ffe8d6; --accent-color: #fb923c; --user-color: #f87171; --msg-bg: #40241f; --msg-own-bg: #c2410c; --border-color: #fb923c; --input-bg: #5a2f24; --input-text: #ffe8d6; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
body.theme-royal { --bg-color: #1a1420; --sidebar-bg: #241b2e; --chat-bg: #1a1420; --text-color: #f5e6b8; --accent-color: #d4af37; --user-color: #c9a3ff; --msg-bg: #241b2e; --msg-own-bg: #581c87; --border-color: #d4af37; --input-bg: #33243f; --input-text: #f5e6b8; --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 

* { box-sizing: border-box; }
body { font-family: var(--font-family); background: var(--bg-color); color: var(--text-color); margin: 0; padding: 0; height: 100vh; width: 100vw; overflow: hidden; display: flex; }
#app-container { display: flex; width: 100%; height: 100%; }

/* SIDEBAR / CONTACTS */
#sidebar { width: 320px; background: var(--sidebar-bg); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 15px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
.sidebar-header h2 { margin: 0; font-size: 18px; color: var(--accent-color); display: flex; align-items: center; gap: 8px; }
.sidebar-actions { display: flex; gap: 8px; align-items: center; }
select.theme-selector { background: var(--input-bg); color: var(--text-color); border: 1px solid var(--border-color); padding: 4px 6px; border-radius: 6px; font-size: 11px; cursor: pointer; }
.btn-logout { background: #ef4444; color: #ffffff; border: none; padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; cursor: pointer; text-decoration: none; }

.user-banner { padding: 10px 15px; background: rgba(0,0,0,0.1); border-bottom: 1px solid var(--border-color); font-size: 12px; }
.pro-badge { color: #eab308; font-weight: bold; margin-top: 4px; display: block; }

.section-title { padding: 10px 15px 5px; font-size: 11px; text-transform: uppercase; color: var(--accent-color); font-weight: bold; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.mi-perfil { display: flex; align-items: center; gap: 10px; }
.avatar-yo { width: 42px; height: 42px; flex-shrink: 0; overflow: hidden; }
.avatar img, .avatar-yo img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
.fila-foto { display: flex; gap: 6px; margin-top: 10px; }
.btn-foto { flex: 1; background: var(--input-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 6px; padding: 6px; font-size: 11px; cursor: pointer; }
.btn-foto:hover { border-color: var(--accent-color); }
.btn-quitar-foto { flex: 0 0 auto; }
.btn-quitar-foto:hover { border-color: #f87171; color: #f87171; }
.contacts-list { flex: 1; overflow-y: auto; }
.contact-item { padding: 12px 15px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: background 0.2s; }
.contact-item:hover, .contact-item.active { background: rgba(255,255,255,0.12); }
.avatar { width: 38px; height: 38px; border-radius: 50%; background: var(--accent-color); color: #000; font-weight: bold; display: flex; align-items: center; justify-content: center; font-size: 16px; position: relative; }
.status-dot { position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; background: #22c55e; border-radius: 50%; border: 2px solid var(--sidebar-bg); }
.contact-info { flex: 1; overflow: hidden; }
.contact-name { font-weight: bold; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: space-between; }
.contact-sub { font-size: 11px; opacity: 0.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.contact-item.desconectado .avatar { background: var(--border-color); color: var(--text-color); opacity: 0.7; }
.sin-chat { margin: auto; text-align: center; opacity: 0.6; font-size: 14px; display: flex; flex-direction: column; gap: 8px; align-items: center; }
.sin-chat-icono { font-size: 48px; }
.sin-chat-pista { font-size: 12px; opacity: 0.8; }
.badge-unread { background: #22c55e; color: #052e16; border-radius: 999px; font-size: 11px; font-weight: bold; line-height: 18px; min-width: 20px; height: 18px; padding: 0 6px; text-align: center; flex-shrink: 0; margin-left: 8px; }

/* DIVISOR PARA REDIMENSIONAR LA BARRA LATERAL */
#sidebar-resizer { width: 5px; flex-shrink: 0; cursor: col-resize; background: var(--border-color); opacity: 0.5; transition: opacity 0.2s, background 0.2s; }
#sidebar-resizer:hover, #sidebar-resizer.resizing { background: var(--accent-color); opacity: 1; }

/* BANNER NORMAS */
.rules-banner { background: rgba(239, 68, 68, 0.15); border-bottom: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 8px 15px; font-size: 12px; font-weight: bold; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px; }
.hint-banner { background: rgba(255,255,255,0.05); border-bottom: 1px solid var(--border-color); color: var(--text-color); opacity: 0.85; padding: 6px 15px; font-size: 11px; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px; }

/* CHAT MAIN AREA */
#chat-main { flex: 1; display: flex; flex-direction: column; background: var(--chat-bg); height: 100%; }
.chat-header { padding: 12px 20px; background: var(--sidebar-bg); border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
.chat-title { display: flex; align-items: center; gap: 12px; }
.chat-title h3 { margin: 0; font-size: 16px; color: var(--accent-color); }
.chat-subtitle { font-size: 11px; opacity: 0.7; }

#chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.msg { max-width: 65%; padding: 8px 12px; border-radius: 12px; word-break: break-word; font-size: var(--chat-font-size); position: relative; border: 1px solid var(--border-color); align-self: flex-start; background: var(--msg-bg); }
.msg.own { align-self: flex-end; background: var(--msg-own-bg); }
.msg-header { font-weight: bold; font-size: 11px; margin-bottom: 3px; display: flex; justify-content: space-between; gap: 10px; color: var(--user-color); }
.msg-time { font-size: 10px; opacity: 0.6; align-self: flex-end; float: right; margin-left: 10px; margin-top: 4px; font-weight: normal; color: var(--text-color); }
.msg-file { color: var(--accent-color); text-decoration: underline; font-weight: bold; }
.msg-eliminado { font-style: italic; opacity: 0.6; }
.btn-borrar-msg, .btn-copiar-msg { background: none; border: none; cursor: pointer; font-size: 11px; padding: 0 0 0 6px; opacity: 0; transition: opacity 0.2s; }
.msg:hover .btn-borrar-msg, .msg:hover .btn-copiar-msg { opacity: 0.7; }
.btn-borrar-msg:hover, .btn-copiar-msg:hover { opacity: 1; }
#aviso-copiado { position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%) translateY(10px); background: var(--msg-bg); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 20px; padding: 8px 18px; font-size: 13px; font-weight: bold; box-shadow: 0 6px 18px rgba(0,0,0,0.4); opacity: 0; pointer-events: none; transition: opacity 0.2s, transform 0.2s; z-index: 600; }
#aviso-copiado.visible { opacity: 1; transform: translateX(-50%) translateY(0); }

/* INPUT AREA */
.chat-input-area { padding: 15px 20px; background: var(--sidebar-bg); border-top: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 8px; }
.input-row { display: flex; gap: 10px; align-items: center; }
input[type="text"] { flex: 1; padding: 12px 15px; border-radius: 20px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--input-text); font-size: 14px; outline: none; }
button.btn-send { padding: 10px 20px; border-radius: 20px; border: none; background: var(--accent-color); color: #000; font-weight: bold; cursor: pointer; font-size: 14px; }
button.btn-file { background: #a855f7; color: white; border: none; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 16px; flex-shrink: 0; }
input[type="range"].size-slider { -webkit-appearance: none; appearance: none; background: var(--msg-bg); border: 1px solid var(--border-color); height: 6px; border-radius: 3px; outline: none; width: 70px; cursor: pointer; }
input[type="range"].size-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 12px; height: 12px; border-radius: 50%; background: var(--accent-color); cursor: pointer; }

/* CAMUFLAJE */
#pantalla-camuflaje { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 999999; background-color: #202124; color: #e8eaed; font-family: 'Segoe UI', Tahoma, Roboto, sans-serif; box-sizing: border-box; padding: 10vh 10vw; }
.chrome-error-box { max-width: 600px; text-align: left; }
.chrome-icon { width: 72px; height: 72px; background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="%239aa0a6"><path d="M44 24c0 11.045-8.955 20-20 20S4 35.045 4 24 4s20 8.955 20 20zM24 18c-3.31 0-6 2.69-6 6s2.69 6 6 6-2.69 6-6-6zm16.93 3c-.92-5.13-4.2-9.43-8.81-11.72L26.6 21h14.33zm-19.3-8.89C16.81 12.87 12.96 16.5 11.13 21h12.81l-2.31-8.89zM10.16 27c.48 5.2 3.6 9.61 8.07 12.02L24.6 27H10.16zm20.8 11.89c4.83-1.76 8.61-5.46 10.32-10.11H28.46l2.5 10.11z"/></svg>'); background-size: contain; background-repeat: no-repeat; margin-bottom: 24px; }
.chrome-h1 { font-size: 24px; font-weight: 500; margin-top: 0; margin-bottom: 12px; color: #e8eaed; }
.chrome-p { font-size: 14px; line-height: 1.6; color: #9aa0a6; margin-bottom: 16px; }
.chrome-code { font-family: monospace; font-size: 13px; color: #9aa0a6; margin-top: 20px; }
</style></head><body id="body-tag">

<div id="pantalla-camuflaje">
    <div class="chrome-error-box">
        <div class="chrome-icon"></div>
        <h1 class="chrome-h1">No se puede acceder a este sitio web</h1>
        <p class="chrome-p">Tardó demasiado tiempo en responder la conexión de <b>Sallenet</b>.</p>
        <p class="chrome-p">Prueba a:</p>
        <ul style="color: #9aa0a6; font-size: 14px; line-height: 1.6; margin-top: 0;">
            <li>Comprobar la conexión de red.</li>
            <li>Ejecutar el Diagnóstico de red de Windows o macOS.</li>
        </ul>
        <div class="chrome-code">ERR_CONNECTION_TIMED_OUT</div>
    </div>
</div>

<div id="app-container">
    <!-- PANEL IZQUIERDO: CONTACTOS Y SALAS -->
    <div id="sidebar">
        <div class="sidebar-header">
            <h2>💬 Chatzzz</h2>
            <div class="sidebar-actions">
                <select class="theme-selector" onchange="cambiarTema(this.value)" id="selector-tema">
                    <option value="default">🌌 Oscuro</option>
                    <option value="hacker">💻 Hacker</option>
                    <option value="cyberpunk">👾 Cyberpunk</option>
                    <option value="dracula">🧛 Dracula</option>
                    <option value="light">☀️ Claro</option>
                    <option value="forest">🌿 Bosque</option>
                    <option value="solarized">⚡ Solarized</option>
                    <option value="candy">🍬 Candy</option>
                    <option value="ocean" class="tema-pro" {{ '' if es_pro else 'disabled' }}>{{ '' if es_pro else '🔒 ' }}🌊 Océano{{ '' if es_pro else ' ⭐PRO' }}</option>
                    <option value="sunset" class="tema-pro" {{ '' if es_pro else 'disabled' }}>{{ '' if es_pro else '🔒 ' }}🌅 Atardecer{{ '' if es_pro else ' ⭐PRO' }}</option>
                    <option value="royal" class="tema-pro" {{ '' if es_pro else 'disabled' }}>{{ '' if es_pro else '🔒 ' }}👑 Real{{ '' if es_pro else ' ⭐PRO' }}</option>
                </select>
                <a href="/logout" class="btn-logout">Salir</a>
            </div>
        </div>

        <div class="user-banner">
            <div class="mi-perfil">
                <div class="avatar avatar-yo" id="mi-avatar" title="Tu foto de perfil">?</div>
                <div>
                    <div>Conectado como: <b id="lbl-apodo">...</b></div>
                    <span class="pro-badge" id="pro-banner">⭐ Plan Gratuito (Hazte PRO por 0,10€)</span>
                </div>
            </div>
            <input type="file" id="inputFoto" accept="image/*" style="display:none;" onchange="subirFotoPerfil()">
            <div class="fila-foto" id="fila-foto" style="display:none;">
                <button class="btn-foto" onclick="document.getElementById('inputFoto').click()">🖼️ Cambiar foto</button>
                <button class="btn-foto btn-quitar-foto" id="btn-quitar-foto" style="display:none;" onclick="quitarFotoPerfil()">🚫 Quitar</button>
            </div>
        </div>

        <div class="section-title"><span>Canales / Grupos</span></div>
        <div id="canal-principal-box">
            <div class="contact-item" onclick="seleccionarChat('todos')">
                <div class="avatar">📢</div>
                <div class="contact-info">
                    <div class="contact-name">Grupo Principal</div>
                    <div class="contact-sub">Chat público de la clase</div>
                </div>
            </div>
        </div>

        <div class="section-title"><span>Personas (<span id="cnt-conectados">0</span> en línea)</span></div>
        <div class="contacts-list" id="lista-contactos">
            <!-- Se carga dinámicamente -->
        </div>
    </div>

    <div id="sidebar-resizer" title="Arrastra para cambiar el ancho"></div>

    <div id="aviso-copiado"></div>


    <!-- PANEL DERECHO: CONVERSACIÓN -->
    <div id="chat-main">
        <div class="rules-banner">
            ⚠️ <span><b>NORMAS DE LA SALA:</b> Estrictamente prohibido hacer spam, saturar el chat e insultar.</span>
        </div>

        <div class="hint-banner">
            🙈 <span>Pulsa <b>ALT + C</b> para tapar el chat con una pantalla de error simulada. Con <b>ESC</b> vuelves.</span>
        </div>

        <div class="chat-header">
            <div class="chat-title">
                <div class="avatar" id="chat-header-icon">💬</div>
                <div>
                    <h3 id="chat-header-title">Ningún chat abierto</h3>
                    <div class="chat-subtitle" id="chat-sub-info">Elige una conversación en la lista</div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px;">
                <input type="range" id="sliderTamano" min="11" max="20" step="1" value="14" class="size-slider" oninput="cambiarTamanoTexto(this.value + 'px')" title="Tamaño de letra">
            </div>
        </div>

        <div id="chat-box"></div>

        <div class="chat-input-area">
            <div class="input-row" id="color-row" style="display:none; gap:6px;">
                <select id="colorPicker" class="theme-selector" onchange="cambiarColor()" style="flex:1;">
                    <option value="">🎨 (Sin Color)</option>
                    <option value="#eab308">🟡 Amarillo</option>
                    <option value="#22d3ee">🔵 Cian</option>
                    <option value="#f472b6">🌸 Rosa</option>
                    <option value="#a78bfa">🟣 Morado</option>
                    <option value="#4ade80">🟢 Verde</option>
                    <option value="#f87171">🔴 Rojo</option>
                </select>
                <select id="emojiPicker" class="theme-selector" onchange="cambiarEmoji()" style="flex:1;">
                    <option value="⭐">⭐ Estrella</option>
                    <option value="👑">👑 Corona</option>
                    <option value="😎">😎 Guay</option>
                    <option value="🚀">🚀 Cohete</option>
                    <option value="💎">💎 Diamante</option>
                    <option value="🔥">🔥 Fuego</option>
                </select>
            </div>
            <div class="input-row">
                <input type="file" id="archivoInput" style="display:none;" onchange="subirArchivo()">
                <button class="btn-file" id="btn-subir-file" onclick="document.getElementById('archivoInput').click()" title="Adjuntar Archivo">📎</button>
                <input type="text" id="mensaje" placeholder="Escribe un mensaje aquí..." autocomplete="off">
                <button class="btn-send" onclick="enviarMensaje()" id="btn-enviar-msg">Enviar</button>
            </div>
        </div>
    </div>
</div>

<script>
let chatActivo = null;
let miApodo = "";
let cntConectadosGlobal = 0;
let mensajesVistos = {};
let ultimosMensajesGlobal = [];

// Lo leído se guarda en este navegador para que al volver a entrar
// sigan marcados los mensajes que aún no has visto
function cargarVistos() {
    try {
        const guardado = localStorage.getItem('chat_vistos_' + miApodo);
        mensajesVistos = guardado ? JSON.parse(guardado) : {};
    } catch (e) {
        mensajesVistos = {};
    }
}

function guardarVistos() {
    try {
        localStorage.setItem('chat_vistos_' + miApodo, JSON.stringify(mensajesVistos));
    } catch (e) {}
}

function marcarVisto(clave, total) {
    if (mensajesVistos[clave] !== total) {
        mensajesVistos[clave] = total;
        guardarVistos();
    }
}

let conFoto = new Set();

function filtrarChat(clave, todosMensajes) {
    return todosMensajes.filter(m => {
        const dest = m.destinatario || 'todos';
        if (clave === 'todos') return dest === 'todos';
        return (m.nombre === miApodo && dest === clave) ||
               (m.nombre === clave && dest === miApodo);
    });
}

function textoDeEscritura() {
    return chatActivo === 'todos'
        ? "Escribe un mensaje aquí..."
        : `Mensaje privado para ${chatActivo}...`;
}

function avatarDe(apodo) {
    return conFoto.has(apodo)
        ? `<img src="/foto/${encodeURIComponent(apodo)}" alt="">`
        : escapeHTML(apodo.charAt(0).toUpperCase());
}

function estoyMirando() {
    return !document.hidden && document.hasFocus();
}

function calcularNoLeidos(clave, todosMensajes) {
    const total = filtrarChat(clave, todosMensajes).length;
    const vistos = mensajesVistos[clave] || 0;
    // Si el admin ha borrado el chat hay menos mensajes que antes: volvemos a empezar
    if (vistos > total) {
        marcarVisto(clave, total);
        return 0;
    }
    if (chatActivo === clave && estoyMirando()) {
        marcarVisto(clave, total);
        return 0;
    }
    return total - vistos;
}

function htmlBadge(n) {
    if (n <= 0) return '';
    return `<span class="badge-unread">${n > 99 ? '99+' : n}</span>`;
}

// Avisamos al servidor al cerrar la pestaña para aparecer desconectado al momento.
// sendBeacon funciona aunque la pagina se este cerrando; un fetch normal no llegaria.
function avisarQueMeVoy() {
    try {
        navigator.sendBeacon('/desconectar');
    } catch (e) {}
}

window.addEventListener('pagehide', avisarQueMeVoy);

// En el movil, cerrar el navegador o cambiar de app muchas veces no dispara 'pagehide'.
// Al ocultarse dejamos de preguntar y avisamos; al volver, se reanuda y vuelves a aparecer.
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
        pararSondeo();
        avisarQueMeVoy();
    } else {
        arrancarSondeo();
        cargarMensajes();
    }
});

// ATAJO: Alt + C (Camuflaje)
window.addEventListener('keydown', function(e) {
    if (e.altKey && e.key.toLowerCase() === 'c') {
        e.preventDefault();
        const camuflaje = document.getElementById('pantalla-camuflaje');
        camuflaje.style.display = (camuflaje.style.display === 'none' || camuflaje.style.display === '') ? 'block' : 'none';
    }
    if (e.key === 'Escape') {
        document.getElementById('pantalla-camuflaje').style.display = 'none';
    }
});

let yoSoyPro = {{ 'true' if es_pro else 'false' }};

function actualizarUIPro(pro, colorActual, emojiActual) {
    yoSoyPro = pro;
    document.getElementById('pro-banner').innerHTML = pro ? '⭐ <b>Usuario PRO</b>' : '⭐ Plan Gratuito (Hazte PRO por 0,10€)';
    document.getElementById('color-row').style.display = pro ? 'flex' : 'none';
    document.getElementById('fila-foto').style.display = pro ? 'flex' : 'none';
    if (pro) {
        if (colorActual) document.getElementById('colorPicker').value = colorActual;
        if (emojiActual) document.getElementById('emojiPicker').value = emojiActual;
    }
    document.querySelectorAll('#selector-tema option.tema-pro').forEach(op => {
        op.disabled = !pro;
        const base = op.textContent.replace('🔒 ', '').replace(' ⭐PRO', '');
        op.textContent = pro ? base : ('🔒 ' + base + ' ⭐PRO');
    });
}

async function comprobarEstadoPro() {
    try {
        const res = await fetch('/estado_pro');
        if (!res.ok) return;
        const data = await res.json();
        actualizarUIPro(data.pro, data.color, data.emoji);
    } catch (e) {}
}
// Mientras miras el chat se pregunta al servidor; si te vas, se para.
// Asi apareces desconectado de verdad y no se gastan peticiones de balde.
let temporizadorMensajes = null;
let temporizadorPro = null;

function arrancarSondeo() {
    if (!temporizadorMensajes) temporizadorMensajes = setInterval(cargarMensajes, 3000);
    if (!temporizadorPro) temporizadorPro = setInterval(comprobarEstadoPro, 6000);
}

function pararSondeo() {
    clearInterval(temporizadorMensajes);
    clearInterval(temporizadorPro);
    temporizadorMensajes = null;
    temporizadorPro = null;
}

async function cambiarColor() {
    const color = document.getElementById('colorPicker').value;
    await fetch('/color', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ color: color }) });
    cargarMensajes();
}

async function cambiarEmoji() {
    const emoji = document.getElementById('emojiPicker').value;
    await fetch('/emoji', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ emoji: emoji }) });
    cargarMensajes();
}

function cambiarTamanoTexto(tamano) {
    document.documentElement.style.setProperty('--chat-font-size', tamano);
    localStorage.setItem('chat_font_size', tamano);
}

const inputMensaje = document.getElementById('mensaje');
inputMensaje.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        enviarMensaje();
    }
});

window.onload = async () => {
    const temaGuardado = localStorage.getItem('chat_theme') || 'default';
    cambiarTema(temaGuardado);
    document.getElementById('selector-tema').value = temaGuardado;
    const tamanoGuardado = localStorage.getItem('chat_font_size') || '14px';
    cambiarTamanoTexto(tamanoGuardado);
    document.getElementById('sliderTamano').value = parseInt(tamanoGuardado);

    try {
        const res = await fetch('/estado_sesion');
        const data = await res.json();
        if (data.apodo) {
            miApodo = data.apodo;
            document.getElementById('lbl-apodo').innerText = miApodo;
        }
    } catch (e) {}

    cargarVistos();

    arrancarSondeo();
    cargarMensajes();
};

function cambiarTema(tema) {
    const body = document.getElementById('body-tag');
    body.className = '';
    if (tema !== 'default') body.classList.add('theme-' + tema);
    localStorage.setItem('chat_theme', tema);
}

function seleccionarChat(destinatario) {
    chatActivo = destinatario;
    marcarVisto(destinatario, filtrarChat(destinatario, ultimosMensajesGlobal).length);

    const iconHeader = document.getElementById('chat-header-icon');
    const titleHeader = document.getElementById('chat-header-title');
    const subHeader = document.getElementById('chat-sub-info');

    if (chatActivo === 'todos') {
        iconHeader.innerHTML = '📢';
        titleHeader.innerText = 'Grupo Principal';
        subHeader.innerText = `${cntConectadosGlobal} miembros conectados`;
    } else {
        iconHeader.innerHTML = avatarDe(chatActivo);
        titleHeader.innerText = `💬 Chat Privado con ${chatActivo}`;
        subHeader.innerText = 'Mensajes privados e confidenciales';
    }

    totalMensajesAnterior = 0;
    cargarMensajes();
}

let totalMensajesAnterior = 0;
const chatBox = document.getElementById('chat-box');

function usuarioEstaAbajo() {
    return chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 30;
}

function bajarScroll() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = (str === null || str === undefined) ? '' : str;
    return div.innerHTML;
}

async function cargarMensajes() {
    try {
        const res = await fetch('/mensajes');
        if (!res.ok) { window.location.reload(); return; }
        const data = await res.json();
        const estabaAbajo = usuarioEstaAbajo();
        const todosMensajes = data.mensajes || [];
        ultimosMensajesGlobal = todosMensajes;

        if (data.conectados !== undefined) {
            cntConectadosGlobal = data.conectados;
            document.getElementById('cnt-conectados').innerText = data.conectados;
            if (chatActivo === 'todos') {
                document.getElementById('chat-sub-info').innerText = `${data.conectados} miembros conectados`;
            }
        }

        if (data.lista_usuarios) {
            conFoto = new Set(data.lista_usuarios.filter(u => u.foto).map(u => u.apodo));

            const activeGrupo = (chatActivo === 'todos') ? 'active' : '';
            document.getElementById('canal-principal-box').innerHTML = `
                <div class="contact-item ${activeGrupo}" onclick="seleccionarChat('todos')">
                    <div class="avatar">📢</div>
                    <div class="contact-info">
                        <div class="contact-name">Grupo Principal ${htmlBadge(calcularNoLeidos('todos', todosMensajes))}</div>
                        <div class="contact-sub">Chat público de la clase</div>
                    </div>
                </div>`;

            let htmlUsuarios = '';
            const otros = data.lista_usuarios.filter(u => u.apodo !== miApodo);
            // Primero los que están en línea, pero todos se pueden abrir
            otros.sort((a, b) => (b.en_linea ? 1 : 0) - (a.en_linea ? 1 : 0));
            otros.forEach(u => {
                const activeCls = (chatActivo === u.apodo) ? 'active' : '';
                const badge = htmlBadge(calcularNoLeidos(u.apodo, todosMensajes));
                const punto = u.en_linea ? '<div class="status-dot"></div>' : '';
                htmlUsuarios += `<div class="contact-item ${activeCls} ${u.en_linea ? '' : 'desconectado'}" onclick="seleccionarChat('${escapeHTML(u.apodo)}')">
                    <div class="avatar">${avatarDe(u.apodo)}${punto}</div>
                    <div class="contact-info">
                        <div class="contact-name">${escapeHTML(u.apodo)} ${badge}</div>
                        <div class="contact-sub">${u.en_linea ? '🟢 En línea' : '⚪ Desconectado · le llegará al entrar'}</div>
                    </div>
                </div>`;
            });
            document.getElementById('lista-contactos').innerHTML = htmlUsuarios || '<div style="padding:10px 15px; font-size:12px; color:#94a3b8;">Todavía no hay nadie más registrado</div>';

            if (miApodo) {
                document.getElementById('mi-avatar').innerHTML = avatarDe(miApodo);
                document.getElementById('btn-quitar-foto').style.display = conFoto.has(miApodo) ? 'block' : 'none';
            }
        }

        if (chatActivo === null) {
            document.getElementById('mensaje').placeholder = "Elige un chat de la lista para escribir...";
            document.getElementById('mensaje').disabled = true;
            document.getElementById('btn-enviar-msg').disabled = true;
            document.getElementById('btn-subir-file').disabled = true;
            chatBox.innerHTML = `<div class="sin-chat">
                <div class="sin-chat-icono">💬</div>
                <div>Elige una conversación en la lista de la izquierda</div>
                <div class="sin-chat-pista">Los chats con mensajes sin leer llevan un número</div>
            </div>`;
            return;
        }
        document.getElementById('btn-subir-file').disabled = false;

        if(data.silencio) {
            document.getElementById('mensaje').placeholder = "🤐 El chat está silenciado por el administrador...";
            document.getElementById('mensaje').disabled = true;
            document.getElementById('btn-enviar-msg').disabled = true;
        } else {
            document.getElementById('mensaje').placeholder = textoDeEscritura();
            document.getElementById('mensaje').disabled = false;
            document.getElementById('btn-enviar-msg').disabled = false;
        }

        const lista = filtrarChat(chatActivo, todosMensajes);

        chatBox.innerHTML = '';
        textosPorId = {};
        lista.forEach(m => {
            let contenido = escapeHTML(m.texto);
            if (m.archivo) contenido = `<a href="/descargar/${encodeURIComponent(m.archivo)}" target="_blank" class="msg-file">📄 ${escapeHTML(m.archivo)}</a>`;
            if (m.eliminado) contenido = '<span class="msg-eliminado">🚫 Este mensaje ha sido eliminado</span>';
            const emojiSelect = m.emoji ? m.emoji : '⭐';
            const insignia = m.pro ? ` ${emojiSelect}` : '';
            const estiloColor = m.color ? ` style="color:${m.color};"` : '';
            const esMio = (m.nombre === miApodo);
            const hora = m.hora || '';
            const puedeBorrar = esMio && !m.eliminado && m.id;
            const btnBorrar = puedeBorrar
                ? `<button class="btn-borrar-msg" title="Eliminar este mensaje" onclick="borrarMensaje('${m.id}')">🗑️</button>`
                : '';

            // El texto se guarda aparte para no tener que meterlo en el HTML del botón
            let btnCopiar = '';
            if (m.texto && !m.eliminado && m.id) {
                textosPorId[m.id] = m.texto;
                btnCopiar = `<button class="btn-copiar-msg" title="Copiar mensaje" data-copiar="${m.id}">📋</button>`;
            }

            chatBox.innerHTML += `
            <div class="msg ${esMio ? 'own' : ''}">
                <div class="msg-header"${estiloColor}>${escapeHTML(m.nombre)}${insignia}${btnCopiar}${btnBorrar}</div>
                <div>${contenido} <span class="msg-time">${hora}</span></div>
            </div>`;
        });

        if (lista.length > totalMensajesAnterior) { 
            if (estabaAbajo || totalMensajesAnterior === 0) bajarScroll(); 
            totalMensajesAnterior = lista.length; 
        } else if (lista.length < totalMensajesAnterior) {
            totalMensajesAnterior = lista.length;
        }
    } catch (error) { 
        console.error(error);
    } 
} 

async function subirFotoPerfil() {
    const input = document.getElementById('inputFoto');
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append('foto', input.files[0]);
    const res = await fetch('/foto_perfil', { method: 'POST', body: formData });
    const data = await res.json();
    input.value = '';
    if (data.status === 'ok') {
        conFoto.add(miApodo);
        document.getElementById('mi-avatar').innerHTML = `<img src="/foto/${encodeURIComponent(miApodo)}?t=${Date.now()}" alt="">`;
        await cargarMensajes();
    } else {
        alert('No se ha podido subir: ' + (data.motivo || 'error'));
    }
}

let textosPorId = {};

async function copiarTexto(texto) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(texto);
            return true;
        }
    } catch (e) {}

    // Entrando por IP (sin https) el navegador bloquea el portapapeles moderno
    try {
        const area = document.createElement('textarea');
        area.value = texto;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.top = '-1000px';
        document.body.appendChild(area);
        area.select();
        const copiado = document.execCommand('copy');
        document.body.removeChild(area);
        return copiado;
    } catch (e) {
        return false;
    }
}

function avisar(texto) {
    const aviso = document.getElementById('aviso-copiado');
    aviso.textContent = texto;
    aviso.classList.add('visible');
    clearTimeout(avisar.temporizador);
    avisar.temporizador = setTimeout(() => aviso.classList.remove('visible'), 1400);
}

chatBox.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-copiar]');
    if (!btn) return;
    const texto = textosPorId[btn.dataset.copiar];
    if (texto === undefined) return;
    avisar(await copiarTexto(texto) ? '✅ Mensaje copiado' : '❌ No se ha podido copiar');
});

async function quitarFotoPerfil() {
    if (!confirm("¿Quitar tu foto de perfil?")) return;
    await fetch('/quitar_foto', { method: 'POST' });
    conFoto.delete(miApodo);
    document.getElementById('mi-avatar').innerHTML = avatarDe(miApodo);
    document.getElementById('btn-quitar-foto').style.display = 'none';
    await cargarMensajes();
}

async function borrarMensaje(id) {
    if (!confirm("¿Eliminar este mensaje para todos?")) return;
    const res = await fetch('/borrar_mensaje', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    });
    if (res.ok) await cargarMensajes();
}

async function enviarMensaje() {
    const msg = document.getElementById('mensaje').value.trim(); 
    if (!msg) return; 
    const res = await fetch('/enviar', { 
        method: 'POST', 
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify({texto: msg, destinatario: chatActivo}) 
    }); 
    if(res.ok) {
        document.getElementById('mensaje').value = ''; 
        await cargarMensajes(); 
        bajarScroll(); 
    }
} 

(function activarRedimensionSidebar() {
    const sidebar = document.getElementById('sidebar');
    const divisor = document.getElementById('sidebar-resizer');
    const ANCHO_MIN = 200, ANCHO_MAX = 600;

    const guardado = parseInt(localStorage.getItem('sidebar_width'));
    if (guardado) sidebar.style.width = Math.min(ANCHO_MAX, Math.max(ANCHO_MIN, guardado)) + 'px';

    let arrastrando = false;

    divisor.addEventListener('mousedown', (e) => {
        arrastrando = true;
        divisor.classList.add('resizing');
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (!arrastrando) return;
        const ancho = Math.min(ANCHO_MAX, Math.max(ANCHO_MIN, e.clientX));
        sidebar.style.width = ancho + 'px';
    });

    window.addEventListener('mouseup', () => {
        if (!arrastrando) return;
        arrastrando = false;
        divisor.classList.remove('resizing');
        document.body.style.userSelect = '';
        localStorage.setItem('sidebar_width', parseInt(sidebar.style.width));
    });
})();

async function subirArchivo() {
    const input = document.getElementById('archivoInput'); 
    if (!input.files[0]) return; 
    const formData = new FormData(); 
    formData.append('archivo', input.files[0]); 
    formData.append('destinatario', chatActivo);
    const res = await fetch('/subir', { method: 'POST', body: formData });
    input.value = '';
    if (res.ok) {
        await cargarMensajes();
        bajarScroll();
    } else {
        const error = await res.json().catch(() => ({}));
        avisar('❌ ' + (error.motivo || 'No se ha podido subir'));
    }
} 
</script></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_VISOR = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITULO_AQUI</title><link rel="icon" type="image/x-icon" href="/favicon.ico?v=2"><style>body { background-color: #0f172a; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; }.viewer-container { width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; }img, video { max-width: 100%; max-height: 100%; object-fit: contain; }iframe { width: 100%; height: 100%; border: none; }</style></head><body><div class="viewer-container">CONTENIDO_VISOR</div></body></html>""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_ADMIN = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITULO_AQUI</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=2">
    <style>
        body { background-color: #0f172a; color: #ffffff; font-family: -apple-system, sans-serif; padding: 20px; }
        .card { background: #1e293b; padding: 25px; border-radius: 15px; max-width: 900px; margin: auto; border: 1px solid #334155; }
        h1 { color: #38bdf8; text-align: center; margin-top: 0; font-size: 24px; }
        .pin-box { background: #334155; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px; font-family: monospace; font-size: 18px; border: 1px solid #eab308; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 15px; text-align: center; }
        .stat-val { font-size: 22px; font-weight: bold; color: #38bdf8; }
        .stat-lbl { font-size: 12px; color: #94a3b8; margin-top: 4px; }

        .global-controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .btn-ctrl { padding: 12px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 13px; text-align: center; }
        .btn-clear { background: #ef4444; color: white; }
        .btn-clear:hover { background: #dc2626; }
        .btn-toggle-on { background: #22c35e; color: black; }
        .btn-toggle-off { background: #64748b; color: white; }
        .btn-limpiar { background: #0e7490; color: #e0f2fe; }
        .btn-limpiar:hover { background: #0891b2; color: #fff; }
        
        .user-row { display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 14px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #475569; }
        .user-info { display: flex; flex-direction: column; }
        .user-apodo { font-weight: bold; font-size: 16px; color: #facc15; }
        .user-real { font-size: 12px; color: #94a3b8; }
        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
        button { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px; transition: 0.2s; }
        .btn-pro { background: #eab308; color: #000; }
        .btn-pro:hover { background: #facc15; }
        .btn-pin { background: #f97316; color: #fff; }
        .btn-pin:hover { background: #ea580c; }
        .btn-danger { background: #ef4444; color: #fff; }
        .btn-danger:hover { background: #dc2626; }
        button.activo { background: #64748b; color: #fff; }
        .btn-eliminar { background: #7f1d1d; color: #fecaca; border: 1px solid #b91c1c; }
        .btn-eliminar:hover { background: #991b1b; color: #fff; }
        .btn-traspaso { background: #0e7490; color: #e0f2fe; }
        .btn-traspaso:hover { background: #0891b2; color: #fff; }

        .modal-fondo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center; padding: 20px; }
        .modal-fondo.abierto { display: flex; }
        .modal-caja { background: #1e293b; border: 1px solid #334155; border-radius: 15px; padding: 25px; width: 100%; max-width: 480px; max-height: 80vh; overflow-y: auto; }
        .modal-caja h3 { color: #38bdf8; margin: 0 0 6px; font-size: 18px; }
        .modal-caja p { color: #94a3b8; font-size: 13px; margin: 0 0 18px; line-height: 1.5; }
        .opcion-cuenta { display: flex; justify-content: space-between; align-items: center; gap: 10px; width: 100%; background: #334155; border: 1px solid #475569; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; text-align: left; color: #fff; }
        .opcion-cuenta:hover { background: #475569; border-color: #38bdf8; }
        .opcion-apodo { font-weight: bold; font-size: 15px; color: #facc15; }
        .opcion-detalle { font-size: 11px; color: #94a3b8; }
        .opcion-cuenta .conteo { font-size: 12px; color: #38bdf8; white-space: nowrap; }
        .grupo-titulo { font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: bold; margin: 14px 0 8px; letter-spacing: 0.5px; }
        .btn-cerrar-modal { background: #64748b; color: #fff; width: 100%; padding: 12px; margin-top: 8px; }

        .section-head { font-size: 15px; color: #38bdf8; margin: 25px 0 6px; padding-bottom: 6px; border-bottom: 1px solid #334155; }
        .section-hint { font-size: 12px; color: #94a3b8; margin: 0 0 12px; }
        .user-row.offline { background: #1e293b; border-color: #334155; }
        .user-row.offline .user-apodo { color: #cbd5e1; }
        .vacio { text-align: center; color: #94a3b8; font-size: 13px; padding: 10px; }
        .tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }
        .tag-pro { background: #eab308; color: #000; }
        .tag-pend { background: #f97316; color: #000; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🛠️ Panel de Control Administrador</h1>
        <div class="pin-box">🔑 PIN de Desbloqueo: <b id="pinActual" style="color: #eab308; font-size: 22px;">...</b></div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val" id="st-conectados" style="color:#4ade80;">0</div>
                <div class="stat-lbl">👥 Personas Conectadas</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="st-registrados" style="color:#38bdf8;">0</div>
                <div class="stat-lbl">📋 Personas Registradas</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="st-uptime" style="color:#facc15;">0s</div>
                <div class="stat-lbl">⏱️ Tiempo Servidor Activo</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="st-mensajes" style="color:#a78bfa;">0</div>
                <div class="stat-lbl">💬 Mensajes Enviados</div>
            </div>
        </div>

        <div class="global-controls">
            <button class="btn-ctrl btn-clear" onclick="borrarGrupo()">🗑️ Borrar Grupo Principal</button>
            <button class="btn-ctrl btn-clear" onclick="borrarPrivados()">🗑️ Borrar Chats Privados</button>
            <button class="btn-ctrl" id="btn-silencio" onclick="toggleSilencio()">🤐 Modo Silencio</button>
            <button class="btn-ctrl" id="btn-puertas" onclick="togglePuertas()">🔒 Cerrar Puertas</button>
            <button class="btn-ctrl btn-limpiar" onclick="limpiarArchivos()">🧹 Limpiar archivos viejos</button>
        </div>

        <h2 class="section-head">💬 Chats privados (<span id="n-privados">0</span>)</h2>
        <div id="lista-privados"></div>

        <h2 class="section-head">🟢 Conectados ahora (<span id="n-conectados">0</span>)</h2>
        <div id="lista-conectados"></div>

        <h2 class="section-head">📋 Registrados sin conectar (<span id="n-desconectados">0</span>)</h2>
        <p class="section-hint">Lo que marques aquí se guarda y se aplica la próxima vez que entren.</p>
        <div id="lista-desconectados"></div>
    </div>

    <div class="modal-fondo" id="modal-traspaso">
        <div class="modal-caja">
            <h3>Traer datos a <span id="modal-destino"></span></h3>
            <p>Elige la cuenta antigua. Sus mensajes, archivos, PRO, color y emoji pasan a esta cuenta y los verá como suyos. Sirve también con cuentas ya eliminadas.</p>
            <div id="modal-lista"></div>
            <button class="btn-cerrar-modal" onclick="cerrarTraspaso()">Cancelar</button>
        </div>
    </div>
    <script>
        function escapeHTML(str) {
            return String(str === null || str === undefined ? '' : str)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }

        function filaUsuario(info, conectado) {
            const apodo = escapeHTML(info.apodo);
            let etiquetas = '';
            if (info.es_pro) etiquetas += '<span class="tag tag-pro">⭐ PRO</span>';
            if (info.pin_pendiente) etiquetas += '<span class="tag tag-pend">⏳ PIN al entrar</span>';

            return `<div class="user-row ${conectado ? '' : 'offline'}">
                <div class="user-info">
                    <span class="user-apodo">${conectado ? '🟢' : '⚪'} ${apodo}${etiquetas}</span>
                    <span class="user-real">${escapeHTML(info.nombre_real)}</span>
                </div>
                <div class="btn-group">
                    <button class="btn-pro" data-accion="pro" data-apodo="${apodo}">${info.es_pro ? '⭐ Quitar PRO' : '⭐ Dar PRO'}</button>
                    <button class="btn-pin ${info.pin_pendiente ? 'activo' : ''}" data-accion="pin" data-apodo="${apodo}">${info.pin_pendiente ? '✖️ Cancelar PIN' : '⚠️ Pedir PIN'}</button>
                    <button class="btn-traspaso" data-accion="traspaso" data-apodo="${apodo}">🔄 Traer datos</button>
                    <button class="btn-eliminar" data-accion="eliminar" data-apodo="${apodo}">❌ Eliminar ya</button>
                </div>
            </div>`;
        }

        document.addEventListener('click', async (e) => {
            const btn = e.target.closest('button[data-accion]');
            if (!btn) return;
            const apodo = btn.dataset.apodo;
            if (btn.dataset.accion === 'pro') togglePro(apodo);
            if (btn.dataset.accion === 'pin') forcePin(apodo);
            if (btn.dataset.accion === 'borrar-privado') {
                const { a, b } = btn.dataset;
                if (!confirm(`¿Borrar la conversación entre "${a}" y "${b}"? Se borra para los dos.`)) return;
                const r = await (await fetch('/api_admin/borrar_privado', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({a, b})
                })).json();
                alert(`Borrados ${r.borrados} mensajes.`);
                await cargarUsuarios();
                return;
            }
            if (btn.dataset.accion === 'traspaso') abrirTraspaso(apodo);
            if (btn.dataset.accion === 'eliminar') {
                if (!confirm(`¿Eliminar a "${apodo}" AHORA MISMO?\n\nSe borran sus datos, su PRO y su color. Si vuelve, entrará como alguien nuevo.`)) return;
                eliminarUsuario(apodo);
            }
        });

        async function cargarUsuarios() {
            try {
                const res = await fetch('/api_admin/usuarios');
                if (!res.ok) { window.location.href = '/'; return; }
                const data = await res.json();
                ultimosDatos = data;
                document.getElementById('pinActual').innerText = data.pin_actual;
                
                if(data.stats) {
                    document.getElementById('st-conectados').innerText = data.stats.conectados;
                    document.getElementById('st-registrados').innerText = data.stats.registrados;
                    document.getElementById('st-uptime').innerText = data.stats.uptime;
                    document.getElementById('st-mensajes').innerText = data.stats.mensajes;
                }

                const btnSilencio = document.getElementById('btn-silencio');
                if(data.modo_silencio) {
                    btnSilencio.textContent = "🔊 Quitar Silencio";
                    btnSilencio.className = "btn-ctrl btn-toggle-on";
                } else {
                    btnSilencio.textContent = "🤐 Modo Silencio";
                    btnSilencio.className = "btn-ctrl btn-toggle-off";
                }

                const btnPuertas = document.getElementById('btn-puertas');
                if(data.puertas_cerradas) {
                    btnPuertas.textContent = "🔓 Abrir Puertas";
                    btnPuertas.className = "btn-ctrl btn-toggle-on";
                } else {
                    btnPuertas.textContent = "🔒 Cerrar Puertas";
                    btnPuertas.className = "btn-ctrl btn-toggle-off";
                }

                const privados = data.privados || [];
                document.getElementById('n-privados').innerText = privados.length;
                document.getElementById('lista-privados').innerHTML = privados.length
                    ? privados.map(p => `<div class="user-row">
                            <div class="user-info">
                                <span class="user-apodo">${escapeHTML(p.a)} ↔ ${escapeHTML(p.b)}</span>
                            </div>
                            <div class="btn-group">
                                <span class="conteo">${p.n_mensajes} mensajes</span>
                                <button class="btn-eliminar" data-accion="borrar-privado" data-a="${escapeHTML(p.a)}" data-b="${escapeHTML(p.b)}">🗑️ Borrar</button>
                            </div>
                        </div>`).join('')
                    : "<p class='vacio'>No hay ninguna conversación privada.</p>";

                const conectados = data.conectados || [];
                const desconectados = data.desconectados || [];

                document.getElementById('n-conectados').innerText = conectados.length;
                document.getElementById('n-desconectados').innerText = desconectados.length;

                document.getElementById('lista-conectados').innerHTML = conectados.length
                    ? conectados.map(u => filaUsuario(u, true)).join('')
                    : "<p class='vacio'>No hay nadie conectado ahora mismo.</p>";

                document.getElementById('lista-desconectados').innerHTML = desconectados.length
                    ? desconectados.map(u => filaUsuario(u, false)).join('')
                    : "<p class='vacio'>Todos los registrados están conectados.</p>";
            } catch (e) {
                console.error("Error de conexión", e);
            }
        }
        
        async function limpiarArchivos() {
            const previo = await (await fetch('/api_admin/limpiar_archivos', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({solo_mirar: true})
            })).json();

            if (!previo.cuantos) {
                alert(`No hay ningún archivo de más de ${previo.dias} días. No hay nada que limpiar.`);
                return;
            }
            if (!confirm(`Hay ${previo.cuantos} archivos de más de ${previo.dias} días, ocupando ${previo.megas} MB.\\n\\nLos mensajes que los tuvieran quedarán como "mensaje eliminado". ¿Los borro?`)) return;

            const r = await (await fetch('/api_admin/limpiar_archivos', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({solo_mirar: false})
            })).json();
            alert(`Borrados ${r.cuantos} archivos, ${r.megas} MB liberados.`);
            await cargarUsuarios();
        }

        async function borrarGrupo() {
            if(!confirm("¿Borrar todos los mensajes del Grupo Principal?\\n\\nLos chats privados no se tocan.")) return;
            const r = await (await fetch('/api_admin/borrar_grupo', { method: 'POST' })).json();
            alert(`Borrados ${r.borrados} mensajes del grupo.`);
            await cargarUsuarios();
        }

        async function borrarPrivados() {
            if(!confirm("¿Borrar TODOS los chats privados de todo el mundo?\\n\\nEl Grupo Principal no se toca.")) return;
            const r = await (await fetch('/api_admin/borrar_privados', { method: 'POST' })).json();
            alert(`Borrados ${r.borrados} mensajes privados.`);
            await cargarUsuarios();
        }

        async function toggleSilencio() {
            await fetch('/api_admin/toggle_silencio', { method: 'POST' });
            await cargarUsuarios();
        }

        async function togglePuertas() {
            await fetch('/api_admin/toggle_puertas', { method: 'POST' });
            await cargarUsuarios();
        }

        async function togglePro(apodo) {
            await fetch('/api_admin/toggle_pro', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({apodo}) });
            await cargarUsuarios();
        }
        
        async function forcePin(apodo) {
            await fetch('/api_admin/force_pin', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({apodo}) });
            await cargarUsuarios();
        }

        let ultimosDatos = null;

        function abrirTraspaso(destino) {
            if (!ultimosDatos) return;
            const activas = [...ultimosDatos.conectados, ...ultimosDatos.desconectados]
                .filter(u => u.registrado && u.apodo !== destino);
            const antiguas = (ultimosDatos.antiguas || []).filter(u => u.apodo !== destino);

            const opcion = (u, vieja) => `<button class="opcion-cuenta" data-origen="${escapeHTML(u.apodo)}" data-destino="${escapeHTML(destino)}">
                    <span>
                        <span class="opcion-apodo">${escapeHTML(u.apodo)}${u.es_pro ? ' ⭐' : ''}</span><br>
                        <span class="opcion-detalle">${vieja ? '❌ Cuenta eliminada · ' : ''}${escapeHTML(u.nombre_real)}</span>
                    </span>
                    <span class="conteo">${u.n_mensajes} mensajes</span>
                </button>`;

            let html = '';
            if (activas.length) {
                html += '<div class="grupo-titulo">Cuentas actuales</div>';
                html += activas.map(u => opcion(u, false)).join('');
            }
            if (antiguas.length) {
                html += '<div class="grupo-titulo">Cuentas eliminadas que aún tienen datos</div>';
                html += antiguas.map(u => opcion(u, true)).join('');
            }

            document.getElementById('modal-destino').textContent = destino;
            document.getElementById('modal-lista').innerHTML = html || "<p class='vacio'>No hay ninguna otra cuenta de la que traer datos.</p>";
            document.getElementById('modal-traspaso').classList.add('abierto');
        }

        function cerrarTraspaso() {
            document.getElementById('modal-traspaso').classList.remove('abierto');
        }

        document.addEventListener('click', async (e) => {
            const opcion = e.target.closest('button[data-origen]');
            if (!opcion) return;
            const { origen, destino } = opcion.dataset;
            if (!confirm(`¿Pasar todos los mensajes y archivos de "${origen}" a "${destino}"?`)) return;
            const res = await fetch('/api_admin/traspasar_datos', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({origen, destino})
            });
            const data = await res.json();
            cerrarTraspaso();
            if (data.status === 'ok') {
                const extras = [];
                if (data.pro) extras.push('PRO');
                if (data.color) extras.push('color');
                if (data.emoji) extras.push('emoji');
                alert(`Listo: ${data.movidos} mensajes de "${origen}" ahora son de "${destino}".`
                    + (extras.length ? `\nTambién se ha traído: ${extras.join(', ')}.` : ''));
            } else {
                alert('No se ha podido hacer el traspaso.');
            }
            await cargarUsuarios();
        });

        async function eliminarUsuario(apodo) {
            await fetch('/api_admin/eliminar_usuario', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({apodo}) });
            await cargarUsuarios();
        }

        setInterval(cargarUsuarios, 1500);
        cargarUsuarios();
    </script>
</body>
</html>
""".replace("TITULO_AQUI", TITULO_PAGINA)

# -------------------------------------------------------------
# RUTAS DE FLASK
# -------------------------------------------------------------

@app.route("/")
def inicio():
    # Sin el PIN de sala se ve una pantalla de error normal y corriente
    if not session.get("sala_autorizada"):
        return render_template_string(HTML_ERROR_CHROME, cerrado=puertas_cerradas)

    if session.get("apodo") and session.get("nombre_real"):
        session["acceso_concedido"] = True
        return render_template_string(HTML_CHAT, es_pro=es_pro(session.get("apodo")))
    return render_template_string(HTML_SOLICITUD)

@app.route("/login_sala", methods=["POST"])
def login_sala():
    # Con las puertas cerradas el PIN deja de valer, ni siquiera el correcto
    if puertas_cerradas:
        return render_template_string(HTML_ERROR_CHROME, cerrado=True)
    if request.form.get("clave", "") == CLAVE_SALA:
        session["sala_autorizada"] = True
        return redirect(url_for("inicio"))
    return render_template_string(HTML_ERROR_CHROME, cerrado=False, error=True)

@app.route("/desbloquear_apodo", methods=["POST"])
def desbloquear_apodo():
    pin_ingresado = request.form.get("pin", "")
    if pin_ingresado == PIN_DESBLOQUEO:
        apodo = session.get("apodo")
        if apodo in pendientes_pin:
            pendientes_pin.discard(apodo)
            guardar_pendientes()
        generar_nuevo_pin()
        return redirect(url_for("inicio"))
    else:
        return redirect(url_for("inicio", error="1"))

@app.route("/procesar_solicitud", methods=["POST"])
def procesar_solicitud():
    if not session.get("sala_autorizada"):
        return redirect(url_for("inicio"))
        
    nombre_real = request.form.get("nombre_real", "").strip()
    apodo = request.form.get("apodo", "").strip()

    if not nombre_real or not apodo:
        return render_template_string(HTML_SOLICITUD, error="ocupado")

    if apodo in nombres_registrados or nombre_real in nombres_reales_registrados:
        return render_template_string(HTML_SOLICITUD, error="ocupado")

    nombres_registrados.add(apodo)
    nombres_reales_registrados.add(nombre_real)
    guardar_nombres()
    guardar_nombres_reales()
    REGISTRO_NOMBRES[apodo] = nombre_real
    guardar_registro()

    # Un apodo liberado puede acabar en otras manos: que no herede órdenes viejas
    if apodo in pendientes_pin:
        pendientes_pin.discard(apodo)
        guardar_pendientes()

    session["apodo"] = apodo
    session["nombre_real"] = nombre_real
    session["acceso_concedido"] = True

    return redirect(url_for("inicio"))

@app.route("/logout", methods=["GET", "POST"])
def logout():
    sid = session.get("id_sesion")
    if sid and sid in usuarios_activos:
        usuarios_activos.pop(sid)
    session.pop("sala_autorizada", None)
    session.pop("acceso_concedido", None)
    session.pop("es_admin", None)
    if request.method == "POST":
        return "", 200
    return redirect(url_for("inicio"))

@app.route("/desconectar", methods=["POST"])
def desconectar():
    """El navegador avisa aquí al cerrar la pestaña, así la desconexión es inmediata."""
    sid = session.get("id_sesion")
    if sid and sid in usuarios_activos:
        apodo = usuarios_activos[sid]["apodo"]
        usuarios_activos.pop(sid, None)
        print(f"🔴 [CERRÓ LA PESTAÑA] \"{apodo}\" | 👥 Total en línea: {len(usuarios_activos)}")
    return "", 204

@app.route("/estado_sesion")
def estado_sesion():
    if not session.get("acceso_concedido"):
        return jsonify({"apodo": None, "nombre_real": None}), 403
    return jsonify({"apodo": session.get("apodo"), "nombre_real": session.get("nombre_real")})

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(BASE_DIR, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/validar_pin", methods=["POST"])
def validar_pin():
    if not session.get("sala_autorizada"):
        return jsonify({"valido": False}), 403
    global PIN_DESBLOQUEO
    data = request.get_json()
    if data.get("pin") == PIN_DESBLOQUEO:
        apodo_viejo = session.get("apodo")
        nombre_real_viejo = session.get("nombre_real")
        
        if apodo_viejo in nombres_registrados:
            nombres_registrados.remove(apodo_viejo)
            guardar_nombres()
        if nombre_real_viejo in nombres_reales_registrados:
            nombres_reales_registrados.remove(nombre_real_viejo)
            guardar_nombres_reales()
            
        sid = session.get("id_sesion")
        if sid and sid in usuarios_activos:
            usuarios_activos.pop(sid)
            
        session.clear()
        session["sala_autorizada"] = True
        
        generar_nuevo_pin() 
        return jsonify({"valido": True})
    return jsonify({"valido": False})

@app.route("/mensajes")
def obtener_mensajes():
    if not session.get("acceso_concedido"):
        return jsonify({"mensajes": [], "silencio": modo_silencio, "conectados": len(usuarios_activos)}), 403
    
    yo = session.get("apodo", "")
    apodos_en_linea = {info["apodo"] for info in usuarios_activos.values()}
    lista_usuarios = [
        {"apodo": apodo, "en_linea": apodo in apodos_en_linea, "foto": apodo in FOTOS_PERFIL}
        for apodo in sorted(nombres_registrados)
    ]

    # Los privados de los demás no salen de aquí: la propia consulta pide solo lo suyo
    con = conectar_bd()
    filas = con.execute(
        """SELECT * FROM mensajes
           WHERE destinatario = 'todos' OR destinatario = ? OR nombre = ?
           ORDER BY orden""",
        (yo, yo)).fetchall()
    con.close()
    mios = [fila_a_mensaje(f) for f in filas]

    return jsonify({
        "mensajes": mios,
        "silencio": modo_silencio,
        "conectados": len(usuarios_activos),
        "lista_usuarios": lista_usuarios
    })

@app.route("/enviar", methods=["POST"])
def enviar():
    if not session.get("acceso_concedido") or modo_silencio:
        return jsonify({"status": "error"}), 403
    data = request.get_json()
    nombre = session.get("apodo", "Anónimo")
    destinatario = data.get("destinatario", "todos")
    if not puede_escribir_en(destinatario):
        return jsonify({"status": "error", "motivo": "no perteneces a ese chat"}), 403
    guardar_mensaje(nombre, data.get("texto", ""), None, destinatario)
    return jsonify({"status": "ok"})

@app.route("/subir", methods=["POST"])
def subir():
    if not session.get("acceso_concedido") or modo_silencio:
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "Anónimo")
    file = request.files.get("archivo")
    destinatario = request.form.get("destinatario", "todos")
    if not puede_escribir_en(destinatario):
        return jsonify({"status": "error", "motivo": "no perteneces a ese chat"}), 403
    if file:
        nombre_archivo = secure_filename(file.filename)
        if not nombre_archivo:
            return jsonify({"status": "error"}), 400

        # El disco del servidor no es infinito: sin tope, un solo vídeo se lo come
        file.seek(0, os.SEEK_END)
        tamano = file.tell()
        file.seek(0)
        if tamano > MAX_SUBIDA:
            return jsonify({
                "status": "error",
                "motivo": f"el archivo pesa {tamano/1048576:.1f} MB y el máximo son {MAX_SUBIDA//1048576} MB"
            }), 400

        ruta = os.path.join(CARPETA_UPLOADS, nombre_archivo)
        file.save(ruta)
        guardar_mensaje(nombre, None, nombre_archivo, destinatario)
    return jsonify({"status": "ok"})

@app.route("/foto_perfil", methods=["POST"])
def subir_foto_perfil():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    yo = session.get("apodo", "")
    if not es_pro(yo):
        return jsonify({"status": "error", "motivo": "solo PRO"}), 403

    file = request.files.get("foto")
    if not file or not file.filename:
        return jsonify({"status": "error", "motivo": "sin archivo"}), 400

    extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if extension not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return jsonify({"status": "error", "motivo": "tiene que ser una imagen"}), 400

    datos = file.read()
    if len(datos) > 3 * 1024 * 1024:
        return jsonify({"status": "error", "motivo": "la imagen pesa más de 3 MB"}), 400

    # El nombre del archivo lo pone el servidor, nunca el usuario
    nombre_archivo = f"{os.urandom(8).hex()}.{extension}"
    with open(os.path.join(CARPETA_FOTOS, nombre_archivo), 'wb') as f:
        f.write(datos)

    anterior = FOTOS_PERFIL.get(yo)
    FOTOS_PERFIL[yo] = nombre_archivo
    guardar_fotos()
    if anterior and anterior != nombre_archivo:
        try:
            os.remove(os.path.join(CARPETA_FOTOS, anterior))
        except OSError:
            pass
    return jsonify({"status": "ok"})

@app.route("/quitar_foto", methods=["POST"])
def quitar_foto_perfil():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    yo = session.get("apodo", "")
    nombre_archivo = FOTOS_PERFIL.pop(yo, None)
    if nombre_archivo:
        guardar_fotos()
        try:
            os.remove(os.path.join(CARPETA_FOTOS, nombre_archivo))
        except OSError:
            pass
    return jsonify({"status": "ok"})

@app.route("/foto/<apodo>")
def ver_foto_perfil(apodo):
    if not session.get("acceso_concedido"):
        return "Acceso denegado", 403
    nombre_archivo = FOTOS_PERFIL.get(apodo)
    if not nombre_archivo:
        return "Sin foto", 404
    return send_from_directory(CARPETA_FOTOS, nombre_archivo)

@app.route("/borrar_mensaje", methods=["POST"])
def borrar_mensaje():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "")
    id_mensaje = (request.get_json() or {}).get("id")

    con = conectar_bd()
    fila = con.execute("SELECT nombre, archivo FROM mensajes WHERE id = ?", (id_mensaje,)).fetchone()
    if not fila:
        con.close()
        return jsonify({"status": "error", "motivo": "no existe"}), 404
    # Cada uno solo puede borrar lo que ha escrito él
    if fila["nombre"] != nombre:
        con.close()
        return jsonify({"status": "error", "motivo": "no es tuyo"}), 403

    adjunto = fila["archivo"]
    with con:
        con.execute(
            "UPDATE mensajes SET texto = NULL, archivo = NULL, eliminado = 1 WHERE id = ?",
            (id_mensaje,))

    # El archivo se va del disco solo si ningún otro mensaje lo sigue usando
    if adjunto:
        quedan = con.execute(
            "SELECT COUNT(*) FROM mensajes WHERE archivo = ?", (adjunto,)).fetchone()[0]
        if quedan == 0:
            try:
                os.remove(os.path.join(CARPETA_UPLOADS, adjunto))
            except OSError:
                pass
    con.close()
    return jsonify({"status": "ok"})

@app.route("/estado_pro")
def estado_pro():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "")
    return jsonify({"pro": es_pro(nombre), "color": COLORES_USUARIOS.get(nombre, ""), "emoji": EMOJIS_USUARIOS.get(nombre, "⭐")})

@app.route("/color", methods=["POST"])
def color():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "Anónimo")
    if not es_pro(nombre):
        return jsonify({"status": "error", "motivo": "no eres Pro"}), 403
    data = request.get_json() or {}
    color_elegido = data.get("color", "")
    if color_elegido and color_elegido not in COLORES_PERMITIDOS:
        return jsonify({"status": "error", "motivo": "color no válido"}), 400
    if color_elegido:
        COLORES_USUARIOS[nombre] = color_elegido
    else:
        COLORES_USUARIOS.pop(nombre, None)
    guardar_colores()
    return jsonify({"status": "ok"})

@app.route("/emoji", methods=["POST"])
def emoji():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "Anónimo")
    if not es_pro(nombre):
        return jsonify({"status": "error", "motivo": "no eres Pro"}), 403
    data = request.get_json() or {}
    emoji_elegido = data.get("emoji", "⭐")
    if emoji_elegido not in EMOJIS_PERMITIDOS:
        return jsonify({"status": "error", "motivo": "emoji no válido"}), 400
    EMOJIS_USUARIOS[nombre] = emoji_elegido
    guardar_emojis()
    return jsonify({"status": "ok"})

@app.route("/descargar/<filename>")
def descargar(filename):
    if not session.get("acceso_concedido"):
        return "Acceso denegado", 403
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    url_raw = url_for('archivo_raw', filename=filename)
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        tag = f'<img src="{url_raw}" alt="Imagen">'
    elif ext in ['mp4', 'webm', 'ogg']:
        tag = f'<video controls autoplay src="{url_raw}"></video>'
    else:
        tag = f'<iframe src="{url_raw}"></iframe>'
    return render_template_string(HTML_VISOR.replace("CONTENIDO_VISOR", tag))

@app.route("/archivo_raw/<filename>")
def archivo_raw(filename):
    if not session.get("acceso_concedido"):
        return "Acceso denegado", 403
    return send_from_directory(CARPETA_UPLOADS, filename)

@app.route("/adminpanel", methods=["GET", "POST"])
def panel_admin_secreto():
    if request.method == "POST":
        clave = request.form.get("clave", "")
        if clave == CLAVE_ADMIN:
            session["es_admin"] = True
            return redirect(url_for("panel_admin_secreto"))
        else:
            return redirect(url_for("inicio"))

    if not session.get("es_admin"):
        return render_template_string(HTML_LOGIN_ADMIN)

    return render_template_string(HTML_ADMIN)

@app.route("/api_admin/usuarios")
def api_admin_usuarios():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    por_autor = mensajes_por_autor()

    def ficha(apodo, nombre_real):
        return {
            "apodo": apodo,
            "nombre_real": nombre_real,
            "es_pro": es_pro(apodo),
            "pin_pendiente": apodo in pendientes_pin,
            "n_mensajes": por_autor.get(apodo, 0),
            "registrado": apodo in nombres_registrados
        }

    conectados = [ficha(info["apodo"], info["nombre_real"]) for info in usuarios_activos.values()]
    apodos_conectados = {info["apodo"] for info in usuarios_activos.values()}
    desconectados = [
        ficha(apodo, REGISTRO_NOMBRES.get(apodo, "—"))
        for apodo in sorted(nombres_registrados) if apodo not in apodos_conectados
    ]

    # Cuentas ya eliminadas de las que aún queda algo: las guardadas al borrarlas,
    # más cualquier apodo que siga apareciendo en los mensajes sin estar registrado
    claves_antiguas = (set(CUENTAS_ANTIGUAS) | set(por_autor)) - nombres_registrados
    antiguas = []
    for apodo in sorted(claves_antiguas):
        guardada = CUENTAS_ANTIGUAS.get(apodo, {})
        antiguas.append({
            "apodo": apodo,
            "nombre_real": guardada.get("nombre_real", "—"),
            "es_pro": guardada.get("pro", False),
            "n_mensajes": por_autor.get(apodo, 0)
        })

    # Cada conversación privada, juntando los dos sentidos (A→B y B→A son el mismo chat)
    con = conectar_bd()
    filas = con.execute(
        """SELECT nombre, destinatario, COUNT(*) AS n FROM mensajes
           WHERE destinatario != 'todos' GROUP BY nombre, destinatario""").fetchall()
    con.close()
    parejas = {}
    for f in filas:
        clave = tuple(sorted([f["nombre"], f["destinatario"]]))
        parejas[clave] = parejas.get(clave, 0) + f["n"]
    privados = [
        {"a": a, "b": b, "n_mensajes": n}
        for (a, b), n in sorted(parejas.items(), key=lambda kv: -kv[1])
    ]

    return jsonify({
        "pin_actual": PIN_DESBLOQUEO,
        "conectados": conectados,
        "desconectados": desconectados,
        "antiguas": antiguas,
        "privados": privados,
        "modo_silencio": modo_silencio,
        "puertas_cerradas": puertas_cerradas,
        "stats": {
            "conectados": len(usuarios_activos),
            "registrados": len(nombres_registrados),
            "uptime": obtener_tiempo_activo(),
            "mensajes": sum(por_autor.values())
        }
    })

@app.route("/api_admin/borrar_grupo", methods=["POST"])
def api_admin_borrar_grupo():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    con = conectar_bd()
    with con:
        borrados = con.execute("DELETE FROM mensajes WHERE destinatario = 'todos'").rowcount
    con.close()
    return jsonify({"status": "ok", "borrados": borrados})

@app.route("/api_admin/borrar_privados", methods=["POST"])
def api_admin_borrar_privados():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    con = conectar_bd()
    with con:
        borrados = con.execute("DELETE FROM mensajes WHERE destinatario != 'todos'").rowcount
    con.close()
    return jsonify({"status": "ok", "borrados": borrados})

@app.route("/api_admin/limpiar_archivos", methods=["POST"])
def api_admin_limpiar_archivos():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    solo_mirar = (request.get_json() or {}).get("solo_mirar", True)

    limite = time.time() - DIAS_ARCHIVO_VIEJO * 86400
    viejos, bytes_totales = [], 0
    for nombre in os.listdir(CARPETA_UPLOADS):
        ruta = os.path.join(CARPETA_UPLOADS, nombre)
        if os.path.isfile(ruta) and os.path.getmtime(ruta) < limite:
            viejos.append(nombre)
            bytes_totales += os.path.getsize(ruta)

    if solo_mirar or not viejos:
        return jsonify({
            "status": "ok", "solo_mirar": True, "dias": DIAS_ARCHIVO_VIEJO,
            "cuantos": len(viejos), "megas": round(bytes_totales / 1048576, 2)
        })

    # Los mensajes que apuntaban a esos archivos quedan como "mensaje eliminado",
    # para que no se vea un enlace roto en el chat
    con = conectar_bd()
    with con:
        for nombre in viejos:
            con.execute(
                "UPDATE mensajes SET archivo = NULL, eliminado = 1 WHERE archivo = ?", (nombre,))
    con.close()

    borrados = 0
    for nombre in viejos:
        try:
            os.remove(os.path.join(CARPETA_UPLOADS, nombre))
            borrados += 1
        except OSError:
            pass

    print(f"🧹 [ADMIN] borrados {borrados} archivos de más de {DIAS_ARCHIVO_VIEJO} días")
    return jsonify({
        "status": "ok", "solo_mirar": False,
        "cuantos": borrados, "megas": round(bytes_totales / 1048576, 2)
    })

@app.route("/api_admin/borrar_privado", methods=["POST"])
def api_admin_borrar_privado():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json() or {}
    a, b = data.get("a"), data.get("b")
    if not a or not b:
        return jsonify({"status": "error", "motivo": "faltan las dos personas"}), 400

    # Los dos sentidos de la conversación
    con = conectar_bd()
    with con:
        borrados = con.execute(
            """DELETE FROM mensajes
               WHERE (nombre = ? AND destinatario = ?) OR (nombre = ? AND destinatario = ?)""",
            (a, b, b, a)).rowcount
    con.close()
    print(f"🗑️ [ADMIN] borrada la conversación {a} ↔ {b} ({borrados} mensajes)")
    return jsonify({"status": "ok", "borrados": borrados})

@app.route("/api_admin/toggle_silencio", methods=["POST"])
def api_admin_toggle_silencio():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    global modo_silencio
    modo_silencio = not modo_silencio
    return jsonify({"status": "ok", "modo_silencio": modo_silencio})

@app.route("/api_admin/toggle_puertas", methods=["POST"])
def api_admin_toggle_puertas():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    global puertas_cerradas
    puertas_cerradas = not puertas_cerradas
    return jsonify({"status": "ok", "puertas_cerradas": puertas_cerradas})

@app.route("/api_admin/toggle_pro", methods=["POST"])
def api_admin_toggle_pro():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    apodo = data.get("apodo")
    if apodo in nombres_registrados:
        if apodo in USUARIOS_PRO:
            USUARIOS_PRO.discard(apodo)
        else:
            USUARIOS_PRO.add(apodo)
        guardar_pro()
    return jsonify({"status": "ok"})

@app.route("/api_admin/force_pin", methods=["POST"])
def api_admin_force_pin():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    apodo = data.get("apodo")
    if apodo in nombres_registrados:
        if apodo in pendientes_pin:
            pendientes_pin.discard(apodo)
        else:
            pendientes_pin.add(apodo)
        guardar_pendientes()
    return jsonify({"status": "ok"})

@app.route("/api_admin/traspasar_datos", methods=["POST"])
def api_admin_traspasar_datos():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    origen = data.get("origen")
    destino = data.get("destino")

    if not origen or not destino or origen == destino:
        return jsonify({"status": "error", "motivo": "cuentas no válidas"}), 400
    if destino not in nombres_registrados:
        return jsonify({"status": "error", "motivo": "la cuenta de destino no existe"}), 400

    con = conectar_bd()
    movidos = con.execute(
        "SELECT COUNT(*) FROM mensajes WHERE nombre = ? OR destinatario = ?",
        (origen, origen)).fetchone()[0]
    with con:
        con.execute("UPDATE mensajes SET nombre = ? WHERE nombre = ?", (destino, origen))
        con.execute("UPDATE mensajes SET destinatario = ? WHERE destinatario = ?", (destino, origen))
    con.close()

    # Lo que tenía la cuenta vieja: si sigue registrada se mira en vivo,
    # y si ya la eliminaste se saca de lo que se guardó al borrarla
    antigua = CUENTAS_ANTIGUAS.get(origen, {})
    era_pro = origen in USUARIOS_PRO or antigua.get("pro", False)
    color_viejo = COLORES_USUARIOS.get(origen) or antigua.get("color", "")
    emoji_viejo = EMOJIS_USUARIOS.get(origen) or antigua.get("emoji", "")

    if era_pro:
        USUARIOS_PRO.add(destino)
        guardar_pro()
    if color_viejo:
        COLORES_USUARIOS[destino] = color_viejo
        guardar_colores()
    if emoji_viejo:
        EMOJIS_USUARIOS[destino] = emoji_viejo
        guardar_emojis()

    # Ya está todo en la cuenta nueva: la vieja deja de aparecer en la lista
    if origen in CUENTAS_ANTIGUAS:
        CUENTAS_ANTIGUAS.pop(origen, None)
        guardar_antiguas()

    print(f"🔄 [TRASPASO] {movidos} mensajes de \"{origen}\" pasan a \"{destino}\" (pro={era_pro})")
    return jsonify({
        "status": "ok",
        "movidos": movidos,
        "pro": era_pro,
        "color": bool(color_viejo),
        "emoji": bool(emoji_viejo)
    })

@app.route("/api_admin/eliminar_usuario", methods=["POST"])
def api_admin_eliminar_usuario():
    if not session.get("es_admin"):
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    apodo = data.get("apodo")
    if apodo in nombres_registrados:
        nombres_registrados.discard(apodo)
        guardar_nombres()

        nombre_real = REGISTRO_NOMBRES.pop(apodo, None)
        guardar_registro()
        if nombre_real in nombres_reales_registrados:
            nombres_reales_registrados.discard(nombre_real)
            guardar_nombres_reales()

        # Se guarda lo que tenía por si luego quiere pasárselo a una cuenta nueva
        CUENTAS_ANTIGUAS[apodo] = {
            "nombre_real": nombre_real or "—",
            "pro": apodo in USUARIOS_PRO,
            "color": COLORES_USUARIOS.get(apodo, ""),
            "emoji": EMOJIS_USUARIOS.get(apodo, "")
        }
        guardar_antiguas()

        USUARIOS_PRO.discard(apodo)
        guardar_pro()
        COLORES_USUARIOS.pop(apodo, None)
        guardar_colores()
        EMOJIS_USUARIOS.pop(apodo, None)
        guardar_emojis()

        pendientes_pin.discard(apodo)
        guardar_pendientes()

        foto = FOTOS_PERFIL.pop(apodo, None)
        if foto:
            guardar_fotos()
            try:
                os.remove(os.path.join(CARPETA_FOTOS, foto))
            except OSError:
                pass

        for sid in [s for s, info in usuarios_activos.items() if info["apodo"] == apodo]:
            usuarios_activos.pop(sid, None)

        print(f"❌ [ELIMINADO] \"{apodo}\" borrado por el administrador")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    ip = obtener_ip_local()
    print("\n" + "="*50)
    print(f"🚀 CHAT INICIADO EN MODO AUTOMÁTICO (SEGUNDO PLANO)")
    print(f"🌐 Enlace de acceso: http://{ip}:{PUERTO_CHAT}")
    print(f"🔑 PIN DE LA SALA:   {CLAVE_SALA}")
    print(f"🛠️ PANEL DE ADMIN:   http://{ip}:{PUERTO_CHAT}/adminpanel")
    print("="*50 + "\n")
    
    app.run(host="0.0.0.0", port=PUERTO_CHAT, debug=False, use_reloader=False, threaded=True)
