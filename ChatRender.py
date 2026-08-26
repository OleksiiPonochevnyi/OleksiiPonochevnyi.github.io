import os
import random
import socket
import json
import time
import threading
from datetime import timedelta
from flask import Flask, render_template_string, request, jsonify, send_from_directory, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "clave_secreta_fija_para_sesiones_chat_2026"
app.permanent_session_lifetime = timedelta(days=30)

# Detecta automáticamente la carpeta de trabajo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_UPLOADS = os.path.join(BASE_DIR, 'Archivos_Chat')
os.makedirs(CARPETA_UPLOADS, exist_ok=True)

ARCHIVO_NOMBRES = os.path.join(BASE_DIR, 'nombres.json')
ARCHIVO_NOMBRES_REALES = os.path.join(BASE_DIR, 'nombres_reales.json')

usuarios_activos = {}

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

CLAVE_SALA = "0000"
PIN_DESBLOQUEO = str(random.randint(1000, 9999))
mensajes = []

TITULO_PAGINA = "NCA_ESO_2_ING: ING.ESO2.IN01.ENG.Exchange_Programs_Dialogue.pdf | Contenidos2ESO"

def generar_nuevo_pin():
    global PIN_DESBLOQUEO
    PIN_DESBLOQUEO = str(random.randint(1000, 9999))
    print("\n" + "="*40)
    print(f"🔄 ¡EL PIN DE CAMBIO DE APODO HA CAMBIADO!")
    print(f"🔑 NUEVO PIN DE ADMINISTRADOR: {PIN_DESBLOQUEO}")
    print("="*40 + "\n")

@app.before_request
def rastrear_conexiones_automaticas():
    session.permanent = True
    if request.endpoint == 'logout':
        return

    if session.get("acceso_concedido"):
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
        
        if es_nuevo:
            total = len(usuarios_activos)
            print(f"\n🟢 [CONEXIÓN EN VIVO] Apodo: \"{apodo_actual}\" | Nombre Real: \"{nombre_real_actual}\" | 👥 Total en línea: {total}\n")

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
                total = len(usuarios_activos)
                print(f"\n🔴 [DESCONEXIÓN] Apodo: \"{apodo}\" (Nombre Real: {nombre_real}) se ha desconectado (Inactividad). | 👥 Total en línea: {total}\n")

threading.Thread(target=monitor_desconexiones, daemon=True).start()

