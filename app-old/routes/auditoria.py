from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import db, Auditoria
from sqlalchemy import desc

bp = Blueprint('auditoria', __name__, url_prefix='/auditoria')


@bp.route('/')
@login_required
def index():
    entidad_f = request.args.get('entidad', '').strip()
    accion_f  = request.args.get('accion', '').strip()
    usuario_f = request.args.get('usuario', '').strip()
    q         = request.args.get('q', '').strip()
    page      = request.args.get('page', 1, type=int)

    query = Auditoria.query

    if entidad_f:
        query = query.filter(Auditoria.entidad == entidad_f.lower())
    if accion_f:
        query = query.filter(Auditoria.accion == accion_f.upper())
    if usuario_f:
        query = query.filter(Auditoria.usuario.like(f'%{usuario_f}%'))
    if q:
        query = query.filter(Auditoria.detalle.like(f'%{q}%'))

    registros = query.order_by(desc(Auditoria.fecha)).paginate(page=page, per_page=50)

    # Valores únicos para filtros
    entidades = db.session.query(Auditoria.entidad).distinct().order_by(Auditoria.entidad).all()
    acciones  = db.session.query(Auditoria.accion).distinct().order_by(Auditoria.accion).all()

    return render_template('auditoria/index.html',
        registros=registros,
        entidades=[e[0] for e in entidades],
        acciones=[a[0] for a in acciones],
        entidad_f=entidad_f, accion_f=accion_f,
        usuario_f=usuario_f, q=q)
