from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.models import db, Responsable, Localidad, Sector, CelxResp, RespxChip, Celular, Chip, Marca, Modelo, Prestadora
from app.utils.auditoria import log as audit

bp = Blueprint('responsables', __name__, url_prefix='/responsables')

_sin_hasta = lambda col: db.or_(col.is_(None), col == '', col == '0000-00-00')


@bp.route('/')
@login_required
def lista():
    q        = request.args.get('q', '').strip()
    sector_f = request.args.get('sector', type=int)
    loc_f    = request.args.get('localidad', type=int)

    query = (
        db.session.query(Responsable, Localidad, Sector)
        .join(Localidad, Responsable.idlocalidad == Localidad.idlocalidad)
        .join(Sector, Responsable.idsector == Sector.idsector)
    )

    if q:
        query = query.filter(Responsable.responsable.like(f'%{q}%'))
    if sector_f:
        query = query.filter(Responsable.idsector == sector_f)
    if loc_f:
        query = query.filter(Responsable.idlocalidad == loc_f)

    responsables = query.order_by(Responsable.responsable).all()

    resultado = []
    for resp, loc, sec in responsables:
        n_cel  = CelxResp.query.filter(CelxResp.idresponsable == resp.idresponsable, _sin_hasta(CelxResp.hasta)).count()
        n_chip = RespxChip.query.filter(RespxChip.idresponsable == resp.idresponsable, _sin_hasta(RespxChip.hasta)).count()
        resultado.append({'resp': resp, 'loc': loc, 'sec': sec,
                          'n_cel': n_cel, 'n_chip': n_chip})

    sectores    = Sector.query.order_by(Sector.sector).all()
    localidades = Localidad.query.order_by(Localidad.localidad).all()

    return render_template('responsables/lista.html',
        responsables=resultado, sectores=sectores, localidades=localidades,
        q=q, sector_f=sector_f, loc_f=loc_f)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        nombre      = request.form.get('responsable', '').strip().upper()
        idlocalidad = request.form.get('idlocalidad', type=int)
        idsector    = request.form.get('idsector', type=int)

        if not nombre or not idlocalidad or not idsector:
            flash('Todos los campos son obligatorios.', 'danger')
        else:
            r = Responsable(responsable=nombre, idlocalidad=idlocalidad, idsector=idsector)
            db.session.add(r)
            db.session.flush()
            audit('CREAR', 'responsable', r.idresponsable,
                  f'nombre={nombre} | localidad={idlocalidad} | sector={idsector}')
            db.session.commit()
            flash(f'Responsable {nombre} creado.', 'success')
            return redirect(url_for('responsables.ver', id=r.idresponsable))

    sectores    = Sector.query.order_by(Sector.sector).all()
    localidades = Localidad.query.order_by(Localidad.localidad).all()
    return render_template('responsables/form.html', resp=None,
                           sectores=sectores, localidades=localidades)


@bp.route('/<int:id>')
@login_required
def ver(id):
    resp = Responsable.query.get_or_404(id)
    loc  = Localidad.query.get(resp.idlocalidad)
    sec  = Sector.query.get(resp.idsector)

    # Celulares asignados actualmente
    cel_activos = (
        db.session.query(CelxResp, Celular, Marca, Modelo)
        .join(Celular, CelxResp.idcelular == Celular.idcelular)
        .join(Marca, Celular.idmarca == Marca.idmarca)
        .outerjoin(Modelo, (Celular.idmarca == Modelo.idmarca) & (Celular.idmodelo == Modelo.idmodelo))
        .filter(CelxResp.idresponsable == id, CelxResp.hasta.is_(None))
        .all()
    )

    # Chips asignados actualmente
    chip_activos = (
        db.session.query(RespxChip, Chip, Prestadora)
        .join(Chip, RespxChip.idchip == Chip.idchip)
        .join(Prestadora, Chip.idprestadora == Prestadora.idprestadora)
        .filter(RespxChip.idresponsable == id, RespxChip.hasta.is_(None))
        .all()
    )

    # Historial completo
    hist_cel = (
        db.session.query(CelxResp, Celular, Marca, Modelo)
        .join(Celular, CelxResp.idcelular == Celular.idcelular)
        .join(Marca, Celular.idmarca == Marca.idmarca)
        .outerjoin(Modelo, (Celular.idmarca == Modelo.idmarca) & (Celular.idmodelo == Modelo.idmodelo))
        .filter(CelxResp.idresponsable == id, CelxResp.hasta.isnot(None))
        .order_by(CelxResp.hasta.desc())
        .all()
    )

    hist_chip = (
        db.session.query(RespxChip, Chip, Prestadora)
        .join(Chip, RespxChip.idchip == Chip.idchip)
        .join(Prestadora, Chip.idprestadora == Prestadora.idprestadora)
        .filter(RespxChip.idresponsable == id, RespxChip.hasta.isnot(None))
        .order_by(RespxChip.hasta.desc())
        .all()
    )

    return render_template('responsables/ver.html',
        resp=resp, loc=loc, sec=sec,
        cel_activos=cel_activos, chip_activos=chip_activos,
        hist_cel=hist_cel, hist_chip=hist_chip)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    resp = Responsable.query.get_or_404(id)

    if request.method == 'POST':
        cambios = []
        nombre_nuevo  = request.form.get('responsable', '').strip().upper()
        loc_nuevo     = request.form.get('idlocalidad', type=int)
        sector_nuevo  = request.form.get('idsector', type=int)
        if resp.responsable != nombre_nuevo:
            cambios.append(f'nombre: {resp.responsable} → {nombre_nuevo}')
        if resp.idlocalidad != loc_nuevo:
            cambios.append(f'localidad: {resp.idlocalidad} → {loc_nuevo}')
        if resp.idsector != sector_nuevo:
            cambios.append(f'sector: {resp.idsector} → {sector_nuevo}')
        resp.responsable = nombre_nuevo
        resp.idlocalidad = loc_nuevo
        resp.idsector    = sector_nuevo
        if cambios:
            audit('EDITAR', 'responsable', id, ' | '.join(cambios))
        db.session.commit()
        flash('Responsable actualizado.', 'success')
        return redirect(url_for('responsables.ver', id=id))

    sectores    = Sector.query.order_by(Sector.sector).all()
    localidades = Localidad.query.order_by(Localidad.localidad).all()
    return render_template('responsables/form.html', resp=resp,
                           sectores=sectores, localidades=localidades)