# -------------------------------------------------------------
# PLANTILLAS HTML
# -------------------------------------------------------------
HTML_ERROR_CHROME = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITULO_AQUI</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=2">
    <style>
        body { background-color: #202124; color: #e8eaed; font-family: 'Segoe UI', Tahoma, Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; width: 100vw; overflow: hidden; }
        .chrome-error-container { text-align: left; max-width: 420px; width: 90%; padding: 20px; }
        .chrome-icon { width: 72px; height: 72px; background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="%239aa0a6"><path d="M44 24c0 11.045-8.955 20-20 20S4 35.045 4 24 4s20 8.955 20 20zM24 18c-3.31 0-6 2.69-6 6s2.69 6 6 6-2.69 6-6-6zm16.93 3c-.92-5.13-4.2-9.43-8.81-11.72L26.6 21h14.33zm-19.3-8.89C16.81 12.87 12.96 16.5 11.13 21h12.81l-2.31-8.89zM10.16 27c.48 5.2 3.6 9.61 8.07 12.02L24.6 27H10.16zm20.8 11.89c4.83-1.76 8.61-5.46 10.32-10.11H28.46l2.5 10.11z"/></svg>'); background-size: contain; background-repeat: no-repeat; margin-bottom: 40px; }
        .chrome-h1 { font-size: 24px; font-weight: 500; margin-top: 0; margin-bottom: 10px; line-height: 1.25; color: #e8eaed; }
        .chrome-p { font-size: 15px; line-height: 1.6; margin-top: 0; margin-bottom: 15px; color: #9aa0a6; }
        .chrome-error-code { font-family: monospace; font-size: 13px; color: #9aa0a6; margin-bottom: 25px; text-transform: uppercase; }
        .login-form { display: flex; flex-direction: column; gap: 12px; }
        .chrome-input { background-color: #202124; border: 1px solid #5f6368; color: #e8eaed; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 14px; padding: 10px 14px; border-radius: 4px; outline: none; width: 100%; box-sizing: border-box; }
        .chrome-input:focus { border-color: #8ab4f8; }
        .chrome-input::placeholder { color: #5f6368; }
        .chrome-button { background-color: #8ab4f8; color: #202124; border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: 500; cursor: pointer; align-self: flex-start; }
        .chrome-button:hover { background-color: #9bbbe8; }
        .error-message { color: #f28b82; font-size: 13px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="chrome-error-container">
        <div class="chrome-icon"></div>
        <h1 class="chrome-h1">No se puede acceder a este sitio web</h1>
        <p class="chrome-p">La página web en la dirección dada puede estar temporalmente inactiva o se ha trasladado permanentemente a una nueva dirección web.</p>
        <div class="chrome-error-code">ERR_CONNECTION_REFUSED</div>
        <form class="login-form" action="/login_sala" method="POST">
            <input type="password" name="clave" class="chrome-input" placeholder="Introduce el PIN de acceso..." required autofocus>
            <button type="submit" class="chrome-button">Cargar de nuevo</button>
        </form>
        {% if error %}
            <div class="error-message">⚠️ Error al conectar. Código PIN incorrecto.</div>
        {% endif %}
    </div>
</body>
</html>
""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_SOLICITUD = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITULO_AQUI</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=2">
    <style>
        body { background-color: #0f172a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; border: 1px solid #334155; }
        h2 { color: #38bdf8; margin-top: 0; margin-bottom: 10px; font-size: 22px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 20px; }
        .form-group { display: flex; flex-direction: column; gap: 12px; }
        input { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #334155; color: #ffffff; font-size: 14px; outline: none; }
        input:focus { border-color: #38bdf8; }
        button { padding: 12px; border-radius: 8px; border: none; background: #38bdf8; color: #0f172a; font-weight: bold; cursor: pointer; font-size: 15px; margin-top: 5px; }
        button:hover { background: #7dd3fc; }
        .error { color: #f87171; font-size: 13px; margin-top: 10px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Identificación requerida</h2>
        <p>Introduce tus datos para solicitar acceso a la sala.</p>
        <form class="form-group" action="/procesar_solicitud" method="POST">
            <input type="text" name="nombre_real" placeholder="Tu Nombre Real..." required autofocus>
            <input type="text" name="apodo" placeholder="Tu Apodo Público (No pongas tu nombre real)..." required>
            <button type="submit">Solicitar Acceso</button>
        </form>
        {% if error == "denegado" %}
            <div class="error">❌ El administrador ha denegado tu acceso.</div>
        {% elif error == "ocupado" %}
            <div class="error">⚠️ Ese nombre real o apodo ya está en uso. Prueba con otros.</div>
        {% endif %}
    </div>
</body>
</html>
""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_CHAT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITULO_AQUI</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=2">
    <style>
        :root {
            --bg-color: #0f172a; --card-bg: #1e293b; --chat-bg: #0f172a;
            --text-color: #ffffff; --accent-color: #38bdf8; --user-color: #facc15;
            --msg-bg: #334155; --border-color: #334155; --warning-bg: #7f1d1d;
            --warning-text: #fecaca; --info-bg: #713f12; --info-text: #fef08a;
            --danger-bg: #7c2d12; --danger-text: #ffedd5;
            --input-bg: #334155; --input-text: #ffffff;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body.theme-hacker {
            --bg-color: #000000; --card-bg: #050505; --chat-bg: #000000;
            --text-color: #00ff00; --accent-color: #00ff00; --user-color: #00cc00;
            --msg-bg: #001100; --border-color: #00ff00; --warning-bg: #002200;
            --warning-text: #00ff00; --info-bg: #003300; --info-text: #00ff00;
            --danger-bg: #002200; --danger-text: #00ff00;
            --input-bg: #001100; --input-text: #00ff00;
            --font-family: "Courier New", Courier, monospace;
        }
        body.theme-cyberpunk {
            --bg-color: #120458; --card-bg: #1f024c; --chat-bg: #120458;
            --text-color: #ff007f; --accent-color: #00f6ff; --user-color: #ffea00;
            --msg-bg: #2d006b; --border-color: #ff007f; --warning-bg: #4a001f;
            --warning-text: #ff80bf; --info-bg: #3a2e00; --info-text: #fff380;
            --danger-bg: #5a0033; --danger-text: #ff99cc;
            --input-bg: #2d006b; --input-text: #ff007f;
            --font-family: "Trebuchet MS", sans-serif;
        }
        body.theme-dracula {
            --bg-color: #282a36; --card-bg: #44475a; --chat-bg: #282a36;
            --text-color: #f8f8f2; --accent-color: #bd93f9; --user-color: #50fa7b;
            --msg-bg: #6272a4; --border-color: #bd93f9; --warning-bg: #ff5555;
            --warning-text: #f8f8f2; --info-bg: #ffb86c; --info-text: #282a36;
            --danger-bg: #ffb86c; --danger-text: #282a36;
            --input-bg: #282a36; --input-text: #f8f8f2;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body.theme-light {
            --bg-color: #f1f5f9; --card-bg: #ffffff; --chat-bg: #f8fafc;
            --text-color: #0f172a; --accent-color: #2563eb; --user-color: #d97706;
            --msg-bg: #e2e8f0; --border-color: #cbd5e1; --warning-bg: #fee2e2;
            --warning-text: #991b1b; --info-bg: #fef3c7; --info-text: #92400e;
            --danger-bg: #ffedd5; --danger-text: #9a3412;
            --input-bg: #ffffff; --input-text: #0f172a;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body.theme-forest {
            --bg-color: #1c2e24; --card-bg: #273e31; --chat-bg: #1c2e24;
            --text-color: #e2fbe8; --accent-color: #4ade80; --user-color: #fde047;
            --msg-bg: #355241; --border-color: #40634e; --warning-bg: #5c1d1d;
            --warning-text: #fecaca; --info-bg: #524716; --info-text: #fef08a;
            --danger-bg: #632211; --danger-text: #fed7aa;
            --input-bg: #355241; --input-text: #e2fbe8;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body.theme-solarized {
            --bg-color: #002b36; --card-bg: #073642; --chat-bg: #002b36;
            --text-color: #839496; --accent-color: #2aa198; --user-color: #b58900;
            --msg-bg: #094755; --border-color: #586e75; --warning-bg: #dc322f;
            --warning-text: #eee8d5; --info-bg: #cb4b16; --info-text: #eee8d5;
            --danger-bg: #6c71c4; --danger-text: #eee8d5;
            --input-bg: #073642; --input-text: #93a1a1;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body.theme-candy {
            --bg-color: #2b1b36; --card-bg: #3d254f; --chat-bg: #2b1b36;
            --text-color: #ffd1dc; --accent-color: #ff77a9; --user-color: #ffe66d;
            --msg-bg: #53336c; --border-color: #6b418c; --warning-bg: #802e3b;
            --warning-text: #ffb3ba; --info-bg: #7a6321; --info-text: #ffffba;
            --danger-bg: #8c3f5d; --danger-text: #ffdfba;
            --input-bg: #53336c; --input-text: #ffd1dc;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        body { font-family: var(--font-family); background: var(--bg-color); color: var(--text-color); margin: 0; padding: 15px; display: flex; justify-content: center; transition: background 0.3s ease; height: 100vh; overflow: hidden; }
        #main-container { width: 100%; max-width: 500px; display: flex; flex-direction: column; height: 95vh; }
        .card { background: var(--card-bg); padding: 15px 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); display: flex; flex-direction: column; flex: 1; box-sizing: border-box; border: 1px solid var(--border-color); overflow: hidden; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-shrink: 0;}
        .header-actions { display: flex; align-items: center; gap: 8px; }
        h2 { margin: 0; color: var(--accent-color); font-size: 18px; position: relative; }
        #new-messages-dot { display: none; position: absolute; top: -5px; right: -10px; width: 8px; height: 8px; background-color: var(--accent-color); border-radius: 50%; }
        select.theme-selector { background: var(--msg-bg); color: var(--text-color); border: 1px solid var(--border-color); padding: 5px; border-radius: 6px; font-size: 12px; cursor: pointer; }
        .btn-logout { background: #ef4444; color: #ffffff; border: none; padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; cursor: pointer; text-decoration: none; }
        .btn-logout:hover { background: #dc2626; }
        .warning-box { background: var(--warning-bg); color: var(--warning-text); font-size: 11px; padding: 6px 10px; border-radius: 8px; margin-bottom: 6px; text-align: center; border: 1px solid var(--border-color); flex-shrink: 0; }
        .info-box { background: var(--info-bg); color: var(--info-text); font-size: 11px; padding: 6px 10px; border-radius: 8px; margin-bottom: 6px; text-align: center; border: 1px solid var(--border-color); flex-shrink: 0; }
        .danger-box { background: var(--danger-bg); color: var(--danger-text); font-size: 11px; padding: 6px 10px; border-radius: 8px; margin-bottom: 10px; text-align: center; border: 1px solid var(--border-color); flex-shrink: 0; }
        #chat-box { flex: 1; overflow-y: auto; background: var(--chat-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; overflow-anchor: none; }
        .msg { background: var(--msg-bg); padding: 8px 12px; border-radius: 10px; word-break: break-word; border: 1px solid var(--border-color); flex-shrink: 0;}
        .msg-user { font-weight: bold; color: var(--user-color); font-size: 13px; }
        .msg-file { color: var(--accent-color); text-decoration: underline; }
        .inputs { display: flex; flex-direction: column; gap: 8px; flex-shrink: 0;}
        input[type="text"] { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--input-text); font-size: 14px; width: 100%; box-sizing: border-box; }
        input[disabled] { opacity: 0.6; cursor: not-allowed; }
        .row { display: flex; gap: 8px; }
        button { padding: 10px 15px; border-radius: 8px; border: none; background: var(--accent-color); color: #000; font-weight: bold; cursor: pointer; }
        .file-btn { background: #a855f7; color: white; }
        .btn-pin { background: #eab308; color: #000; font-size: 11px; padding: 4px 8px; border-radius: 5px; font-weight: bold; }
    </style>
</head>
<body id="body-tag">
    <div id="main-container">
        <div class="card">
            <div class="header">
                <h2>Chat <span id="new-messages-dot"></span></h2>
                <div class="header-actions">
                    <select class="theme-selector" onchange="cambiarTema(this.value)" id="selector-tema">
                        <option value="default">🌌 Oscuro (Por defecto)</option>
                        <option value="hacker">💻 Hacker (Verde/Negro)</option>
                        <option value="cyberpunk">👾 Cyberpunk</option>
                        <option value="dracula">🧛 Dracula</option>
                        <option value="light">☀️ Claro / Minimalista</option>
                        <option value="forest">🌿 Bosque / Nature</option>
                        <option value="solarized">⚡ Solarized Dark</option>
                        <option value="candy">🍬 Pastel / Candy</option>
                    </select>
                    <a href="/logout" class="btn-logout">🚪 Salir</a>
                </div>
            </div>
            <div class="warning-box">🔒 <strong>Nombre Real:</strong> Solo el administrador lo verá (¡No se permiten nombres reales duplicados!).</div>
            <div class="info-box">🔑 Para cambiar tus datos deberás pedir el PIN al administrador.</div>
            <div class="danger-box">⚠️ <strong>Aviso:</strong> En el campo de apodo <strong>no pongas tu nombre real</strong>, utiliza un alias o mote público.</div>
            
            <div style="margin-bottom: 10px; flex-shrink: 0; display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <label style="font-size: 11px; opacity: 0.8;">Tus Datos <span id="status"></span></label>
                    <button id="btnCambiar" class="btn-pin" style="display:none;" onclick="solicitarCambioNombre()">🔑 Cambiar Datos</button>
                </div>
                <input type="text" id="nombre_real" placeholder="Tu Nombre Real (Privado, único)..." disabled>
                <input type="text" id="nombre" placeholder="Tu Apodo (Público, visible para todos)..." disabled>
            </div>

            <div id="chat-box"></div>
            
            <div class="inputs">
                <div class="row">
                    <input type="text" id="mensaje" placeholder="Escribe un mensaje y pulsa Enter..." style="flex:1;">
                    <button onclick="enviarMensaje()">Enviar</button>
                </div>
                <div class="row">
                    <input type="file" id="archivoInput" style="display:none;" onchange="subirArchivo()">
                    <button class="file-btn" style="width:100%;" onclick="document.getElementById('archivoInput').click()">📁 Subir Archivo</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        window.addEventListener("beforeunload", function() {
            navigator.sendBeacon("/logout");
        });

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

            try {
                const res = await fetch('/estado_sesion');
                const data = await res.json();
                if (data.apodo && data.nombre_real) {
                    bloquearNombre(data.apodo, data.nombre_real);
                }
            } catch (e) {
                console.error(e);
            }

            setInterval(cargarMensajes, 1500);
            cargarMensajes(); 
        };

        function cambiarTema(tema) {
            const body = document.getElementById('body-tag');
            body.className = '';
            if (tema !== 'default') body.classList.add('theme-' + tema);
            localStorage.setItem('chat_theme', tema);
        }

        function bloquearNombre(apodo, nombreReal) {
            const inputApodo = document.getElementById('nombre');
            const inputReal = document.getElementById('nombre_real');
            
            inputApodo.value = apodo;
            inputReal.value = nombreReal;
            document.getElementById('status').innerText = '🔒';
            document.getElementById('btnCambiar').style.display = 'inline-block';
        }

        async function solicitarCambioNombre() {
            const pin = prompt("Pide el PIN al administrador para cambiar tus datos:");
            if (!pin) return;

            const res = await fetch('/validar_pin', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pin: pin})
            });

            const data = await res.json();
            if (data.valido) {
                alert("⚠️ Tus datos anteriores han sido eliminados. Ahora podrás introducir un nuevo nombre y apodo.");
                window.location.href = '/logout';
            } else {
                alert("❌ PIN incorrecto.");
            }
        }

        let totalMensajesAnterior = 0; 
        const chatBox = document.getElementById('chat-box');
        const notificacionPunto = document.getElementById('new-messages-dot');

        function usuarioEstaAbajo() {
            return chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 5;
        }

        function bajarScroll() {
            chatBox.scrollTop = chatBox.scrollHeight;
            notificacionPunto.style.display = 'none'; 
        }

        async function cargarMensajes() {
            try {
                const res = await fetch('/mensajes');
                if (!res.ok) { window.location.reload(); return; }
                const lista = await res.json();
                const box = document.getElementById('chat-box');
                const estabaAbajo = usuarioEstaAbajo();
                box.innerHTML = '';
                lista.forEach(m => {
                    let contenido = m.texto;
                    if (m.archivo) contenido = `<a href="/descargar/${m.archivo}" target="_blank" class="msg-file">📄 ${m.archivo}</a>`;
                    box.innerHTML += `<div class="msg"><div class="msg-user">${m.nombre}</div><div>${contenido}</div></div>`;
                });

                if (lista.length > totalMensajesAnterior) {
                    if (estabaAbajo) bajarScroll();
                    else notificacionPunto.style.display = 'block';
                    totalMensajesAnterior = lista.length; 
                } else if (estabaAbajo) {
                    bajarScroll();
                }
            } catch (error) {
                window.location.reload();
            }
        }

        async function enviarMensaje() {
            const msg = document.getElementById('mensaje').value.trim();
            if (!msg) return;

            await fetch('/enviar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({texto: msg})
            });

            document.getElementById('mensaje').value = '';
            await cargarMensajes(); 
            bajarScroll(); 
        }

        async function subirArchivo() {
            const input = document.getElementById('archivoInput');
            if (!input.files[0]) return;

            const formData = new FormData();
            formData.append('archivo', input.files[0]);

            await fetch('/subir', { method: 'POST', body: formData });

            input.value = '';
            await cargarMensajes();
            bajarScroll();
        }
    </script>
</body>
</html>
""".replace("TITULO_AQUI", TITULO_PAGINA)

HTML_VISOR = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITULO_AQUI</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico?v=2">
    <style>
        body { background-color: #0f172a; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; }
        .viewer-container { width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; }
        img, video { max-width: 100%; max-height: 100%; object-fit: contain; }
        iframe { width: 100%; height: 100%; border: none; }
    </style>
</head>
<body>
    <div class="viewer-container">CONTENIDO_VISOR</div>
</body>
</html>
""".replace("TITULO_AQUI", TITULO_PAGINA)

# -------------------------------------------------------------
# RUTAS DE FLASK
# -------------------------------------------------------------

@app.route("/")
def inicio():
    if session.get("sala_autorizada"):
        if session.get("apodo") and session.get("nombre_real"):
            session["acceso_concedido"] = True
            return render_template_string(HTML_CHAT)
        else:
            return render_template_string(HTML_SOLICITUD)
    
    return render_template_string(HTML_ERROR_CHROME)

@app.route("/login_sala", methods=["POST"])
def login_sala():
    clave_ingresada = request.form.get("clave", "")
    if clave_ingresada == CLAVE_SALA:
        session.permanent = True
        session["sala_autorizada"] = True
        return redirect(url_for("inicio"))
    return render_template_string(HTML_ERROR_CHROME, error=True)

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

    print("\n" + "="*50)
    print(f"🔔 ¡SOLICITUD DE ACCESO A LA SALA!")
    print(f"   👤 Nombre Real: {nombre_real}")
    print(f"   💬 Apodo:       {apodo}")
    decision = input("👉 ¿Deseas darle paso? [Pulsa ENTER para PERMITIR / Escribe 'n' para DENEGAR]: ").strip().lower()
    print("="*50 + "\n")

    if decision == 'n':
        print(f"❌ Acceso denegado a: {nombre_real} ({apodo})")
        return render_template_string(HTML_SOLICITUD, error="denegado")

    nombres_registrados.add(apodo)
    nombres_reales_registrados.add(nombre_real)
    guardar_nombres()
    guardar_nombres_reales()

    session["apodo"] = apodo
    session["nombre_real"] = nombre_real
    session["acceso_concedido"] = True

    print(f"✅ Acceso concedido a: {nombre_real} ({apodo})")
    return redirect(url_for("inicio"))

@app.route("/logout", methods=["GET", "POST"])
def logout():
    sid = session.get("id_sesion")
    apodo = session.get("apodo")
    nombre_real = session.get("nombre_real")
    
    if sid and sid in usuarios_activos:
        usuarios_activos.pop(sid)
    
    if apodo or nombre_real:
        total = len(usuarios_activos)
        print(f"\n🔴 [DESCONEXIÓN] Apodo: \"{apodo}\" (Nombre Real: {nombre_real}) se ha desconectado. (Datos conservados) | 👥 Total en línea: {total}\n")
    
    session.pop("sala_autorizada", None)
    session.pop("acceso_concedido", None)
    
    if request.method == "POST":
        return "", 200
    return redirect(url_for("inicio"))

@app.route("/estado_sesion")
def estado_sesion():
    if not session.get("acceso_concedido"):
        return jsonify({"apodo": None, "nombre_real": None}), 403
    return jsonify({
        "apodo": session.get("apodo"),
        "nombre_real": session.get("nombre_real")
    })

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(BASE_DIR, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/validar_pin", methods=["POST"])
def validar_pin():
    if not session.get("acceso_concedido"):
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
            
        session.pop("apodo", None)
        session.pop("nombre_real", None)
        session.pop("acceso_concedido", None)
        session.pop("sala_autorizada", None)
            
        print(f"🧹 [DATOS CAMBIADOS] El usuario actualizó sus datos. Se liberaron los anteriores: '{apodo_viejo}' y '{nombre_real_viejo}'")
        
        generar_nuevo_pin() 
        return jsonify({"valido": True})
    return jsonify({"valido": False})

@app.route("/mensajes")
def obtener_mensajes():
    if not session.get("acceso_concedido"):
        return jsonify([]), 403
    return jsonify(mensajes)

@app.route("/enviar", methods=["POST"])
def enviar():
    if not session.get("acceso_concedydo"): # type: ignore
        pass
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    data = request.get_json()
    nombre = session.get("apodo", "Anónimo")
    
    mensajes.append({"nombre": nombre, "texto": data["texto"], "archivo": None})
    return jsonify({"status": "ok"})

@app.route("/subir", methods=["POST"])
def subir():
    if not session.get("acceso_concedido"):
        return jsonify({"status": "error"}), 403
    nombre = session.get("apodo", "Anónimo")
    file = request.files.get("archivo")
    if file:
        nombre_archivo = file.filename
        ruta = os.path.join(CARPETA_UPLOADS, nombre_archivo)
        file.save(ruta)
        mensajes.append({"nombre": nombre, "texto": None, "archivo": nombre_archivo})
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

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print("\n" + "="*50)
    print(f"🚀 CHAT INICIADO EN LA NUBE")
    print(f"🔑 CONTRASEÑA DE ACCESO A LA SALA: {CLAVE_SALA}")
    print(f"🔑 PIN DE CAMBIO DE APODO: {PIN_DESBLOQUEO}")
    print("="*50 + "\n")
    
    app.run(host="0.0.0.0", port=puerto)