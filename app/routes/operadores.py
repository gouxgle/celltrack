from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.models import db, Usuario
from app.utils.auditoria import log as audit
from functools import wraps

bp = Blueprint('operadores', __name__, url_prefix='/operadores')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@login_required
@admin_required
def lista():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template('operadores/lista.html', usuarios=usuarios)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo():
    if request.method == 'POST':
        nombre  = request.form.get('nombre', '').strip()
        usuario = request.form.get('usuario', '').strip().lower()
        pwd     = request.form.get('password', '')
        confirm = request.form.get('confirmar', '')
        admin   = request.form.get('admin') == '1'

        if not nombre or not usuario or not pwd:
            flash('Nombre, usuario y contraseña son obligatorios.', 'danger')
        elif len(pwd) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        elif pwd != confirm:
            flash('Las contraseñas no coinciden.', 'danger')
        elif Usuario.query.filter_by(usuario=usuario).first():
            flash(f'El usuario "{usuario}" ya existe.', 'danger')
        else:
            u = Usuario(nombre=nombre, usuario=usuario, admin=admin, activo=True)
            u.set_password(pwd)
            db.session.add(u)
            db.session.flush()
            audit('CREAR', 'usuario', u.idusuario,
                  f'nuevo operador: {usuario} | nombre: {nombre} | admin: {admin}')
            db.session.commit()
            flash(f'Operador "{nombre}" creado.', 'success')
            return redirect(url_for('operadores.lista'))

    return render_template('operadores/form.html', usuario=None)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar(id):
    u = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        cambios = []
        nombre_nuevo = request.form.get('nombre', '').strip()
        if u.nombre != nombre_nuevo:
            cambios.append(f'nombre: {u.nombre} → {nombre_nuevo}')
            u.nombre = nombre_nuevo

        admin_nuevo = request.form.get('admin') == '1'
        if u.admin != admin_nuevo:
            cambios.append(f'admin: {u.admin} → {admin_nuevo}')
            u.admin = admin_nuevo

        activo_nuevo = request.form.get('activo') == '1'
        if u.activo != activo_nuevo:
            cambios.append(f'activo: {u.activo} → {activo_nuevo}')
            u.activo = activo_nuevo

        nueva_pwd = request.form.get('password', '').strip()
        if nueva_pwd:
            if len(nueva_pwd) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
                return render_template('operadores/form.html', usuario=u)
            if nueva_pwd != request.form.get('confirmar', ''):
                flash('Las contraseñas no coinciden.', 'danger')
                return render_template('operadores/form.html', usuario=u)
            u.set_password(nueva_pwd)
            cambios.append('contraseña actualizada')

        # No permitir dejar sin admin si es el único admin activo
        if not admin_nuevo and id == current_user.idusuario:
            flash('No podés quitarte el rol admin a vos mismo.', 'danger')
            return render_template('operadores/form.html', usuario=u)

        if cambios:
            audit('EDITAR', 'usuario', id, ' | '.join(cambios))
        db.session.commit()
        flash('Operador actualizado.', 'success')
        return redirect(url_for('operadores.lista'))

    return render_template('operadores/form.html', usuario=u)


@bp.route('/<int:id>/toggle-activo', methods=['POST'])
@login_required
@admin_required
def toggle_activo(id):
    u = Usuario.query.get_or_404(id)
    if u.idusuario == current_user.idusuario:
        flash('No podés desactivarte a vos mismo.', 'danger')
        return redirect(url_for('operadores.lista'))
    u.activo = not u.activo
    accion = 'ACTIVAR' if u.activo else 'DESACTIVAR'
    audit(accion, 'usuario', id, f'operador: {u.usuario}')
    db.session.commit()
    flash(f'Operador {"activado" if u.activo else "desactivado"}.', 'success')
    return redirect(url_for('operadores.lista'))
