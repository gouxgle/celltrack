from flask import Blueprint, render_template
from flask_login import login_required
from app.models import db, Celular, Chip, Responsable, CelxResp, RespxChip, Sector
from sqlalchemy import func

bp = Blueprint('main', __name__)

_sin_baja_cel  = db.or_(Celular.baja.is_(None),  Celular.baja  == '', Celular.baja  == '0000-00-00')
_sin_baja_chip = db.or_(Chip.baja.is_(None),     Chip.baja     == '', Chip.baja     == '0000-00-00')
_sin_hasta_cel  = db.or_(CelxResp.hasta.is_(None),  CelxResp.hasta  == '', CelxResp.hasta  == '0000-00-00')
_sin_hasta_chip = db.or_(RespxChip.hasta.is_(None), RespxChip.hasta == '', RespxChip.hasta == '0000-00-00')


@bp.route('/')
@login_required
def dashboard():
    # ── Totales celulares ──────────────────────────────────────────────────────
    cel_total     = Celular.query.count()
    cel_activos   = Celular.query.filter(_sin_baja_cel).count()
    cel_baja      = cel_total - cel_activos
    cel_asignados = (db.session.query(func.count(CelxResp.id))
                     .join(Celular, CelxResp.idcelular == Celular.idcelular)
                     .filter(_sin_hasta_cel, _sin_baja_cel).scalar())
    cel_libres    = cel_activos - cel_asignados

    # ── Totales chips ──────────────────────────────────────────────────────────
    chip_total     = Chip.query.count()
    chip_activos   = Chip.query.filter(_sin_baja_chip).count()
    chip_baja      = chip_total - chip_activos
    chip_asignados = (db.session.query(func.count(RespxChip.id))
                      .join(Chip, RespxChip.idchip == Chip.idchip)
                      .filter(_sin_hasta_chip, _sin_baja_chip).scalar())
    chip_libres    = chip_activos - chip_asignados

    # ── Responsables ───────────────────────────────────────────────────────────
    resp_total = Responsable.query.count()

    # ── Últimas 8 asignaciones activas ────────────────────────────────────────
    ultimas = (
        db.session.query(CelxResp, Celular, Responsable)
        .join(Celular,     CelxResp.idcelular     == Celular.idcelular)
        .join(Responsable, CelxResp.idresponsable == Responsable.idresponsable)
        .filter(_sin_hasta_cel)
        .order_by(CelxResp.desde.desc())
        .limit(8).all()
    )

    # ── Top sectores con más equipos ──────────────────────────────────────────
    top_sectores = (
        db.session.query(Sector.sector, func.count(CelxResp.id).label('total'))
        .join(Responsable, Sector.idsector == Responsable.idsector)
        .join(CelxResp, Responsable.idresponsable == CelxResp.idresponsable)
        .filter(_sin_hasta_cel)
        .group_by(Sector.idsector, Sector.sector)
        .order_by(func.count(CelxResp.id).desc())
        .limit(6).all()
    )

    # ── Alertas: responsables con celular pero sin chip ────────────────────────
    resp_sin_chip = (
        db.session.query(Responsable)
        .join(CelxResp, Responsable.idresponsable == CelxResp.idresponsable)
        .filter(_sin_hasta_cel)
        .filter(
            ~Responsable.idresponsable.in_(
                db.session.query(RespxChip.idresponsable).filter(_sin_hasta_chip)
            )
        )
        .distinct()
        .limit(5).all()
    )

    return render_template('dashboard/index.html',
        cel_activos=cel_activos,   cel_baja=cel_baja,
        cel_asignados=cel_asignados, cel_libres=cel_libres,
        chip_activos=chip_activos,  chip_baja=chip_baja,
        chip_asignados=chip_asignados, chip_libres=chip_libres,
        resp_total=resp_total,
        ultimas=ultimas,
        top_sectores=top_sectores,
        resp_sin_chip=resp_sin_chip,
    )
