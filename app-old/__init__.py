from flask import Flask, redirect, url_for, request, flash, session
from flask_login import LoginManager, logout_user, current_user
import os
from datetime import datetime, timedelta
from config import Config
from app.models import db, Usuario

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    cfg = Config()
    app.config.from_object(cfg)
    app.config['SQLALCHEMY_DATABASE_URI'] = cfg.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'ssl_disabled': True}}

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Iniciá sesión para continuar.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(uid):
        return Usuario.query.get(int(uid))

    @app.before_request
    def check_session():
        if request.endpoint in ('auth.login', 'auth.logout', 'static'):
            return
        if current_user.is_authenticated:
            login_time = session.get('login_time')
            if login_time:
                elapsed = datetime.utcnow() - datetime.fromisoformat(login_time)
                if elapsed > timedelta(hours=8):
                    logout_user()
                    session.clear()
                    flash('Sesión expirada. Ingresá nuevamente.', 'warning')
                    return redirect(url_for('auth.login'))

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    # Registrar blueprints
    from app.routes import auth, main, celulares, chips, responsables, catalogos, reportes, auditoria, operadores
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(celulares.bp)
    app.register_blueprint(chips.bp)
    app.register_blueprint(responsables.bp)
    app.register_blueprint(catalogos.bp)
    app.register_blueprint(reportes.bp)
    app.register_blueprint(auditoria.bp)
    app.register_blueprint(operadores.bp)

    os.makedirs('logs', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app
