from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.models import db, Usuario
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        uname = request.form.get('usuario', '').strip()
        pwd   = request.form.get('password', '')

        user = Usuario.query.filter_by(usuario=uname, activo=True).first()
        if user and user.check_password(pwd):
            login_user(user)
            session['login_time'] = datetime.utcnow().isoformat()
            return redirect(url_for('main.dashboard'))

        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


@bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        actual  = request.form.get('actual', '')
        nueva   = request.form.get('nueva', '')
        confirm = request.form.get('confirmar', '')

        if not current_user.check_password(actual):
            flash('La contraseña actual es incorrecta.', 'danger')
        elif nueva != confirm:
            flash('Las contraseñas nuevas no coinciden.', 'danger')
        elif len(nueva) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
        else:
            current_user.set_password(nueva)
            db.session.commit()
            flash('Contraseña actualizada.', 'success')
            return redirect(url_for('main.dashboard'))

    return render_template('auth/cambiar_password.html')
