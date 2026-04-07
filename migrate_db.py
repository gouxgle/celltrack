"""
Script de migración segura para CellTrack.
Agrega columnas y tablas nuevas sin tocar datos existentes.
Ejecutar: docker exec celltrack_web python migrate_db.py
"""
import os
import pymysql

HOST = os.getenv('MYSQL_HOST', '192.168.0.7')
PORT = int(os.getenv('MYSQL_PORT', 3306))
USER = os.getenv('MYSQL_USER', 'celltrack')
PASS = os.getenv('MYSQL_PASSWORD', 'Celulares580')
DB   = os.getenv('MYSQL_DATABASE', 'gcel')

conn = pymysql.connect(
    host=HOST, port=PORT, user=USER, password=PASS,
    database=DB, ssl_disabled=True, autocommit=True
)
cur = conn.cursor()

def column_exists(table, column):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DB, table, column)
    )
    return cur.fetchone()[0] > 0

def table_exists(table):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
        (DB, table)
    )
    return cur.fetchone()[0] > 0

changes = []

# ── respxchip: condicion, observaciones ──────────────────────────────────────
if not column_exists('respxchip', 'condicion'):
    cur.execute("ALTER TABLE respxchip ADD COLUMN condicion VARCHAR(20) DEFAULT 'BUENO'")
    changes.append("respxchip.condicion agregada")

if not column_exists('respxchip', 'observaciones'):
    cur.execute("ALTER TABLE respxchip ADD COLUMN observaciones TEXT")
    changes.append("respxchip.observaciones agregada")

# ── celxresp: condicion, observaciones, idchip ───────────────────────────────
if not column_exists('celxresp', 'condicion'):
    cur.execute("ALTER TABLE celxresp ADD COLUMN condicion VARCHAR(20) DEFAULT 'BUENO'")
    changes.append("celxresp.condicion agregada")

if not column_exists('celxresp', 'observaciones'):
    cur.execute("ALTER TABLE celxresp ADD COLUMN observaciones TEXT")
    changes.append("celxresp.observaciones agregada")

if not column_exists('celxresp', 'idchip'):
    cur.execute("ALTER TABLE celxresp ADD COLUMN idchip INT NULL")
    changes.append("celxresp.idchip agregada")

# ── tabla auditoria ───────────────────────────────────────────────────────────
if not table_exists('auditoria'):
    cur.execute("""
        CREATE TABLE auditoria (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            fecha      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            idusuario  INT NOT NULL,
            usuario    VARCHAR(30) NOT NULL,
            accion     VARCHAR(20) NOT NULL,
            entidad    VARCHAR(30) NOT NULL,
            id_entidad INT,
            detalle    TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    changes.append("tabla auditoria creada")

# ── tabla usuario ─────────────────────────────────────────────────────────────
if not table_exists('usuario'):
    cur.execute("""
        CREATE TABLE usuario (
            idusuario INT AUTO_INCREMENT PRIMARY KEY,
            usuario   VARCHAR(30) NOT NULL UNIQUE,
            password  VARCHAR(255) NOT NULL,
            nombre    VARCHAR(60) NOT NULL,
            admin     TINYINT(1) DEFAULT 0,
            activo    TINYINT(1) DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    changes.append("tabla usuario creada")

cur.close()
conn.close()

if changes:
    print("Migraciones aplicadas:")
    for c in changes:
        print(f"  ✓ {c}")
else:
    print("Base de datos ya actualizada, no se necesitan cambios.")
