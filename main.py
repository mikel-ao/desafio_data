from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import math
import psycopg2
from psycopg2.extras import Json
import os

app = FastAPI(
    title="Motor de Recomendación — Data Science",
    description="API del motor de recomendación basado en pesos para la app de comercios del País Vasco.",
    version="1.0.0"
)

# ── CONFIGURACIÓN BD SUPABASE ─────────────────────────────────────────────────
# Local: meter las strings directas
# Render: usar variables de entorno (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)

DB_PARAMS = {
    "dbname":   os.environ.get("DB_NAME"),
    "user":     os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host":     os.environ.get("DB_HOST"),
    "port":     int(os.environ.get("DB_PORT"))
}

# ── CATÁLOGO OFICIAL DE TAGS ──────────────────────────────────────────────────
# 30 tags acordados con Marketing y Data Science
# Cualquier tag fuera de esta lista se ignora silenciosamente

TAGS_OFICIALES = [
    "after-party", "after-work", "cuidarme", "brunch", "pelis",
    "cultura", "deporte", "low-cost", "euskaldun", "arte", "party",
    "gastronomia", "juegos-de-mesa", "mercado", "tendencia",
    "conciertos", "nocturno", "outdoor", "pintxopote", "poteo",
    "rooftop", "talleres", "teatro", "terraceo", "comercio-local",
    "tradicional", "chill", "vermut", "deportes-extremos", "caprichos"
]

TAGS_SET = set(TAGS_OFICIALES)  # para lookups O(1)

# ── MODELOS DE DATOS ──────────────────────────────────────────────────────────

class ActivityInput(BaseModel):
    id: int
    name: str
    activity_category_id_1: str
    activity_category_id_2: Optional[str] = None
    activity_category_id_3: Optional[str] = None
    time_slot: str
    lat: float
    lng: float

class RecomendacionesRequest(BaseModel):
    user_id: int
    lat: float
    lng: float
    time_slot: str
    activities: List[ActivityInput]
    top_n: Optional[int] = 5

class ActualizarTagsRequest(BaseModel):
    user_id: int
    tags: List[str]  # hasta 9 tags del perfil del usuario

class ActualizarPesosRequest(BaseModel):
    user_id: int
    activity_tags: List[str]       # tags de la actividad valorada
    score_servicio: int            # 1-5
    score_ambiente: int            # 1-5
    score_calidad_precio: int      # 1-5

# ── FUNCIONES DE BD ───────────────────────────────────────────────────────────

