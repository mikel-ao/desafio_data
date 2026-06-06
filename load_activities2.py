"""
load_activities2.py — Carga actividades adicionales en PostgreSQL de Render
Normaliza tags con espacios/mayúsculas al catálogo oficial.
Ejecutar: python load_activities2.py
"""
import pandas as pd
import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recomendador_ds_user:NJBcVxYoa7SrmDVRpCfmIHCCexWLsbDQ@dpg-d8ga02vlk1mc73elmv40-a.frankfurt-postgres.render.com/recomendador_ds"
)
CSV_FILE = os.environ.get("CSV_FILE", "actividades_kulturklik_clean3.csv")

MAPEO_TAGS = {
    "after party":       "after-party",
    "after work":        "after-work",
    "al aire libre":     "outdoor",
    "arte":              "arte",
    "brunch":            "brunch",
    "comer bien":        "gastronomia",
    "comercio local":    "comercio-local",
    "cuidarme":          "cuidarme",
    "cultureta":         "cultura",
    "deporte":           "deporte",
    "euskaldun":         "euskaldun",
    "juegos de mesa":    "juegos-de-mesa",
    "low-cost":          "low-cost",
    "me lo merezco":     "caprichos",
    "mercado":           "mercado",
    "música en vivo":    "conciertos",
    "musica en vivo":    "conciertos",
    "party":             "party",
    "pelis":             "pelis",
    "pintxopote":        "pintxopote",
    "poteo":             "poteo",
    "putivuelta":        "putivuelta",
    "rooftop":           "rooftop",
    "talleres":          "talleres",
    "teatro":            "teatro",
    "terraceo":          "terraceo",
    "a la última":       "tendencia",
    "a la ultima":       "tendencia",
    "animal nocturno":   "nocturno",
    "de toda la vida":   "tradicional",
    "de chill":          "chill",
    "grandes emociones": "deportes-extremos",
}

TAGS_OFICIALES = {
    "after-party","after-work","cuidarme","brunch","pelis",
    "cultura","deporte","low-cost","euskaldun","arte","party",
    "gastronomia","juegos-de-mesa","mercado","tendencia",
    "conciertos","nocturno","outdoor","pintxopote","poteo",
    "rooftop","talleres","teatro","terraceo","comercio-local",
    "tradicional","chill","putivuelta","deportes-extremos","caprichos"
}

FRANJA_MAP = {"Mañana": "manana", "Tarde": "tarde", "Noche": "noche"}

def normalizar(tag):
    if not tag or str(tag).strip().lower() in ['nan', 'none', '']:
        return None
    t = str(tag).strip().lower()
    if t in TAGS_OFICIALES:
        return t
    return MAPEO_TAGS.get(t, "cultura")

def get_conn():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        return psycopg2.connect(DATABASE_URL, sslmode="require")

def main():
    df = pd.read_csv(CSV_FILE)
    df = df.where(pd.notnull(df), None)
    print(f"CSV cargado: {len(df)} filas")

    conn = get_conn()
    cur  = conn.cursor()

    # Ver cuántas hay antes
    cur.execute("SELECT COUNT(*) FROM activities")
    antes = cur.fetchone()[0]
    print(f"Activities antes: {antes}")

    rows = []
    for _, r in df.iterrows():
        franja    = FRANJA_MAP.get(r.get("franja") or "Tarde", "tarde")
        price     = float(r.get("precio_min") or 0.0)
        t1        = normalizar(r.get("tag1")) or "cultura"
        t2        = normalizar(r.get("tag2"))
        t3        = normalizar(r.get("tag3"))
        # Deduplicar tags
        tags = list(dict.fromkeys([x for x in [t1, t2, t3] if x]))
        while len(tags) < 3:
            tags.append(None)
        rows.append((
            r.get("nombre_evento"), r.get("municipio"),
            r.get("lat"), r.get("lng"),
            tags[0], tags[1], tags[2],
            franja, price,
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

    cur.execute("SELECT COUNT(*) FROM activities")
    despues = cur.fetchone()[0]
    print(f"Activities después: {despues} (+{despues - antes} nuevas)")

    print(f"\n─── Tag_1 más frecuentes ───────────────")
    cur.execute("""
        SELECT tag_1, COUNT(*) as n FROM activities
        WHERE tag_1 IS NOT NULL
        GROUP BY tag_1 ORDER BY n DESC LIMIT 10
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<20} {r[1]}")

    cur.close()
    conn.close()
    print("\n✅ Carga completada")

if __name__ == "__main__":
    main()
