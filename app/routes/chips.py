from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required
from app.models import db, Chip, Prestadora, Servicio, Motivo, RespxChip, Responsable
from app.utils.auditoria import log as audit
from datetime import date

bp = Blueprint('chips', __name__, url_prefix='/chips')

def _es_datos(idservicio):
    s = Servicio.query.get(idservicio)
    return s and s.servicio.strip().upper() == 'DATOS'

# Asignación activa: hasta NULL, vacío o '0000-00-00' (campos legacy)
_sin_hasta_chip = db.or_(RespxChip.hasta.is_(None), RespxChip.hasta == '', RespxChip.hasta == '0000-00-00')

def _asign_activa_chip(idchip):
    return RespxChip.query.filter(RespxChip.idchip == idchip, _sin_hasta_chip).first()


@bp.route('/')
@login_required
def lista():
    filtro       = request.args.get('filtro', 'activos')
    q            = request.args.get('q', '').strip()
    prestadora_f = request.args.get('prestadora', type=int)
    tab          = request.args.get('tab', 'telefonia')

    # Identificar idservicio DATOS
    serv_datos = Servicio.query.filter(
        db.func.upper(Servicio.servicio) == 'DATOS'
    ).first()
    id_datos = serv_datos.idservicio if serv_datos else -1

    _sin_baja = db.or_(Chip.baja.is_(None), Chip.baja == '', Chip.baja == '0000-00-00')

    # Conteos para los badges de tabs
    total_datos     = Chip.query.filter(Chip.idservicio == id_datos, _sin_baja).count()
    total_telefonia = Chip.query.filter(Chip.idservicio != id_datos, _sin_baja).count()

    query = (
        db.session.query(Chip, Prestadora, Servicio)
        .join(Prestadora, Chip.idprestadora == Prestadora.idprestadora)
        .join(Servicio,   Chip.idservicio   == Servicio.idservicio)
    )

    # Filtrar por tab
    if tab == 'datos':
        query = query.filter(Chip.idservicio == id_datos)
    else:
        query = query.filter(Chip.idservicio != id_datos)

    if filtro in ('activos', 'disponibles'):
        query = query.filter(_sin_baja)
    elif filtro == 'baja':
        query = query.filter(db.not_(_sin_baja))
    if prestadora_f:
        query = query.filter(Chip.idprestadora == prestadora_f)
    if q:
        query = query.filter(
            db.or_(Chip.nrolinea.like(f'%{q}%'), Chip.nrochip.like(f'%{q}%'))
        )

    chips = query.order_by(Prestadora.prestadora, Chip.nrolinea).all()

    resultado = []
    for chip, prest, serv in chips:
        asign = _asign_activa_chip(chip.idchip)
        resp  = Responsable.query.get(asign.idresponsable) if asign else None
        if filtro == 'disponibles' and resp:
            continue
        resultado.append({'chip': chip, 'prest': prest, 'serv': serv,
                          'asign': asign, 'resp': resp})

    prestadoras = Prestadora.query.order_by(Prestadora.prestadora).all()
    return render_template('chips/lista.html',
        chips=resultado, prestadoras=prestadoras,
        filtro=filtro, q=q, prestadora_f=prestadora_f,
        tab=tab, total_datos=total_datos, total_telefonia=total_telefonia)


