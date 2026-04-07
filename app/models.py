from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import types
from datetime import date as _date

db = SQLAlchemy()


class FlexDate(types.TypeDecorator):
    """Columna DATE que también acepta strings 'YYYY-MM-DD' del esquema legacy."""
    impl = types.Date
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, _date):
            return value
        if isinstance(value, str):
            if not value or value.startswith('0000'):
                return None
            try:
                return _date.fromisoformat(value[:10])
            except Exception:
                return None
        return value


# ── Autenticación ──────────────────────────────────────────────────────────────

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    idusuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario   = db.Column(db.String(30), nullable=False, unique=True)
    password  = db.Column(db.String(255), nullable=False)
    nombre    = db.Column(db.String(60), nullable=False)
    admin     = db.Column(db.Boolean, default=False)
    activo    = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.idusuario)

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password, pwd)


# ── Catálogos ──────────────────────────────────────────────────────────────────

class Distrito(db.Model):
    __tablename__ = 'distrito'
    iddistrito = db.Column(db.Integer, primary_key=True)
    distrito   = db.Column(db.String(25), nullable=False)
    localidades = db.relationship('Localidad', backref='distrito_rel', lazy='dynamic')


class Localidad(db.Model):
    __tablename__ = 'localidad'
    idlocalidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    localidad   = db.Column(db.String(30), nullable=False)
    codigo      = db.Column(db.String(3), nullable=False)
    iddistrito  = db.Column(db.Integer, db.ForeignKey('distrito.iddistrito'), nullable=False)


class Sector(db.Model):
    __tablename__ = 'sector'
    idsector = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sector   = db.Column(db.String(25), nullable=False)


class Marca(db.Model):
    __tablename__ = 'marca'
    idmarca = db.Column(db.Integer, primary_key=True, autoincrement=True)
    marca   = db.Column(db.String(25), nullable=False)
    modelos = db.relationship('Modelo', backref='marca_rel', lazy='dynamic',
                              foreign_keys='Modelo.idmarca')


class Modelo(db.Model):
    __tablename__ = 'modelo'
    idmarca     = db.Column(db.Integer, db.ForeignKey('marca.idmarca'), primary_key=True)
    idmodelo    = db.Column(db.String(3), primary_key=True)
    modelo      = db.Column(db.String(20), nullable=False)
    disponibles = db.Column(db.Integer, default=0)


class Prestadora(db.Model):
    __tablename__ = 'prestadora'
    idprestadora = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prestadora   = db.Column(db.String(30), nullable=False)


class Servicio(db.Model):
    __tablename__ = 'servicio'
    idservicio = db.Column(db.Integer, primary_key=True, autoincrement=True)
    servicio   = db.Column(db.String(20), nullable=False)


class Motivo(db.Model):
    __tablename__ = 'motivo'
    idmotivo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    motivo   = db.Column(db.String(40), nullable=False)


# ── Entidades principales ──────────────────────────────────────────────────────

class Celular(db.Model):
    __tablename__ = 'celular'
    idcelular = db.Column(db.Integer, primary_key=True, autoincrement=True)
    imei      = db.Column(db.String(15), nullable=False)
    serie     = db.Column(db.String(20))
    idmarca   = db.Column(db.Integer, db.ForeignKey('marca.idmarca'), nullable=False)
    idmodelo  = db.Column(db.String(3), nullable=False)
    baja      = db.Column(FlexDate)
    idmotivo  = db.Column(db.Integer, db.ForeignKey('motivo.idmotivo'))

    marca    = db.relationship('Marca', foreign_keys=[idmarca])
    motivo   = db.relationship('Motivo', foreign_keys=[idmotivo])
    asignaciones = db.relationship('CelxResp', backref='celular_rel', lazy='dynamic',
                                   foreign_keys='CelxResp.idcelular')

    @property
    def modelo_rel(self):
        return Modelo.query.filter_by(idmarca=self.idmarca, idmodelo=self.idmodelo).first()

    @property
    def activo(self):
        return self.baja is None

    @property
    def asignacion_actual(self):
        return self.asignaciones.filter_by(hasta=None).first()


