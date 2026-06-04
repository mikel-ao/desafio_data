from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import math
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Motor de Recomendación — Data Science",
    description="API del motor de recomendación basado en pesos para la app de comercios del País Vasco.",
    version="1.0.0"
)

# ── CONFIGURACIÓN BD SQLITE ───────────────────────────────────────────────────

DB_PATH = os.environ.get("DB_PATH", "weights.db")

# ── CATÁLOGO OFICIAL DE TAGS ──────────────────────────────────────────────────
# Los guiones se convierten a guiones bajos para los nombres de columna SQL

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
    """Convierte un tag a nombre de columna SQL. Ej: after-party → after_party"""
    return tag.replace("-", "_")

def col_a_tag(col: str) -> str:
    """Convierte un nombre de columna SQL a tag. Ej: after_party → after-party"""
    return col.replace("_", "-")

COLUMNAS = [tag_a_col(t) for t in TAGS_OFICIALES]

# ── INICIALIZACIÓN DE LA BD ───────────────────────────────────────────────────

def init_db():
    """Crea la tabla user_weights si no existe."""
    cols_sql = ",\n    ".join([f"{col} REAL DEFAULT 0.0" for col in COLUMNAS])
    sql = f"""
        CREATE TABLE IF NOT EXISTS user_weights (
            user_id INTEGER PRIMARY KEY,
            {cols_sql}
        );
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(sql)
    conn.commit()
    conn.close()
    logger.info(f"BD inicializada en {DB_PATH}")

init_db()

# ── FUNCIONES DE BD ───────────────────────────────────────────────────────────

def obtener_o_crear_pesos(user_id: int) -> dict:
    """
    Busca los pesos del usuario en SQLite.
    Si no existe, lo inicializa con todos los tags a 0.0 (cold-start).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM user_weights WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row:
            # Convertir columnas SQL de vuelta a tags con guiones
            return {col_a_tag(col): row[col] for col in COLUMNAS}

        # Cold-start: usuario nuevo → INSERT con todos los pesos a 0.0
        cols_str = ", ".join(COLUMNAS)
        vals_str = ", ".join(["0.0"] * len(COLUMNAS))
        conn.execute(
            f"INSERT INTO user_weights (user_id, {cols_str}) VALUES (?, {vals_str})",
            (user_id,)
        )
        conn.commit()
        return {tag: 0.0 for tag in TAGS_OFICIALES}
    finally:
        conn.close()

def guardar_pesos(user_id: int, pesos: dict):
    """Actualiza los pesos del usuario en SQLite."""
    set_clauses = ", ".join([f"{tag_a_col(tag)} = ?" for tag in TAGS_OFICIALES])
    valores = [pesos.get(tag, 0.0) for tag in TAGS_OFICIALES]
    valores.append(user_id)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"UPDATE user_weights SET {set_clauses} WHERE user_id = ?",
            valores
        )
        conn.commit()
    finally:
        conn.close()

# ── HELPER: DISTANCIA HAVERSINE ───────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en km entre dos coordenadas."""
    R = 6371.0
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlng = (lng2 - lng1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

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

class ActualizarPesosRequest(BaseModel):
    user_id: int
    activity_tags: List[str]
    score_servicio: int
    score_ambiente: int
    score_calidad_precio: int

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    """Health check."""
    return {"status": "ok", "service": "Motor de Recomendación — Data Science"}


@app.post("/recomendaciones")
def post_recomendaciones(req: RecomendacionesRequest):
    """
    Devuelve las top_n actividades más compatibles con el perfil del usuario.

    Flujo:
      1. Obtener pesos del usuario desde SQLite
      2. Filtrar actividades por time_slot
      3. Filtrar actividades a menos de 40 km (Haversine)
      4. Calcular score ponderado por coincidencia de tags
      5. Ordenar por score DESC y devolver top_n
    """
    weights = obtener_o_crear_pesos(req.user_id)
    candidatas = []

    for act in req.activities:
        # Filtro 1: time_slot
        if act.time_slot.lower() != req.time_slot.lower():
            continue

        # Filtro 2: distancia máxima 40 km
        distancia = haversine_km(req.lat, req.lng, act.lat, act.lng)
        if distancia > 40.0:
            continue

        # Score: media de los pesos para los tags de la actividad
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


@app.post("/actualizar-pesos")
def post_actualizar_pesos(req: ActualizarPesosRequest):
    """
    El usuario ha dejado una reseña.
    Actualiza los pesos de los tags de la actividad valorada.

    Fórmula:
      val_media = (score_servicio + score_ambiente + score_calidad_precio) / 3
      val_norm  = (val_media - 1) / 4    →  escala 1-5 a 0.0-1.0
      peso_nuevo = peso_actual * 0.9 + val_norm * 0.1
    """
    # Validar rangos
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
        "ok":             True,
        "weights":        weights,
        "val_norm":       round(val_norm, 3),
        "tags_ignorados": tags_ignorados
    }