@bp.route('/api/activos')
@login_required
def api_chips_activos():
    """Chips activos (sin baja) para el selector de reposición."""
    _sin_baja = db.or_(Chip.baja.is_(None), Chip.baja == '', Chip.baja == '0000-00-00')
    rows = (
        db.session.query(Chip, Prestadora)
        .join(Prestadora, Chip.idprestadora == Prestadora.idprestadora)
        .filter(_sin_baja)
        .order_by(Prestadora.prestadora, Chip.nrolinea)
        .all()
    )
    resultado = []
    for chip, prest in rows:
        asign = _asign_activa_chip(chip.idchip)
        resp  = Responsable.query.get(asign.idresponsable) if asign else None
        resultado.append({
            'idchip':      chip.idchip,
            'nrolinea':    chip.nrolinea,
            'plan':        (chip.plan or '').strip(),
            'prestadora':  prest.prestadora.strip(),
            'responsable': resp.responsable.strip() if resp else None,
        })
    return jsonify(resultado)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        nrolinea     = request.form.get('nrolinea', '').strip()
        idprestadora = request.form.get('idprestadora', type=int)
        idservicio   = request.form.get('idservicio', type=int)
        nrochip      = request.form.get('nrochip', '').strip() or None
        plan         = request.form.get('plan', '').strip() or None

        if not nrolinea or not idprestadora or not idservicio:
            flash('Nro. de línea, prestadora y servicio son obligatorios.', 'danger')
        else:
            descripcion        = request.form.get('descripcion', '').strip() or None
            if not _es_datos(idservicio):
                descripcion = None
            idchip_ant         = request.form.get('idchip_reemplazado', type=int) or None
            idmotivo_repos     = request.form.get('idmotivo_reposicion', type=int) or None
            fecha_repos_str    = request.form.get('fecha_reposicion', '').strip()
            fecha_repos        = date.fromisoformat(fecha_repos_str) if fecha_repos_str else date.today()

            chip = Chip(nrolinea=nrolinea, idprestadora=idprestadora,
                        idservicio=idservicio, nrochip=nrochip, plan=plan,
                        descripcion=descripcion, idchip_reemplazado=idchip_ant)
            db.session.add(chip)
            db.session.flush()

            detalle_audit = f'Nueva línea {nrolinea} | prestadora={idprestadora} | plan={plan}'

            if idchip_ant:
                chip_ant = Chip.query.get(idchip_ant)
                if chip_ant and not chip_ant.baja:
                    chip_ant.baja     = fecha_repos
                    chip_ant.idmotivo = idmotivo_repos
                    asign_ant = _asign_activa_chip(idchip_ant)
                    if asign_ant:
                        asign_ant.hasta    = fecha_repos
                        asign_ant.idmotivo = idmotivo_repos
                        nueva_asign = RespxChip(
                            idresponsable=asign_ant.idresponsable,
                            idchip=chip.idchip,
                            desde=fecha_repos,
                            condicion='BUENO',
                            observaciones=f'Reposición de línea {chip_ant.nrolinea}',
                        )
                        db.session.add(nueva_asign)
                        resp = Responsable.query.get(asign_ant.idresponsable)
                        detalle_audit += f' | reemplaza #{idchip_ant} ({chip_ant.nrolinea}) → {resp.responsable.strip() if resp else "?"}'
                    audit('BAJA', 'chip', idchip_ant,
                          f'Reemplazado por chip #{chip.idchip} ({nrolinea}) | motivo={idmotivo_repos} | fecha={fecha_repos}')

            audit('CREAR', 'chip', chip.idchip, detalle_audit)
            db.session.commit()
            flash(f'Chip {nrolinea} agregado.', 'success')
            return redirect(url_for('chips.ver', id=chip.idchip))

    prestadoras = Prestadora.query.order_by(Prestadora.prestadora).all()
    servicios   = Servicio.query.order_by(Servicio.servicio).all()
    motivos     = Motivo.query.order_by(Motivo.motivo).all()
    return render_template('chips/form.html', chip=None,
                           prestadoras=prestadoras, servicios=servicios, motivos=motivos)


