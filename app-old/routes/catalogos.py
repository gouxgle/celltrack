from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.models import db, Marca, Modelo, Sector, Localidad, Distrito, Prestadora, Servicio, Motivo

bp = Blueprint('catalogos', __name__, url_prefix='/catalogos')


# ── Marcas ─────────────────────────────────────────────────────────────────────

@bp.route('/marcas')
@login_required
def marcas():
    lista = Marca.query.order_by(Marca.marca).all()
    return render_template('catalogos/marcas.html', marcas=lista)


@bp.route('/marcas/nueva', methods=['POST'])
@login_required
def nueva_marca():
    nombre = request.form.get('marca', '').strip().upper()
    if nombre:
        db.session.add(Marca(marca=nombre))
        db.session.commit()
        flash(f'Marca {nombre} creada.', 'success')
    return redirect(url_for('catalogos.marcas'))


@bp.route('/marcas/<int:id>/editar', methods=['POST'])
@login_required
def editar_marca(id):
    m = Marca.query.get_or_404(id)
    m.marca = request.form.get('marca', '').strip().upper()
    db.session.commit()
    flash('Marca actualizada.', 'success')
    return redirect(url_for('catalogos.marcas'))


# ── Modelos ────────────────────────────────────────────────────────────────────

@bp.route('/modelos')
@login_required
def modelos():
    lista  = (
        db.session.query(Modelo, Marca)
        .join(Marca, Modelo.idmarca == Marca.idmarca)
        .order_by(Marca.marca, Modelo.modelo)
        .all()
    )
    marcas = Marca.query.order_by(Marca.marca).all()
    return render_template('catalogos/modelos.html', modelos=lista, marcas=marcas)


@bp.route('/modelos/nuevo', methods=['POST'])
@login_required
def nuevo_modelo():
    idmarca  = request.form.get('idmarca', type=int)
    idmodelo = request.form.get('idmodelo', '').strip().upper()
    nombre   = request.form.get('modelo', '').strip().upper()
    if idmarca and idmodelo and nombre:
        db.session.add(Modelo(idmarca=idmarca, idmodelo=idmodelo, modelo=nombre))
        db.session.commit()
        flash(f'Modelo {nombre} creado.', 'success')
    return redirect(url_for('catalogos.modelos'))


# ── Sectores ───────────────────────────────────────────────────────────────────

@bp.route('/sectores')
@login_required
def sectores():
    lista = Sector.query.order_by(Sector.sector).all()
    return render_template('catalogos/sectores.html', sectores=lista)


@bp.route('/sectores/nuevo', methods=['POST'])
@login_required
def nuevo_sector():
    nombre = request.form.get('sector', '').strip().upper()
    if nombre:
        db.session.add(Sector(sector=nombre))
        db.session.commit()
        flash(f'Sector {nombre} creado.', 'success')
    return redirect(url_for('catalogos.sectores'))


# ── Localidades ────────────────────────────────────────────────────────────────

@bp.route('/localidades')
@login_required
def localidades():
    lista     = (
        db.session.query(Localidad, Distrito)
        .join(Distrito, Localidad.iddistrito == Distrito.iddistrito)
        .order_by(Localidad.localidad)
        .all()
    )
    distritos = Distrito.query.order_by(Distrito.distrito).all()
    return render_template('catalogos/localidades.html', localidades=lista, distritos=distritos)


@bp.route('/localidades/nueva', methods=['POST'])
@login_required
def nueva_localidad():
    nombre     = request.form.get('localidad', '').strip().upper()
    codigo     = request.form.get('codigo', '').strip().upper()
    iddistrito = request.form.get('iddistrito', type=int)
    if nombre and codigo and iddistrito:
        db.session.add(Localidad(localidad=nombre, codigo=codigo, iddistrito=iddistrito))
        db.session.commit()
        flash(f'Localidad {nombre} creada.', 'success')
    return redirect(url_for('catalogos.localidades'))
