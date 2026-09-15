# Cotizador de Cuidado de Mascotas

Servidor en Flask que permite pedir el cuidado de un perro/gato/otro animal
indicando fecha de inicio y fecha de fin, y calcula el costo total.

## Estructura
```
pet-sitter/
├── app.py              # Servidor Flask + lógica de cálculo
├── requirements.txt    # Dependencias
├── render.yaml          # Configuración para despliegue en Render
└── templates/
    └── index.html       # Formulario web
```

## Cómo funciona
- El usuario elige el tipo de mascota, cuántas mascotas, y el rango de fechas.
- El servidor calcula las noches (fecha_fin - fecha_inicio) y multiplica por
  el precio por noche según el tipo de mascota y la cantidad.
- Los precios se definen en el diccionario `PRECIOS_POR_NOCHE` dentro de `app.py`;
  puedes cambiarlos ahí.

## Probarlo en local
```bash
pip install -r requirements.txt
python app.py
```
Abre http://localhost:5000

## Desplegar en Render
1. Sube esta carpeta a un repositorio de GitHub (o GitLab).
2. Entra a https://render.com → "New +" → "Web Service".
3. Conecta tu repositorio.
4. Render detectará el `render.yaml` automáticamente. Si no, configura a mano:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3
5. Haz clic en "Create Web Service". En unos minutos tendrás una URL pública
   tipo `https://tu-app.onrender.com`.

## Endpoint de la API
`POST /api/cotizar`
```json
{
  "tipo_mascota": "perro_mediano",
  "cantidad": 1,
  "fecha_inicio": "2026-09-20",
  "fecha_fin": "2026-09-25"
}
```
Respuesta:
```json
{
  "ok": true,
  "noches": 5,
  "precio_por_noche": 13,
  "cantidad_mascotas": 1,
  "tipo_mascota": "Perro mediano",
  "costo_total": 65,
  "fecha_inicio": "2026-09-20",
  "fecha_fin": "2026-09-25"
}
```
