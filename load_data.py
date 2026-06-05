"""
load_data.py — Cargar restaurantes y actividades reales en SQLite
=================================================================
Fuentes:
  restaurantes_clean2.csv        → tabla businesses
  actividades_kulturklik_clean.csv → tabla activities

Ejecutar: python load_data.py
"""

import sqlite3
import pandas as pd
import os

DB_PATH   = os.environ.get("DB_PATH", "weights.db")
CSV_REST  = os.environ.get("CSV_REST",  "restaurantes_clean2.csv")
CSV_ACTS  = os.environ.get("CSV_ACTS",  "actividades_kulturklik_clean.csv")

# Mapeo de franja del CSV → time_slot del motor
FRANJA_MAP = {
    "Mañana": "manana",
    "Tarde":  "tarde",
    "Noche":  "noche",
}

# ── INIT BD ───────────────────────────────────────────────────────────────────

def init_db(conn):
    """Crea las tablas si no existen."""

    # businesses — comercios / restaurantes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            municipio   TEXT,
            lat         REAL,
            lng         REAL,
            tipo        TEXT,
            telefono    TEXT,
            direccion   TEXT,
            email       TEXT,
            web         TEXT,
            tag_1       TEXT,
            tag_2       TEXT,
            tag_3       TEXT
        );
    """)

    # activities — actividades Kulturklik
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            municipio       TEXT,
            lat             REAL,
            lng             REAL,
            tag_1           TEXT,
            tag_2           TEXT,
            tag_3           TEXT,
            time_slot       TEXT,
            price           REAL DEFAULT 0.0,
            fecha_inicio    TEXT,
            fecha_fin       TEXT,
            horario         TEXT,
            is_active       INTEGER DEFAULT 1,
            is_indoor       INTEGER DEFAULT 0
        );
    """)

    conn.commit()
    print("✓ Tablas verificadas")

# ── CARGAR RESTAURANTES ───────────────────────────────────────────────────────

def load_businesses(conn):
    count = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
    if count > 0:
        print(f"  businesses ya tiene {count} filas — saltando")
        return

    df = pd.read_csv(CSV_REST)
    df = df.where(pd.notnull(df), None)  # NaN → None para SQLite

    rows = []
    for _, r in df.iterrows():
        rows.append((
            r.get("Nombre"),
            r.get("Localidad"),
            r.get("LATWGS84"),
            r.get("LONWGS84"),
            r.get("Tipo de Restauración"),
            r.get("Teléfono"),
            r.get("Dirección"),
            r.get("Email"),
            r.get("WEB"),
            r.get("tag1"),
            r.get("tag2"),
            r.get("tag3"),
        ))

    conn.executemany("""
        INSERT INTO businesses
          (name, municipio, lat, lng, tipo, telefono, direccion, email, web, tag_1, tag_2, tag_3)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    print(f"✓ {len(rows)} restaurantes/comercios cargados en businesses")

# ── CARGAR ACTIVIDADES ────────────────────────────────────────────────────────

def load_activities(conn):
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if count > 0:
        print(f"  activities ya tiene {count} filas — saltando")
        return

    df = pd.read_csv(CSV_ACTS)
    df = df.where(pd.notnull(df), None)

    rows = []
    for _, r in df.iterrows():
        # Normalizar franja a time_slot del motor
        franja_raw = r.get("franja") or "Tarde"
        time_slot  = FRANJA_MAP.get(franja_raw, "tarde")

        # Precio: usar precio_min como referencia
        price = r.get("precio_min") or 0.0

        # is_indoor: si tag1, tag2 o tag3 contiene "indoor"
        tags = [r.get("tag1"), r.get("tag2"), r.get("tag3")]
        is_indoor = 1 if any(t and "indoor" in str(t).lower() for t in tags) else 0

        rows.append((
            r.get("nombre_evento"),
            r.get("municipio"),
            r.get("lat"),
            r.get("lng"),
            r.get("tag1"),
            r.get("tag2"),
            r.get("tag3"),
            time_slot,
            float(price),
            r.get("fecha_inicio"),
            r.get("fecha_fin"),
            r.get("horario"),
            1,         # is_active
            is_indoor,
        ))

    conn.executemany("""
        INSERT INTO activities
          (name, municipio, lat, lng, tag_1, tag_2, tag_3,
           time_slot, price, fecha_inicio, fecha_fin, horario,
           is_active, is_indoor)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    print(f"✓ {len(rows)} actividades cargadas en activities")

# ── VERIFICAR ─────────────────────────────────────────────────────────────────

def verificar(conn):
    print(f"\n─── Resumen ─────────────────────────────────────")
    for tabla in ["businesses", "activities", "user_weights"]:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla:<25} {n:>6} filas")
        except:
            print(f"  {tabla:<25} (no existe)")

    print(f"\n─── Muestra businesses ──────────────────────────")
    rows = conn.execute(
        "SELECT id, name, municipio, tipo, tag_1, tag_2 FROM businesses LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"  [{r[0]}] {str(r[1]):<35} {str(r[2]):<20} {str(r[3]):<15} {r[4]}/{r[5]}")

    print(f"\n─── Muestra activities ──────────────────────────")
    rows = conn.execute(
        "SELECT id, name, municipio, tag_1, time_slot, price FROM activities LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"  [{r[0]}] {str(r[1]):<45} {str(r[2]):<15} {r[3]:<15} {r[4]:<8} {r[5]}€")

    print(f"\n─── Distribución por time_slot ──────────────────")
    rows = conn.execute(
        "SELECT time_slot, COUNT(*) as n FROM activities GROUP BY time_slot ORDER BY n DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:<10} {r[1]} actividades")

    print(f"\n─── Distribución por municipio (top 8) ──────────")
    rows = conn.execute("""
        SELECT municipio, COUNT(*) as n FROM activities
        WHERE municipio IS NOT NULL
        GROUP BY municipio ORDER BY n DESC LIMIT 8
    """).fetchall()
    for r in rows:
        print(f"  {str(r[0]):<25} {r[1]} actividades")
    print()

# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nConectando a {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_businesses(conn)
        load_activities(conn)
        verificar(conn)
        print("✅ Carga completada\n")
    finally:
        conn.close()
