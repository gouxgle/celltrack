"""
Ejecutar una sola vez para crear el usuario administrador inicial.
Uso: python seed_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import db, Usuario

app = create_app()

with app.app_context():
    if Usuario.query.filter_by(usuario='admin').first():
        print('El usuario admin ya existe.')
        sys.exit(0)

    admin = Usuario(
        usuario='admin',
        nombre='Administrador',
        admin=True,
        activo=True
    )
    admin.set_password('Celulares580')
    db.session.add(admin)
    db.session.commit()
    print('Usuario admin creado.')
    print('  Usuario:    admin')
    print('  Contraseña: Celulares580')
