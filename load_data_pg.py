"""
load_data_pg.py — Cargar actividades y comercios en PostgreSQL de Render
========================================================================
Ejecutar: python load_data_pg.py
"""

import pandas as pd
import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recomendador_ds_user:NJBcVxYoa7SrmDVRpCfmIHCCexWLsbDQ@dpg-d8ga02vlk1mc73elmv40-a.frankfurt-postgres.render.com/recomendador_ds"
)

CSV_REST = os.environ.get("CSV_REST", "restaurantes_clean2.csv")
CSV_ACTS = os.environ.get("CSV_ACTS", "actividades_kulturklik_clean.csv")

# Mapeo de tags al catálogo oficial
MAPEO_TAGS = {
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
    "animado":         "party",
    "indoor":          None,
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
    if not tag:
        return None
    tag_lower = str(tag).strip().lower()
    if tag_lower in TAGS_OFICIALES:
        return tag_lower
    if tag_lower in MAPEO_TAGS:
        return MAPEO_TAGS[tag_lower]
    return "cultura"  # fallback para Kulturklik

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# ── CARGAR ACTIVITIES ─────────────────────────────────────────────────────────

def load_activities(conn):
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM activities")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  activities ya tiene {count} filas — saltando")
        cur.close()
        return

    df = pd.read_csv(CSV_ACTS)
    df = df.where(pd.notnull(df), None)

    FRANJA_MAP = {"Mañana": "manana", "Tarde": "tarde", "Noche": "noche"}

    rows = []
    for _, r in df.iterrows():
        franja   = FRANJA_MAP.get(r.get("franja") or "Tarde", "tarde")
        price    = float(r.get("precio_min") or 0.0)
        t1       = normalizar(r.get("tag1")) or "cultura"
        t2       = normalizar(r.get("tag2"))
        t3       = normalizar(r.get("tag3"))
        rows.append((
            r.get("nombre_evento"), r.get("municipio"),
            r.get("lat"), r.get("lng"),
            t1, t2, t3, franja, price,
            r.get("fecha_inicio"), r.get("fecha_fin"), r.get("horario"),
            1, 0
        ))

    cur.executemany("""
        INSERT INTO activities
          (name, municipio, lat, lng, tag_1, tag_2, tag_3,
           time_slot, price, fecha_inicio, fecha_fin, horario, is_active, is_indoor)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, rows)
    conn.commit()
    print(f"✓ {len(rows)} actividades cargadas")
    cur.close()

# ── CARGAR BUSINESSES ─────────────────────────────────────────────────────────

def load_businesses(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM businesses")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  businesses ya tiene {count} filas — saltando")
        cur.close()
        return

    df = pd.read_csv(CSV_REST)
    df = df.where(pd.notnull(df), None)

    rows = []
    for _, r in df.iterrows():
        rows.append((
            r.get("Nombre"), r.get("Localidad"),
            r.get("LATWGS84"), r.get("LONWGS84"),
            r.get("Tipo de Restauración"), r.get("Teléfono"),
            r.get("Dirección"), r.get("Email"), r.get("WEB"),
            r.get("tag1"), r.get("tag2"), r.get("tag3"),
        ))

    cur.executemany("""
        INSERT INTO businesses
          (name, municipio, lat, lng, tipo, telefono, direccion, email, web,
           tag_1, tag_2, tag_3)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, rows)
    conn.commit()
    print(f"✓ {len(rows)} comercios cargados")
    cur.close()

# ── VERIFICAR ─────────────────────────────────────────────────────────────────

def verificar(conn):
    cur = conn.cursor()
    print(f"\n─── Resumen ─────────────────────────────")
    for tabla in ["activities", "businesses", "user_weights"]:
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        n = cur.fetchone()[0]
        print(f"  {tabla:<25} {n:>6} filas")

    print(f"\n─── Tag_1 más frecuentes en activities ──")
    cur.execute("""
        SELECT tag_1, COUNT(*) as n FROM activities
        WHERE tag_1 IS NOT NULL
        GROUP BY tag_1 ORDER BY n DESC LIMIT 10
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<20} {r[1]}")
    cur.close()

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nConectando a Render PostgreSQL...")
    conn = get_conn()
    try:
        load_activities(conn)
        load_businesses(conn)
        verificar(conn)
        print("\n✅ Carga completada\n")
    finally:
        conn.close()