class Chip(db.Model):
    __tablename__ = 'chip'
    idchip       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idprestadora = db.Column(db.Integer, db.ForeignKey('prestadora.idprestadora'), nullable=False)
    nrolinea     = db.Column(db.String(15), nullable=False)
    idservicio   = db.Column(db.Integer, db.ForeignKey('servicio.idservicio'), nullable=False)
    baja         = db.Column(FlexDate)
    idmotivo     = db.Column(db.Integer, db.ForeignKey('motivo.idmotivo'))
    nrochip      = db.Column(db.String(20))
    plan         = db.Column(db.String(10))
    descripcion  = db.Column(db.String(100))

    prestadora = db.relationship('Prestadora', foreign_keys=[idprestadora])
    servicio   = db.relationship('Servicio', foreign_keys=[idservicio])
    motivo     = db.relationship('Motivo', foreign_keys=[idmotivo])
    asignaciones = db.relationship('RespxChip', backref='chip_rel', lazy='dynamic',
                                   foreign_keys='RespxChip.idchip')

    @property
    def activo(self):
        return self.baja is None

    @property
    def asignacion_actual(self):
        return self.asignaciones.filter_by(hasta=None).first()


class Responsable(db.Model):
    __tablename__ = 'responsable'
    idresponsable = db.Column(db.Integer, primary_key=True, autoincrement=True)
    responsable   = db.Column(db.String(40), nullable=False)
    idlocalidad   = db.Column(db.Integer, db.ForeignKey('localidad.idlocalidad'), nullable=False)
    idsector      = db.Column(db.Integer, db.ForeignKey('sector.idsector'), nullable=False)

    localidad_rel = db.relationship('Localidad', foreign_keys=[idlocalidad])
    sector_rel    = db.relationship('Sector', foreign_keys=[idsector])
    celulares     = db.relationship('CelxResp', backref='responsable_cel', lazy='dynamic',
                                    foreign_keys='CelxResp.idresponsable')
    chips         = db.relationship('RespxChip', backref='responsable_chip', lazy='dynamic',
                                    foreign_keys='RespxChip.idresponsable')

    @property
    def celulares_activos(self):
        return self.celulares.filter_by(hasta=None).all()

    @property
    def chips_activos(self):
        return self.chips.filter_by(hasta=None).all()


# ── Vínculos (historial) ───────────────────────────────────────────────────────

class CelxResp(db.Model):
    __tablename__ = 'celxresp'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idresponsable = db.Column(db.Integer, db.ForeignKey('responsable.idresponsable'), nullable=False)
    idcelular     = db.Column(db.Integer, db.ForeignKey('celular.idcelular'), nullable=False)
    idchip        = db.Column(db.Integer, db.ForeignKey('chip.idchip'), nullable=True)
    desde         = db.Column(db.Date)
    hasta         = db.Column(db.Date)
    condicion     = db.Column(db.String(20), default='BUENO')
    observaciones = db.Column(db.Text)
    idmotivo      = db.Column(db.Integer, db.ForeignKey('motivo.idmotivo'))

    motivo_rel    = db.relationship('Motivo', foreign_keys=[idmotivo])
    chip_asignado = db.relationship('Chip', foreign_keys=[idchip])


class RespxChip(db.Model):
    __tablename__ = 'respxchip'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idresponsable = db.Column(db.Integer, db.ForeignKey('responsable.idresponsable'), nullable=False)
    idchip        = db.Column(db.Integer, db.ForeignKey('chip.idchip'), nullable=False)
    desde         = db.Column(db.Date)
    hasta         = db.Column(db.Date)
    condicion     = db.Column(db.String(20), default='BUENO')
    observaciones = db.Column(db.Text)
    idmotivo      = db.Column(db.Integer, db.ForeignKey('motivo.idmotivo'))

    motivo_rel    = db.relationship('Motivo', foreign_keys=[idmotivo])


# ── Auditoría ─────────────────────────────────────────────────────────────────

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha      = db.Column(db.DateTime, nullable=False,
                           server_default=db.func.current_timestamp())
    idusuario  = db.Column(db.Integer, nullable=False)
    usuario    = db.Column(db.String(30), nullable=False)
    accion     = db.Column(db.String(20), nullable=False)
    entidad    = db.Column(db.String(30), nullable=False)
    id_entidad = db.Column(db.Integer)
    detalle    = db.Column(db.Text)


# ── Reportes de facturación ────────────────────────────────────────────────────

class Reporte(db.Model):
    __tablename__ = 'reporte'
    nrolinea        = db.Column(db.String(15), primary_key=True)
    Bill            = db.Column(db.BigInteger)
    Plan            = db.Column(db.String(50))
    PlanDescripcion = db.Column(db.String(50))
    Importe         = db.Column(db.Integer)
    PromoPlan       = db.Column(db.String(50))
    DescripPlan     = db.Column(db.String(50))
    Desde           = db.Column(db.DateTime)
    Hasta           = db.Column(db.DateTime)
    Status          = db.Column(db.String(50))
    ActivaLinea     = db.Column(db.DateTime)
    Sim             = db.Column(db.BigInteger)