@bp.route('/<int:id>')
@login_required
def ver(id):
    chip = Chip.query.get_or_404(id)
    historial = (
        db.session.query(RespxChip, Responsable)
        .join(Responsable, RespxChip.idresponsable == Responsable.idresponsable)
        .filter(RespxChip.idchip == id)
        .order_by(RespxChip.desde.desc())
        .all()
    )
    responsables_disponibles = Responsable.query.order_by(Responsable.responsable).all()
    motivos = Motivo.query.order_by(Motivo.motivo).all()
    return render_template('chips/ver.html',
        chip=chip, historial=historial,
        motivos=motivos, responsables_disponibles=responsables_disponibles)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    chip = Chip.query.get_or_404(id)

    if request.method == 'POST':
        cambios = []

        nrolinea_nuevo = request.form.get('nrolinea', '').strip()
        if chip.nrolinea != nrolinea_nuevo:
            cambios.append(f'nrolinea: {chip.nrolinea} → {nrolinea_nuevo}')
            chip.nrolinea = nrolinea_nuevo

        idprest_nuevo = request.form.get('idprestadora', type=int)
        if chip.idprestadora != idprest_nuevo:
            cambios.append(f'prestadora: {chip.idprestadora} → {idprest_nuevo}')
            chip.idprestadora = idprest_nuevo

        idserv_nuevo = request.form.get('idservicio', type=int)
        if chip.idservicio != idserv_nuevo:
            cambios.append(f'servicio: {chip.idservicio} → {idserv_nuevo}')
            chip.idservicio = idserv_nuevo

        nrochip_nuevo = request.form.get('nrochip', '').strip() or None
        if chip.nrochip != nrochip_nuevo:
            cambios.append(f'nrochip: {chip.nrochip} → {nrochip_nuevo}')
            chip.nrochip = nrochip_nuevo

        plan_nuevo = request.form.get('plan', '').strip() or None
        if chip.plan != plan_nuevo:
            cambios.append(f'plan: {chip.plan} → {plan_nuevo}')
            chip.plan = plan_nuevo

        desc_nuevo = request.form.get('descripcion', '').strip() or None
        if not _es_datos(chip.idservicio):
            desc_nuevo = None
        if chip.descripcion != desc_nuevo:
            cambios.append(f'descripcion: {chip.descripcion} → {desc_nuevo}')
            chip.descripcion = desc_nuevo

        # ── Estado de la línea (baja / activo) ────────────────────────────────
        estado_nuevo  = request.form.get('estado', 'activo')
        baja_str      = request.form.get('fecha_baja', '').strip()
        idmotivo_baja = request.form.get('idmotivo_baja', type=int) or None

        if estado_nuevo == 'baja' and chip.baja is None:
            chip.baja     = date.fromisoformat(baja_str) if baja_str else date.today()
            chip.idmotivo = idmotivo_baja
            cambios.append(f'BAJA al {chip.baja} motivo={idmotivo_baja}')
            # Cerrar asignación activa si existe
            asign_activa = _asign_activa_chip(id)
            if asign_activa:
                asign_activa.hasta    = chip.baja
                asign_activa.idmotivo = idmotivo_baja
                cambios.append('asignación activa cerrada automáticamente')

        elif estado_nuevo == 'activo':
            # Normaliza siempre: tanto NULL como '' (string vacío del esquema legacy) → NULL real
            if chip.baja is not None:
                cambios.append(f'REACTIVACIÓN (baja anterior: {chip.baja})')
            chip.baja     = None
            chip.idmotivo = None

        if cambios:
            audit('EDITAR', 'chip', id, ' | '.join(cambios))

        db.session.commit()
        flash('Chip actualizado.', 'success')
        return redirect(url_for('chips.ver', id=id))

    prestadoras = Prestadora.query.order_by(Prestadora.prestadora).all()
    servicios   = Servicio.query.order_by(Servicio.servicio).all()
    motivos     = Motivo.query.order_by(Motivo.motivo).all()
    return render_template('chips/form.html', chip=chip,
                           prestadoras=prestadoras, servicios=servicios, motivos=motivos)


