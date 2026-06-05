"""
normalizar_tags.py — Normaliza los tags de activities en SQLite
usando la tabla de etiquetas oficial del equipo.
Ejecutar DESPUÉS de load_data.py
"""
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "weights.db")

# Mapeo de tags del CSV → tags oficiales del motor
# Basado en TABLA_DE_ETIQUETAS_-_NAMING.xlsx
MAPEO_TAGS = {
    # Tags de actividades
    "after":           "after-party",
    "afterwork":       "after-work",
    "bienestar":       "cuidarme",
    "cine":            "pelis",
    "concierto":       "conciertos",
    "cultura":         "cultura",
    "cultureta":       "cultura",
    "deporte":         "deporte",
    "economico":       "low-cost",
    "euskera":         "euskaldun",
    "exposicion":      "arte",
    "fiesta":          "party",
    "gastronomia":     "gastronomia",
    "juegos-de-mesa":  "juegos-de-mesa",
    "mercado":         "mercado",
    "moderno":         "tendencia",
    "musica-en-vivo":  "conciertos",
    "musica_en_vivo":  "conciertos",
    "nocturno":        "nocturno",
    "noche":           "nocturno",
    "outdoor":         "outdoor",
    "pintxopote":      "pintxopote",
    "poteo":           "poteo",
    "rooftop":         "rooftop",
    "taller":          "talleres",
    "talleres":        "talleres",
    "teatro":          "teatro",
    "terraceo":        "terraceo",
    "tienda-local":    "comercio-local",
    "tienda_local":    "comercio-local",
    "comercio_local":  "comercio-local",
    "tradicional":     "tradicional",
    "tranquilo":       "chill",
    "vermut":          "vermut",
    # Valores que se eliminan
    "indoor":          None,
    "animado":         None,
    "moda":            None,
}

TAGS_OFICIALES = {
    "after-party", "after-work", "cuidarme", "brunch", "pelis",
    "cultura", "deporte", "low-cost", "euskaldun", "arte", "party",
    "gastronomia", "juegos-de-mesa", "mercado", "tendencia",
    "conciertos", "nocturno", "outdoor", "pintxopote", "poteo",
    "rooftop", "talleres", "teatro", "terraceo", "comercio-local",
    "tradicional", "chill", "vermut", "deportes-extremos", "caprichos"
}

def normalizar(tag):
    """Normaliza un tag al catálogo oficial."""
    if not tag:
        return None
    tag_lower = tag.strip().lower()
    # Ya es oficial
    if tag_lower in TAGS_OFICIALES:
        return tag_lower
    # Está en el mapeo
    if tag_lower in MAPEO_TAGS:
        return MAPEO_TAGS[tag_lower]
    # No reconocido → eliminar
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, tag_1, tag_2, tag_3 FROM activities").fetchall()
    print(f"Normalizando {len(rows)} actividades...")

    actualizadas = 0
    eliminados = {"tag_1": 0, "tag_2": 0, "tag_3": 0}

    for row in rows:
        t1 = normalizar(row["tag_1"])
        t2 = normalizar(row["tag_2"])
        t3 = normalizar(row["tag_3"])

        # Contar eliminados
        if row["tag_1"] and not t1: eliminados["tag_1"] += 1
        if row["tag_2"] and not t2: eliminados["tag_2"] += 1
        if row["tag_3"] and not t3: eliminados["tag_3"] += 1

        conn.execute(
            "UPDATE activities SET tag_1=?, tag_2=?, tag_3=? WHERE id=?",
            (t1, t2, t3, row["id"])
        )
        actualizadas += 1

    conn.commit()

    print(f"✓ {actualizadas} actividades normalizadas")
    print(f"  Tags eliminados por no tener equivalente: {eliminados}")

    print(f"\n─── Distribución de tags tras normalización ───")
    for col in ["tag_1", "tag_2", "tag_3"]:
        print(f"\n  {col}:")
        rows_dist = conn.execute(f"""
            SELECT {col}, COUNT(*) as n FROM activities
            WHERE {col} IS NOT NULL
            GROUP BY {col} ORDER BY n DESC LIMIT 10
        """).fetchall()
        for r in rows_dist:
            print(f"    {r[0]:<20} {r[1]}")

    conn.close()
    print("\n✅ Normalización completada")

if __name__ == "__main__":
    main()