def obtener_o_crear_pesos(user_id: int) -> dict:
    """
    Busca los pesos del usuario en Supabase.
    Si no existe, lo inicializa con todos los tags a 0.0 (cold-start).
    """
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    try:
        cur.execute("SELECT weights FROM user_weights WHERE user_id = %s;", (user_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        # Cold-start: usuario nuevo → todos los pesos a 0.0
        pesos_iniciales = {tag: 0.0 for tag in TAGS_OFICIALES}
        cur.execute(
            "INSERT INTO user_weights (user_id, weights) VALUES (%s, %s);",
            (user_id, Json(pesos_iniciales))
        )
        conn.commit()
        return pesos_iniciales
    finally:
        cur.close()
        conn.close()

def guardar_pesos(user_id: int, pesos: dict):
    """
    Guarda o sobreescribe los pesos del usuario en Supabase.
    Usa UPSERT para manejar tanto inserts como updates.
    """
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_weights (user_id, weights, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                weights    = EXCLUDED.weights,
                updated_at = CURRENT_TIMESTAMP;
        """, (user_id, Json(pesos)))
        conn.commit()
    finally:
        cur.close()
        conn.close()

# ── HELPER: DISTANCIA HAVERSINE ───────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en km entre dos coordenadas usando la fórmula de Haversine."""
    R = 6371.0
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlng = (lng2 - lng1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    """Health check para Render y monitorización."""
    return {"status": "ok", "service": "Motor de Recomendación — Data Science"}


@app.post("/recomendaciones")
def post_recomendaciones(req: RecomendacionesRequest):
    """
    Devuelve las top_n actividades más compatibles con el perfil del usuario.

    Flujo:
      1. Obtener pesos del usuario desde Supabase
      2. Filtrar actividades por time_slot
      3. Filtrar actividades a menos de 40 km (Haversine)
      4. Calcular score ponderado por coincidencia de tags
      5. Ordenar por score DESC y devolver top_n
    """
    weights = obtener_o_crear_pesos(req.user_id)
    candidatas = []

    for act in req.activities:

        # Filtro 1: time_slot debe coincidir exactamente
        if act.time_slot.lower() != req.time_slot.lower():
            continue

        # Filtro 2: distancia máxima 40 km
        distancia = haversine_km(req.lat, req.lng, act.lat, act.lng)
        if distancia > 40.0:
            continue

        # Score: media de los pesos del usuario para los tags de la actividad
        tags_act = [
            t for t in [
                act.activity_category_id_1,
                act.activity_category_id_2,
                act.activity_category_id_3
            ] if t is not None
        ]
        score = (
            sum(weights.get(t, 0.0) for t in tags_act) / len(tags_act)
            if tags_act else 0.0
        )

        candidatas.append({
            "activity_id":  act.id,
            "name":         act.name,
            "score":        round(score, 3),
            "distancia_km": round(distancia, 2),
        })

    candidatas.sort(key=lambda x: x["score"], reverse=True)
    return candidatas[:req.top_n]


@app.post("/actualizar-tags")
def post_actualizar_tags(req: ActualizarTagsRequest):
    """
    El usuario ha modificado sus tags en el perfil.
    Sube +0.1 a cada tag seleccionado (tope 1.0).
    Ignora tags que no están en el catálogo oficial.
    """
    weights = obtener_o_crear_pesos(req.user_id)

    tags_validos = [t for t in req.tags if t in TAGS_SET]
    tags_ignorados = [t for t in req.tags if t not in TAGS_SET]

    for tag in tags_validos:
        weights[tag] = round(min(weights[tag] + 0.1, 1.0), 3)

    guardar_pesos(req.user_id, weights)

    return {
        "ok":              True,
        "weights":         weights,
        "tags_ignorados":  tags_ignorados  # útil para que Full Stack detecte errores
    }


@app.post("/actualizar-pesos")
def post_actualizar_pesos(req: ActualizarPesosRequest):
    """
    El usuario ha dejado una reseña.
    Actualiza los pesos de los tags de la actividad valorada.

    Fórmula:
      val_media = (score_servicio + score_ambiente + score_calidad_precio) / 3
      val_norm  = (val_media - 1) / 4    →  escala 1-5 a 0.0-1.0
      peso_nuevo = peso_actual * 0.9 + val_norm * 0.1

    Ignora tags que no están en el catálogo oficial.
    """
    # Validar rangos de puntuaciones
    for campo, valor in [
        ("score_servicio",       req.score_servicio),
        ("score_ambiente",       req.score_ambiente),
        ("score_calidad_precio", req.score_calidad_precio),
    ]:
        if not 1 <= valor <= 5:
            raise HTTPException(
                status_code=422,
                detail=f"{campo} debe ser un entero entre 1 y 5, recibido: {valor}"
            )

    weights = obtener_o_crear_pesos(req.user_id)

    val_media = (req.score_servicio + req.score_ambiente + req.score_calidad_precio) / 3.0
    val_norm  = (val_media - 1.0) / 4.0

    tags_validos   = [t for t in req.activity_tags if t in TAGS_SET]
    tags_ignorados = [t for t in req.activity_tags if t not in TAGS_SET]

    for tag in tags_validos:
        weights[tag] = round(weights[tag] * 0.9 + val_norm * 0.1, 3)

    guardar_pesos(req.user_id, weights)

    return {
        "ok":              True,
        "weights":         weights,
        "val_norm":        round(val_norm, 3),   # útil para depuración
        "tags_ignorados":  tags_ignorados
    }