@bp.route('/<int:id>/cambiar-sim', methods=['POST'])
@login_required
def cambiar_sim(id):
    chip = Chip.query.get_or_404(id)
    if chip.baja:
        flash('El chip está dado de baja.', 'warning')
        return redirect(url_for('chips.ver', id=id))

    nrochip_nuevo  = request.form.get('nrochip_nuevo', '').strip() or None
    idmotivo       = request.form.get('idmotivo', type=int) or None
    fecha_str      = request.form.get('fecha_cambio', '').strip()
    fecha          = date.fromisoformat(fecha_str) if fecha_str else date.today()

    nrochip_viejo  = chip.nrochip
    chip.nrochip   = nrochip_nuevo
    audit('EDITAR', 'chip', id,
          f'Cambio SIM: {(nrochip_viejo or "").strip() or "sin SIM"} → {nrochip_nuevo or "sin SIM"} | motivo={idmotivo} | fecha={fecha}')
    db.session.commit()
    flash('SIM actualizado correctamente.', 'success')
    return redirect(url_for('chips.ver', id=id))


@bp.route('/<int:id>/dar-baja', methods=['POST'])
@login_required
def dar_baja(id):
    chip = Chip.query.get_or_404(id)
    if chip.baja:
        flash('El chip ya está dado de baja.', 'warning')
        return redirect(url_for('chips.ver', id=id))

    idmotivo = request.form.get('idmotivo', type=int)
    asign = _asign_activa_chip(id)
    if asign:
        asign.hasta    = date.today()
        asign.idmotivo = idmotivo

    chip.baja     = date.today()
    chip.idmotivo = idmotivo
    audit('BAJA', 'chip', id, f'motivo={idmotivo}')
    db.session.commit()
    flash('Chip dado de baja.', 'info')
    return redirect(url_for('chips.ver', id=id))


@bp.route('/<int:id>/asignar', methods=['POST'])
@login_required
def asignar(id):
    chip = Chip.query.get_or_404(id)
    if chip.baja:
        flash('No se puede asignar un chip dado de baja.', 'danger')
        return redirect(url_for('chips.ver', id=id))

    if _asign_activa_chip(id):
        flash('El chip ya tiene una asignación activa.', 'warning')
        return redirect(url_for('chips.ver', id=id))

    idresponsable = request.form.get('idresponsable', type=int)
    desde_str     = request.form.get('desde', '')
    desde         = date.fromisoformat(desde_str) if desde_str else date.today()
    condicion     = request.form.get('condicion', 'BUENO')
    observaciones = request.form.get('observaciones', '').strip() or None

    nueva = RespxChip(idresponsable=idresponsable, idchip=id, desde=desde,
                      condicion=condicion, observaciones=observaciones)
    db.session.add(nueva)
    resp = Responsable.query.get(idresponsable)
    audit('ASIGNAR', 'chip', id,
          f'→ {resp.responsable.strip() if resp else idresponsable} | desde={desde} condicion={condicion}')
    db.session.commit()
    flash('Chip asignado correctamente.', 'success')
    return redirect(url_for('chips.ver', id=id))


@bp.route('/devolver/<int:asign_id>', methods=['POST'])
@login_required
def devolver(asign_id):
    asign = RespxChip.query.get_or_404(asign_id)
    if asign.hasta:
        flash('Esta asignación ya fue cerrada.', 'warning')
        return redirect(url_for('chips.ver', id=asign.idchip))

    hasta_str      = request.form.get('hasta', '')
    idmotivo       = request.form.get('idmotivo', type=int)
    asign.hasta    = date.fromisoformat(hasta_str) if hasta_str else date.today()
    asign.idmotivo = idmotivo or None

    resp = Responsable.query.get(asign.idresponsable)
    audit('DEVOLVER', 'chip', asign.idchip,
          f'devuelto por {resp.responsable.strip() if resp else asign.idresponsable} | hasta={asign.hasta}')
    db.session.commit()
    flash('Devolución registrada.', 'success')
    return redirect(url_for('chips.ver', id=asign.idchip))
