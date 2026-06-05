"""
load_users.py — Carga usuarios con pesos en PostgreSQL de Render
================================================================
Ejecutar: python load_users.py
"""

import pandas as pd
import psycopg2
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recomendador_ds_user:NJBcVxYoa7SrmDVRpCfmIHCCexWLsbDQ@dpg-d8ga02vlk1mc73elmv40-a.frankfurt-postgres.render.com/recomendador_ds"
)

CSV_USERS = os.environ.get("CSV_USERS", "user_weights.csv")

# Mapeo columnas CSV → columnas oficiales en BD
MAPEO_COLUMNAS = {
    "after_party":      "after_party",
    "after_work":       "after_work",
    "cuidarme":         "cuidarme",
    "brunch":           "brunch",
    "pelis":            "pelis",
    "cultureta":        "cultura",
    "deporte":          "deporte",
    "low_cost":         "low_cost",
    "euskaldun":        "euskaldun",
    "arte":             "arte",
    "party":            "party",
    "comer_bien":       "gastronomia",
    "juegos_de_mesa":   "juegos_de_mesa",
    "mercado":          "mercado",
    "a_la_ultima":      "tendencia",
    "musica_en_vivo":   "conciertos",
    "animal_nocturno":  "nocturno",
    "al_aire_libre":    "outdoor",
    "pintxopote":       "pintxopote",
    "poteo":            "poteo",
    "rooftop":          "rooftop",
    "talleres":         "talleres",
    "teatro":           "teatro",
    "terraceo":         "terraceo",
    "comercio_local":   "comercio_local",
    "de_toda_la_vida":  "tradicional",
    "de_chill":         "chill",
    "putivuelta":       "putivuelta",
    "grandes_emociones":"deportes_extremos",
    "me_lo_merezco":    "caprichos",
}

COLUMNAS_BD = [
    "after_party", "after_work", "cuidarme", "brunch", "pelis",
    "cultura", "deporte", "low_cost", "euskaldun", "arte", "party",
    "gastronomia", "juegos_de_mesa", "mercado", "tendencia",
    "conciertos", "nocturno", "outdoor", "pintxopote", "poteo",
    "rooftop", "talleres", "teatro", "terraceo", "comercio_local",
    "tradicional", "chill", "putivuelta", "deportes_extremos", "caprichos"
]

def get_conn():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        return psycopg2.connect(DATABASE_URL, sslmode="require")

def load_users():
    df = pd.read_csv(CSV_USERS)
    df = df.where(pd.notnull(df), 0.0)

    conn = get_conn()
    cur  = conn.cursor()

    # Verificar cuántos ya existen
    cur.execute("SELECT COUNT(*) FROM user_weights")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"  user_weights ya tiene {existing} filas — saltando")
        cur.close()
        conn.close()
        return

    cols_str  = ", ".join(COLUMNAS_BD)
    vals_str  = ", ".join(["%s"] * len(COLUMNAS_BD))

    rows = []
    for _, r in df.iterrows():
        valores = [float(r.get(csv_col, 0.0)) for csv_col, bd_col in MAPEO_COLUMNAS.items()]
        rows.append([int(r["user_id"])] + valores)

    cur.executemany(
        f"INSERT INTO user_weights (user_id, {cols_str}) VALUES (%s, {vals_str}) ON CONFLICT (user_id) DO NOTHING",
        rows
    )
    conn.commit()
    print(f"✓ {len(rows)} usuarios cargados")

    # Verificar
    cur.execute("SELECT COUNT(*) FROM user_weights")
    print(f"  Total en BD: {cur.fetchone()[0]} usuarios")

    cur.execute("SELECT user_id, cultura, teatro, party, putivuelta FROM user_weights LIMIT 3")
    print(f"\n─── Muestra ─────────────────────────")
    for r in cur.fetchall():
        print(f"  user_id={r[0]}  cultura={r[1]}  teatro={r[2]}  party={r[3]}  putivuelta={r[4]}")

    cur.close()
    conn.close()
    print("\n✅ Carga completada")

if __name__ == "__main__":
    print(f"\nConectando a Render PostgreSQL...")
    load_users()
