from app.models import db, Auditoria
from flask_login import current_user
from datetime import datetime


def log(accion: str, entidad: str, id_entidad=None, detalle: str = ''):
    """
    Registra un evento en la tabla auditoria.

    accion   : 'CREAR', 'EDITAR', 'BAJA', 'ASIGNAR', 'DEVOLVER', 'IMPORTAR'
    entidad  : 'celular', 'chip', 'responsable', 'marca', etc.
    id_entidad: PK del registro afectado (int)
    detalle  : texto libre con los cambios realizados
    """
    try:
        evento = Auditoria(
            fecha      = datetime.now(),
            idusuario  = int(current_user.get_id()),
            usuario    = current_user.usuario,
            accion     = accion.upper(),
            entidad    = entidad.lower(),
            id_entidad = id_entidad,
            detalle    = detalle[:2000] if detalle else None,
        )
        db.session.add(evento)
        # No hacemos commit aquí; se hace junto con la operación principal
    except Exception:
        pass  # La auditoría nunca debe romper la operación principal
