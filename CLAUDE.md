# CLAUDE.md — CellTrack REFSA

Contexto del proyecto para Claude Code. Se carga automáticamente en cada sesión.

---

## Stack técnico

- **Backend:** Flask + SQLAlchemy ORM (≠ almacenes que usa cursores directos)
- **Auth:** Flask-Login + werkzeug `generate_password_hash` / `check_password_hash`
- **Base de datos:** MySQL `gcel` en `192.168.0.7:3306`, usuario `celltrack`
- **Contenedor:** Docker, `container_name=celltrack_web`, puerto `5010:5000`, red bridge
- **WSGI:** Gunicorn 2 workers (`run:app`)
- **PDFs:** fpdf2 (`FPDF` subclase `ActaPDF`) — NO ReportLab
- **Reportes:** openpyxl para export Excel
- **Volume mount:** `./app:/app/app` + `./config.py:/app/config.py` — hot-reload activo para código Python y templates sin rebuild
- **Credenciales:** en `docker-compose.yml` como env vars (no hay `.env` separado)

---

## Estructura del proyecto

```
run.py                        # Entry point: create_app() + app.run()
config.py                     # Config class — lee env vars, construye SQLALCHEMY_DATABASE_URI
app/
  __init__.py                 # Factory create_app(): init db, login_manager, blueprints, sesión 8h
  models.py                   # Todos los modelos SQLAlchemy
  routes/
    auth.py                   # Blueprint auth — /auth/login, /auth/logout, /auth/cambiar-password
    main.py                   # Blueprint main — / dashboard con métricas
    celulares.py              # Blueprint celulares — /celulares/
    chips.py                  # Blueprint chips — /chips/
    responsables.py           # Blueprint responsables — /responsables/
    catalogos.py              # Blueprint catalogos — /catalogos/marcas, modelos, sectores, localidades
    reportes.py               # Blueprint reportes — /reportes/ + export Excel
    auditoria.py              # Blueprint auditoria — /auditoria/ (solo admin)
    operadores.py             # Blueprint operadores — /operadores/ (solo admin)
  utils/
    auditoria.py              # log(accion, entidad, id_entidad, detalle) — nunca rompe la operación
    pdf_acta.py               # generar_acta_celular() → bytes PDF acta de comodato A4
  templates/
    base.html                 # Layout base Bootstrap
    auth/login.html
    celulares/lista.html, ver.html, form.html
    chips/lista.html, ver.html, form.html
    responsables/lista.html, ver.html, form.html
    catalogos/marcas.html, modelos.html, sectores.html, localidades.html
    reportes/index.html
    auditoria/index.html
    operadores/lista.html, form.html
    dashboard/index.html
  static/images/Logo_REFSA.jpg
```

---

## Modelos principales (`app/models.py`)

### Autenticación
```python
Usuario: idusuario, usuario (unique), password (hash), nombre, admin (bool), activo (bool)
```
Login: `user.check_password(pwd)` — werkzeug hash. `user.set_password(pwd)` para cambiar.

### Catálogos
| Modelo | PK | Campos clave |
|---|---|---|
| `Marca` | `idmarca` | `marca` |
| `Modelo` | `(idmarca, idmodelo)` — PK compuesta | `modelo`, `disponibles` |
| `Sector` | `idsector` | `sector` |
| `Localidad` | `idlocalidad` | `localidad`, `codigo`, `iddistrito` |
| `Distrito` | `iddistrito` | `distrito` |
| `Prestadora` | `idprestadora` | `prestadora` |
| `Servicio` | `idservicio` | `servicio` |
| `Motivo` | `idmotivo` | `motivo` (motivo de baja o devolución) |

### Entidades principales
```python
Celular: idcelular, imei (15), serie, idmarca, idmodelo, baja (FlexDate), idmotivo
Chip:    idchip, idprestadora, nrolinea (15), idservicio, baja (FlexDate), idmotivo, nrochip, plan, descripcion
Responsable: idresponsable, responsable (nombre en MAYÚSCULAS), idlocalidad, idsector
```

### Asignaciones (historial)
```python
CelxResp:  id, idresponsable, idcelular, idchip (nullable), desde, hasta, condicion, observaciones, idmotivo
RespxChip: id, idresponsable, idchip, desde, hasta, condicion, observaciones, idmotivo
```
**Regla crítica:** `hasta=NULL` (o `''` o `'0000-00-00'`) = asignación activa.
Siempre usar el helper:
```python
_sin_hasta = lambda col: db.or_(col.is_(None), col == '', col == '0000-00-00')
_sin_baja  = lambda col: db.or_(col.is_(None), col == '', col == '0000-00-00')
```
Estos helpers existen en cada route que los necesita (no son globales). Copiarlos localmente.

