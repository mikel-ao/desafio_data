"""
seed.py — Poblar la BD SQLite con actividades y usuarios inventados
===================================================================
Estructura de activities alineada con la BD de Full Stack.
Campos imprescindibles para el motor (tag_1/2/3, lat, lng, time_slot)
se mantienen aunque Full Stack no los tenga.

Ejecutar: python seed.py
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DB_PATH", "weights.db")

TAGS_OFICIALES = [
    "after-party", "after-work", "cuidarme", "brunch", "pelis",
    "cultura", "deporte", "low-cost", "euskaldun", "arte", "party",
    "gastronomia", "juegos-de-mesa", "mercado", "tendencia",
    "conciertos", "nocturno", "outdoor", "pintxopote", "poteo",
    "rooftop", "talleres", "teatro", "terraceo", "comercio-local",
    "tradicional", "chill", "vermut", "deportes-extremos", "caprichos"
]

def tag_a_col(tag): return tag.replace("-", "_")

# ── CATEGORÍAS (activity_categories de Full Stack) ────────────────────────────
# id, name
CATEGORIAS = [
    (1,  "Gastronomia"),
    (2,  "Cultura"),
    (3,  "Ocio Nocturno"),
    (4,  "Deporte"),
    (5,  "Bienestar"),
    (6,  "Comercio Local"),
    (7,  "Naturaleza"),
    (8,  "Musica"),
]

# ── ACTIVIDADES ───────────────────────────────────────────────────────────────
# name, municipio, lat, lng,
# tag_1, tag_2, tag_3,        ← imprescindibles para el motor
# time_slot,                  ← imprescindible para el motor
# activity_category_id,       ← igual que Full Stack
# price (numeric),            ← igual que Full Stack
# is_indoor, is_active, available_slots, age_range

ACTIVIDADES = [
    # BILBAO
    ("Noche de Jazz en Kafe Antzokia",      "Bilbao",    43.2587, -2.9233, "conciertos",     "euskaldun",      "nocturno",        "noche",  8,  12.00, False, True, 80,  "18+"),
    ("Pintxopote de los jueves en Ledesma", "Bilbao",    43.2570, -2.9220, "pintxopote",     "poteo",          "low-cost",        "tarde",  1,   8.00, False, True, 200, "18+"),
    ("Vermut en la Ría",                    "Bilbao",    43.2560, -2.9340, "vermut",         "terraceo",       "chill",           "manana", 1,   6.00, False, True, 50,  "todos"),
    ("Exposición Guggenheim Bilbao",        "Bilbao",    43.2688, -2.9341, "arte",           "cultura",        None,              "tarde",  2,  14.00, True,  True, 300, "todos"),
    ("Taller de cerámica vasca",            "Bilbao",    43.2600, -2.9280, "talleres",       "cultura",        "euskaldun",       "tarde",  2,  25.00, True,  True, 15,  "todos"),
    ("Sesión DJ en Fever Club",             "Bilbao",    43.2630, -2.9350, "party",          "nocturno",       "after-party",     "noche",  3,  10.00, True,  True, 300, "18+"),
    ("Brunch en el Ensanche",               "Bilbao",    43.2650, -2.9400, "brunch",         "chill",          "terraceo",        "manana", 1,  18.00, False, True, 40,  "todos"),
    ("Ruta de pintxos Casco Viejo",         "Bilbao",    43.2560, -2.9230, "gastronomia",    "poteo",          "tradicional",     "tarde",  1,  15.00, False, True, 20,  "todos"),
    ("Concierto de rock en Bilborock",      "Bilbao",    43.2543, -2.9218, "conciertos",     "party",          "nocturno",        "noche",  8,  18.00, True,  True, 200, "18+"),
    ("Yoga matutino en Doña Casilda",       "Bilbao",    43.2662, -2.9441, "deporte",        "cuidarme",       "outdoor",         "manana", 4,   8.00, False, True, 30,  "todos"),
    ("Escape room en el Casco Viejo",       "Bilbao",    43.2558, -2.9235, "juegos-de-mesa", "nocturno",       None,              "tarde",  3,  22.00, True,  True, 24,  "todos"),
    ("Mercado de San Antón",                "Bilbao",    43.2567, -2.9221, "mercado",        "gastronomia",    "tradicional",     "manana", 6,   0.00, False, True, 500, "todos"),
    ("After work en rooftop Indautxu",      "Bilbao",    43.2690, -2.9470, "after-work",     "rooftop",        "terraceo",        "tarde",  3,  12.00, False, True, 60,  "18+"),
    ("Bertso saio en Rekalde",              "Bilbao",    43.2510, -2.9340, "euskaldun",      "cultura",        "tradicional",     "tarde",  2,   5.00, False, True, 100, "todos"),
    ("Cine de verano en Abandoibarra",      "Bilbao",    43.2680, -2.9360, "pelis",          "outdoor",        "chill",           "noche",  2,   6.00, False, True, 150, "todos"),

    # DONOSTIA
    ("Pintxos en la Parte Vieja",           "Donostia",  43.3241, -1.9859, "gastronomia",    "pintxopote",     "tradicional",     "tarde",  1,  10.00, False, True, 200, "todos"),
    ("Concierto folk en Donostia",          "Donostia",  43.3220, -1.9840, "conciertos",     "euskaldun",      "tradicional",     "noche",  8,  15.00, True,  True, 250, "todos"),
    ("Surf en la playa de Zurriola",        "Donostia",  43.3270, -1.9730, "deporte",        "outdoor",        "deportes-extremos","manana",4,  35.00, False, True, 12,  "16+"),
    ("Exposición en el Museo San Telmo",    "Donostia",  43.3238, -1.9861, "arte",           "cultura",        "euskaldun",       "tarde",  2,   8.00, True,  True, 200, "todos"),
    ("Cata de txakoli en Getaria",          "Donostia",  43.2997, -2.2029, "gastronomia",    "tradicional",    "euskaldun",       "tarde",  1,  20.00, False, True, 20,  "18+"),
    ("Terraceo en el Boulevard",            "Donostia",  43.3213, -1.9842, "terraceo",       "chill",          "vermut",          "tarde",  1,   8.00, False, True, 80,  "todos"),
    ("Ruta de sidrerías Gipuzkoa",          "Donostia",  43.3100, -2.0200, "gastronomia",    "tradicional",    "poteo",           "tarde",  1,  25.00, False, True, 15,  "18+"),
    ("Taller de cocina vasca",              "Donostia",  43.3215, -1.9838, "talleres",       "gastronomia",    "euskaldun",       "tarde",  1,  45.00, True,  True, 12,  "todos"),
    ("Festival de jazz Jazzaldia",          "Donostia",  43.3190, -1.9820, "conciertos",     "party",          "nocturno",        "noche",  8,  30.00, False, True, 5000,"todos"),
    ("Mercado de la Bretxa",                "Donostia",  43.3235, -1.9858, "mercado",        "gastronomia",    "comercio-local",  "manana", 6,   0.00, False, True, 400, "todos"),

    # VITORIA-GASTEIZ
    ("Vermut en el Casco Medieval",         "Vitoria",   42.8467, -2.6726, "vermut",         "tradicional",    "euskaldun",       "manana", 1,   5.00, False, True, 60,  "todos"),
    ("Exposición en Artium",                "Vitoria",   42.8497, -2.6748, "arte",           "cultura",        None,              "tarde",  2,   6.00, True,  True, 200, "todos"),
    ("After work en la Florida",            "Vitoria",   42.8510, -2.6780, "after-work",     "terraceo",       "chill",           "tarde",  3,   8.00, False, True, 80,  "18+"),
    ("Concierto en la Plaza de la Virgen",  "Vitoria",   42.8466, -2.6722, "conciertos",     "euskaldun",      "outdoor",         "noche",  8,   0.00, False, True, 1000,"todos"),
    ("Ruta de bares Calle Dato",            "Vitoria",   42.8495, -2.6750, "poteo",          "party",          "nocturno",        "noche",  3,  10.00, False, True, 200, "18+"),
    ("Mercado medieval de Vitoria",         "Vitoria",   42.8470, -2.6730, "mercado",        "tradicional",    "comercio-local",  "manana", 6,   0.00, False, True, 800, "todos"),
    ("Taller de cerámica en Artium",        "Vitoria",   42.8497, -2.6748, "talleres",       "arte",           "cultura",         "tarde",  2,  20.00, True,  True, 15,  "todos"),
    ("Senderismo Llanada Alavesa",          "Vitoria",   42.8200, -2.6500, "outdoor",        "deporte",        "cuidarme",        "manana", 7,   0.00, False, True, 30,  "todos"),

    # MUNICIPIOS
    ("Regatas en Hondarribia",              "Hondarribia",43.3680,-1.7960, "deporte",        "outdoor",        "euskaldun",       "manana", 4,  15.00, False, True, 50,  "todos"),
    ("Cata de vinos Rioja Alavesa",         "Laguardia",  42.5600,-2.5900, "gastronomia",    "tradicional",    "caprichos",       "tarde",  1,  35.00, False, True, 20,  "18+"),
    ("Fiestas de Gernika",                  "Gernika",    43.3172,-2.6790, "party",          "euskaldun",      "tradicional",     "noche",  3,   0.00, False, True, 2000,"todos"),
    ("Surf extremo en Mundaka",             "Mundaka",    43.4080,-2.6950, "deportes-extremos","outdoor",       "deporte",         "manana", 4,  40.00, False, True, 10,  "16+"),
]

# ── PERFILES DE USUARIOS ──────────────────────────────────────────────────────

ARQUETIPOS = {
    "festero":    {"altos": ["party","nocturno","after-party","poteo","conciertos"],    "medios": ["pintxopote","rooftop","after-work"]},
    "cultural":   {"altos": ["cultura","arte","euskaldun","teatro","conciertos"],       "medios": ["talleres","tradicional","pelis"]},
    "gastronomo": {"altos": ["gastronomia","pintxopote","vermut","tradicional","poteo"],"medios": ["brunch","mercado","low-cost"]},
    "activo":     {"altos": ["deporte","outdoor","deportes-extremos","cuidarme"],       "medios": ["after-work","terraceo","brunch"]},
    "tranquilo":  {"altos": ["chill","vermut","terraceo","brunch","pelis"],             "medios": ["juegos-de-mesa","low-cost","mercado"]},
}

def generar_pesos(arquetipo):
    perfil = ARQUETIPOS[arquetipo]
    pesos = {tag: 0.0 for tag in TAGS_OFICIALES}
    for tag in perfil["altos"]:
        pesos[tag] = round(random.uniform(0.65, 0.95), 3)
    for tag in perfil["medios"]:
        pesos[tag] = round(random.uniform(0.30, 0.60), 3)
    for tag in TAGS_OFICIALES:
        if pesos[tag] == 0.0 and random.random() < 0.2:
            pesos[tag] = round(random.uniform(0.05, 0.20), 3)
    return pesos

# ── INIT BD ───────────────────────────────────────────────────────────────────

def init_db(conn):
    # activity_categories
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_categories (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    # activities — alineada con Full Stack + campos del motor
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT NOT NULL,
            municipio            TEXT NOT NULL,
            lat                  REAL NOT NULL,
            lng                  REAL NOT NULL,
            tag_1                TEXT,
            tag_2                TEXT,
            tag_3                TEXT,
            time_slot            TEXT NOT NULL,
            activity_category_id INTEGER,
            price                REAL DEFAULT 0.0,
            is_indoor            INTEGER DEFAULT 0,
            is_active            INTEGER DEFAULT 1,
            available_slots      INTEGER,
            age_range            TEXT,
            FOREIGN KEY (activity_category_id) REFERENCES activity_categories(id)
        );
    """)

    # user_weights
    cols_sql = ",\n    ".join([f"{tag_a_col(t)} REAL DEFAULT 0.0" for t in TAGS_OFICIALES])
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS user_weights (
            user_id INTEGER PRIMARY KEY,
            {cols_sql}
        );
    """)

    conn.commit()
    print("✓ Tablas verificadas")

# ── SEED ──────────────────────────────────────────────────────────────────────

def seed_categorias(conn):
    count = conn.execute("SELECT COUNT(*) FROM activity_categories").fetchone()[0]
    if count > 0:
        print(f"  activity_categories ya tiene {count} filas — saltando")
        return
    conn.executemany("INSERT INTO activity_categories (id, name) VALUES (?, ?)", CATEGORIAS)
    conn.commit()
    print(f"✓ {len(CATEGORIAS)} categorías insertadas")

def seed_activities(conn):
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if count > 0:
        print(f"  activities ya tiene {count} filas — saltando")
        return
    conn.executemany("""
        INSERT INTO activities
          (name, municipio, lat, lng, tag_1, tag_2, tag_3,
           time_slot, activity_category_id, price,
           is_indoor, is_active, available_slots, age_range)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, ACTIVIDADES)
    conn.commit()
    print(f"✓ {len(ACTIVIDADES)} actividades insertadas")

