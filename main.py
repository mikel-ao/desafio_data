from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import math
import psycopg2
import psycopg2.extras
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Motor de Recomendación — Data Science",
    description="API del motor de recomendación basado en pesos para la app de comercios del País Vasco.",
    version="1.0.0"
)

# ── CONFIGURACIÓN BD ──────────────────────────────────────────────────────────
# Internal URL para Render (sin SSL), External URL para local (con SSL)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recomendador_ds_user:NJBcVxYoa7SrmDVRpCfmIHCCexWLsbDQ@dpg-d8ga02vlk1mc73elmv40-a.frankfurt-postgres.render.com/recomendador_ds"
)

def get_conn():
    """Abre una conexión a PostgreSQL."""
    try:
        # Intento sin SSL (Internal URL dentro de Render)
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        # Fallback con SSL (External URL desde local)
        return psycopg2.connect(DATABASE_URL, sslmode="require")

# ── CATÁLOGO OFICIAL DE TAGS ──────────────────────────────────────────────────

TAGS_OFICIALES = [
    "after-party", "after-work", "cuidarme", "brunch", "pelis",
    "cultura", "deporte", "low-cost", "euskaldun", "arte", "party",
    "gastronomia", "juegos-de-mesa", "mercado", "tendencia",
    "conciertos", "nocturno", "outdoor", "pintxopote", "poteo",
    "rooftop", "talleres", "teatro", "terraceo", "comercio-local",
    "tradicional", "chill", "vermut", "deportes-extremos", "caprichos"
]

TAGS_SET = set(TAGS_OFICIALES)

def tag_a_col(tag: str) -> str:
    return tag.replace("-", "_")

def col_a_tag(col: str) -> str:
    return col.replace("_", "-")

COLUMNAS = [tag_a_col(t) for t in TAGS_OFICIALES]

# ── FUNCIONES DE BD ───────────────────────────────────────────────────────────

def obtener_o_crear_pesos(user_id: int) -> dict:
    """
    Busca los pesos del usuario en PostgreSQL.
    Si no existe, lo inicializa con todos los tags a 0.0 (cold-start).
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM user_weights WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return {col_a_tag(col): float(row[col]) for col in COLUMNAS}
            # Cold-start
            cols_str  = ", ".join(COLUMNAS)
            vals_str  = ", ".join(["0.0"] * len(COLUMNAS))
            cur.execute(
                f"INSERT INTO user_weights (user_id, {cols_str}) VALUES (%s, {vals_str})",
                (user_id,)
            )
            conn.commit()
            return {tag: 0.0 for tag in TAGS_OFICIALES}
    finally:
        conn.close()

def guardar_pesos(user_id: int, pesos: dict):
    """Actualiza los pesos del usuario en PostgreSQL."""
    set_clauses = ", ".join([f"{tag_a_col(tag)} = %s" for tag in TAGS_OFICIALES])
    valores     = [pesos.get(tag, 0.0) for tag in TAGS_OFICIALES]
    valores.append(user_id)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE user_weights SET {set_clauses} WHERE user_id = %s",
                valores
            )
            conn.commit()
    finally:
        conn.close()

def obtener_activities(time_slot: str, municipio: Optional[str] = None) -> list:
    """Consulta actividades filtrando por time_slot y opcionalmente municipio."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if municipio:
                cur.execute("""
                    SELECT id, name, municipio, lat, lng,
                           tag_1, tag_2, tag_3, time_slot, price
                    FROM activities
                    WHERE LOWER(time_slot) = LOWER(%s)
                    AND LOWER(municipio) LIKE LOWER(%s)
                    AND is_active = 1
                """, (time_slot, f"%{municipio}%"))
            else:
                cur.execute("""
                    SELECT id, name, municipio, lat, lng,
                           tag_1, tag_2, tag_3, time_slot, price
                    FROM activities
                    WHERE LOWER(time_slot) = LOWER(%s)
                    AND is_active = 1
                """, (time_slot,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

# ── HELPER: DISTANCIA HAVERSINE ───────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R   = 6371.0
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlng = (lng2 - lng1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── MODELOS DE DATOS ──────────────────────────────────────────────────────────

class RecomendacionesRequest(BaseModel):
    user_id: int
    lat: float
    lng: float
    time_slot: str
    municipio: Optional[str] = None
    top_n: Optional[int] = 5

class ActualizarPesosRequest(BaseModel):
    user_id: int
    activity_tags: List[str]
    score_servicio: int
    score_ambiente: int
    score_calidad_precio: int

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Motor de Recomendación — Data Science"}


@app.post("/recomendaciones")
def post_recomendaciones(req: RecomendacionesRequest):
    """
    Devuelve las top_n actividades más compatibles con el perfil del usuario.
    Filtra por time_slot y distancia máxima 40 km. Ordena por score ponderado.
    """
    weights    = obtener_o_crear_pesos(req.user_id)
    activities = obtener_activities(req.time_slot, req.municipio)

    if not activities:
        return []

    candidatas = []
    for act in activities:
        if act["lat"] is None or act["lng"] is None:
            continue
        distancia = haversine_km(req.lat, req.lng, float(act["lat"]), float(act["lng"]))
        if distancia > 40.0:
            continue

        tags_act = [t for t in [act["tag_1"], act["tag_2"], act["tag_3"]] if t]
        score = (
            sum(weights.get(t, 0.0) for t in tags_act) / len(tags_act)
            if tags_act else 0.0
        )

        candidatas.append({
            "activity_id":  act["id"],
            "name":         act["name"],
            "municipio":    act["municipio"],
            "score":        round(score, 3),
            "distancia_km": round(distancia, 2),
            "tags":         tags_act,
            "price":        float(act["price"]) if act["price"] else 0.0,
        })

    candidatas.sort(key=lambda x: x["score"], reverse=True)
    return candidatas[:req.top_n]


@app.post("/actualizar-pesos")
def post_actualizar_pesos(req: ActualizarPesosRequest):
    """
    El usuario ha dejado una reseña.
    Actualiza los pesos de los tags de la actividad valorada.
    peso_nuevo = peso_actual * 0.9 + val_norm * 0.1
    """
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

    weights   = obtener_o_crear_pesos(req.user_id)
    val_media = (req.score_servicio + req.score_ambiente + req.score_calidad_precio) / 3.0
    val_norm  = (val_media - 1.0) / 4.0

    tags_validos   = [t for t in req.activity_tags if t in TAGS_SET]
    tags_ignorados = [t for t in req.activity_tags if t not in TAGS_SET]

    for tag in tags_validos:
        weights[tag] = round(weights[tag] * 0.9 + val_norm * 0.1, 3)

    guardar_pesos(req.user_id, weights)

    return {
        "ok":             True,
        "weights":        weights,
        "val_norm":       round(val_norm, 3),
        "tags_ignorados": tags_ignorados
    }