### Otros
```python
Auditoria: id, fecha, idusuario, usuario, accion, entidad, id_entidad, detalle
Reporte:   nrolinea (PK), Bill, Plan, PlanDescripcion, Importe, Status, ActivaLinea, Sim
```

### FlexDate
Tipo custom en `models.py` para columnas DATE con valores legacy `'0000-00-00'`. Devuelve `None` en esos casos. Usado en `Celular.baja` y `Chip.baja`.

---

## Lógica de negocio crítica

### Asignar celular
1. Verificar que el celular no tenga `baja` y no tenga asignación activa (`CelxResp.hasta IS NULL`)
2. Si se elige un chip ya asignado a otro celular → cerrar la asignación vieja (`hasta=hoy`), dar baja al celular viejo
3. Crear `CelxResp` nueva con `hasta=None`
4. Auditar con `audit('ASIGNAR', 'celular', id, detalle)`
5. Redirigir a `celulares.acta_pdf` para imprimir el acta

### Devolver celular
- Setear `CelxResp.hasta = fecha` + `CelxResp.idmotivo`
- NO dar baja al celular (queda disponible)

### Dar de baja celular/chip
- Setear `baja = date.today()` + `idmotivo`
- Cerrar asignación activa si existe

### Acta PDF (`/celulares/acta/<asign_id>.pdf`)
- Genera con `app/utils/pdf_acta.py:generar_acta_celular(asign, cel, resp, marca, modelo, chip)`
- Usa fpdf2, una página A4, incluye cláusulas de comodato
- Logo desde `app/static/images/Logo_REFSA.jpg`
- `Content-Disposition: inline` (abre en browser)

### Auditoría
```python
from app.utils.auditoria import log as audit
audit('ACCION', 'entidad', id_entidad, 'detalle texto libre')
```
Acciones estándar: `CREAR`, `EDITAR`, `BAJA`, `ASIGNAR`, `DEVOLVER`, `ACTIVAR`, `DESACTIVAR`, `IMPORTAR`
La función nunca hace commit — se hace junto con la operación principal.

### Admin-only
Rutas de `operadores` y `auditoria` usan `@admin_required` (decorator local en `operadores.py`).
Check: `current_user.admin == True`.

---

## Base de datos (`gcel`)

### Tablas principales
| Tabla | Descripción |
|---|---|
| `celular` | Inventario de equipos |
| `chip` | Inventario de SIM cards |
| `responsable` | Empleados/responsables |
| `celxresp` | Historial asignación cel→responsable |
| `respxchip` | Historial asignación chip→responsable |
| `marca`, `modelo` | Catálogo equipos |
| `prestadora`, `servicio` | Catálogo chips |
| `sector`, `localidad`, `distrito` | Catálogo organizacional |
| `motivo` | Motivos de baja/devolución |
| `usuario` | Operadores del sistema |
| `auditoria` | Log de operaciones |
| `reporte` | Datos de facturación importados (nrolinea PK) |

### Consulta típica de asignación activa
```python
# Celular activo en uso
asign = CelxResp.query.filter(
    CelxResp.idcelular == id,
    db.or_(CelxResp.hasta.is_(None), CelxResp.hasta == '', CelxResp.hasta == '0000-00-00')
).first()
```

---

## Iniciar / detener

```bash
cd /home/sistemas/docker/celulares_flask

# Iniciar
docker compose up -d

# Ver logs
docker logs -f celltrack_web

# Rebuild tras cambios en requirements.txt o Dockerfile
docker compose up -d --build

# Parar
docker compose down
```

El volume mount activa hot-reload automático para cambios en `app/` y `config.py` sin rebuild.

---

## Convenciones del código

- Factory pattern: `create_app()` en `app/__init__.py`, entry point en `run.py`
- Blueprints con `url_prefix` definido en la declaración del `bp`
- ORM SQLAlchemy — NO queries raw (excepto en `reportes.py` donde se usa `text()` para el join complejo)
- Sesión expira a las 8h desde login (`check_session` en `before_request`)
- `db.session.flush()` antes de auditar para obtener el PK del nuevo registro
- `db.session.commit()` siempre al final de la operación, nunca dentro de `audit()`
- Templates extienden `base.html` con bloques `title`, `content`
- Nombres de responsable se guardan en MAYÚSCULAS (`.strip().upper()`)
- `Modelo.idmodelo` es `String(3)` — código alfanumérico, no entero