def seed_users(conn, n=25):
    count = conn.execute("SELECT COUNT(*) FROM user_weights").fetchone()[0]
    if count > 0:
        print(f"  user_weights ya tiene {count} filas — saltando")
        return
    cols = [tag_a_col(t) for t in TAGS_OFICIALES]
    cols_str = ", ".join(cols)
    placeholders = ", ".join(["?"] * len(cols))
    arquetipos = list(ARQUETIPOS.keys())
    for user_id in range(1, n + 1):
        pesos = generar_pesos(random.choice(arquetipos))
        valores = [pesos[t] for t in TAGS_OFICIALES]
        conn.execute(
            f"INSERT INTO user_weights (user_id, {cols_str}) VALUES (?, {placeholders})",
            [user_id] + valores
        )
    conn.commit()
    print(f"✓ {n} usuarios insertados con pesos")

def verificar(conn):
    print(f"\n─── Resumen ─────────────────────────────")
    for tabla in ["activity_categories", "activities", "user_weights"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        print(f"  {tabla:<25} {n} filas")

    print(f"\n─── Muestra activities ──────────────────")
    rows = conn.execute("""
        SELECT a.id, a.name, a.municipio, a.tag_1, a.time_slot, a.price, c.name
        FROM activities a
        LEFT JOIN activity_categories c ON c.id = a.activity_category_id
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"  [{r[0]}] {r[1]:<40} {r[2]:<12} {r[3]:<15} {r[4]:<8} {r[5]}€  [{r[6]}]")

    print(f"\n─── Muestra user_weights ────────────────")
    rows = conn.execute(
        "SELECT user_id, conciertos, gastronomia, party, chill FROM user_weights LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"  user_id={r[0]}  conciertos={r[1]}  gastronomia={r[2]}  party={r[3]}  chill={r[4]}")
    print()

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nConectando a {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        seed_categorias(conn)
        seed_activities(conn)
        seed_users(conn, n=25)
        verificar(conn)
        print("✅ Seed completado\n")
    finally:
        conn.close()
