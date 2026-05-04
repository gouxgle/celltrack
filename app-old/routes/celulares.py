from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response, jsonify
from flask_login import login_required
from app.models import db, Celular, Marca, Modelo, Motivo, CelxResp, Responsable, RespxChip, Chip
from app.utils.auditoria import log as audit
from datetime import date
import traceback as _tb

bp = Blueprint('celulares', __name__, url_prefix='/celulares')

_sin_baja  = lambda col: db.or_(col.is_(None), col == '', col == '0000-00-00')
_sin_hasta = lambda col: db.or_(col.is_(None), col == '', col == '0000-00-00')


# ── Lista ──────────────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def lista():
    try:
        filtro  = request.args.get('filtro', 'activos')
        q       = request.args.get('q', '').strip()
        marca_f = request.args.get('marca', type=int)
        query = (
            db.session.query(Celular, Marca, Modelo)
            .join(Marca, Celular.idmarca == Marca.idmarca)
            .outerjoin(Modelo, (Celular.idmarca == Modelo.idmarca) & (Celular.idmodelo == Modelo.idmodelo))
        )
        if filtro in ('activos', 'disponibles'):
            query = query.filter(_sin_baja(Celular.baja))
        elif filtro == 'baja':
            query = query.filter(db.not_(_sin_baja(Celular.baja)))
        if marca_f:
            query = query.filter(Celular.idmarca == marca_f)
        if q:
            query = query.filter(db.or_(Celular.imei.like(f'%{q}%'), Celular.serie.like(f'%{q}%')))
        celulares = query.order_by(Marca.marca, Modelo.modelo).all()
        resultado = []
        for cel, marca, modelo in celulares:
            asign = (CelxResp.query
                     .filter(CelxResp.idcelular == cel.idcelular,
                             _sin_hasta(CelxResp.hasta))
                     .first())
            resp  = Responsable.query.get(asign.idresponsable) if asign else None
            if filtro == 'disponibles' and resp:
                continue
            resultado.append({'cel': cel, 'marca': marca, 'modelo': modelo, 'asign': asign, 'resp': resp})
        marcas = Marca.query.order_by(Marca.marca).all()
        return render_template('celulares/lista.html',
            celulares=resultado, marcas=marcas, filtro=filtro, q=q, marca_f=marca_f)
    except Exception:
        return f"<pre>{_tb.format_exc()}</pre>", 500


# ── Nuevo ──────────────────────────────────────────────────────────────────────

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        imei     = request.form.get('imei', '').strip()
        serie    = request.form.get('serie', '').strip()
        idmarca  = request.form.get('idmarca', type=int)
        idmodelo = request.form.get('idmodelo', '').strip()

        if not imei or not idmarca or not idmodelo:
            flash('IMEI, marca y modelo son obligatorios.', 'danger')
        else:
            cel = Celular(imei=imei, serie=serie or None, idmarca=idmarca, idmodelo=idmodelo)
            db.session.add(cel)
            db.session.flush()
            audit('CREAR', 'celular', cel.idcelular,
                  f'IMEI={imei} | serie={serie} | marca={idmarca} | modelo={idmodelo}')

            # ── Asignación opcional al crear ───────────────────────────────────
            idresponsable = request.form.get('idresponsable', type=int)
            if idresponsable:
                idchip        = request.form.get('idchip', type=int) or None
                desde_str     = request.form.get('desde', '')
                desde         = date.fromisoformat(desde_str) if desde_str else date.today()
                condicion     = request.form.get('condicion', 'BUENO')
                observaciones = request.form.get('observaciones', '').strip() or None

                # Reemplazar teléfono viejo si el chip ya tiene uno activo
                if idchip:
                    old_asign = CelxResp.query.filter(CelxResp.idchip == idchip, _sin_hasta(CelxResp.hasta)).first()
                    if old_asign and old_asign.idcelular != cel.idcelular:
                        idmotivo_reemplazo = request.form.get('idmotivo_reemplazo', type=int) or None
                        old_cel = Celular.query.get(old_asign.idcelular)
                        old_asign.hasta    = desde
                        old_asign.idmotivo = idmotivo_reemplazo
                        if old_cel:
                            old_cel.baja     = desde
                            old_cel.idmotivo = idmotivo_reemplazo
                            audit('BAJA', 'celular', old_cel.idcelular,
                                  f'reemplazado por IMEI={imei} | motivo={idmotivo_reemplazo}')

                asign = CelxResp(idresponsable=idresponsable, idcelular=cel.idcelular,
                                 idchip=idchip, desde=desde,
                                 condicion=condicion, observaciones=observaciones)
                db.session.add(asign)
                db.session.flush()
                resp = Responsable.query.get(idresponsable)
                audit('ASIGNAR', 'celular', cel.idcelular,
                      f'→ {resp.responsable.strip() if resp else idresponsable} | chip={idchip} | desde={desde} | condicion={condicion}')
                db.session.commit()
                return redirect(url_for('celulares.acta_pdf', asign_id=asign.id))

            db.session.commit()
            flash(f'Celular {imei} agregado.', 'success')
            return redirect(url_for('celulares.ver', id=cel.idcelular))

    marcas        = Marca.query.order_by(Marca.marca).all()
    responsables  = Responsable.query.order_by(Responsable.responsable).all()
    motivos       = Motivo.query.order_by(Motivo.motivo).all()
    return render_template('celulares/form.html', cel=None,
                           marcas=marcas, responsables=responsables, motivos=motivos)


# ── Ver ────────────────────────────────────────────────────────────────────────

@bp.route('/<int:id>')
@login_required
def ver(id):
    cel    = Celular.query.get_or_404(id)
    marca  = Marca.query.get(cel.idmarca)
    modelo = Modelo.query.filter_by(idmarca=cel.idmarca, idmodelo=cel.idmodelo).first()
    historial = (
        db.session.query(CelxResp, Responsable)
        .join(Responsable, CelxResp.idresponsable == Responsable.idresponsable)
        .filter(CelxResp.idcelular == id)
        .order_by(CelxResp.desde.desc())
        .all()
    )
    responsables_libres = (
        Responsable.query
        .filter(~Responsable.idresponsable.in_(
            db.session.query(CelxResp.idresponsable).filter(_sin_hasta(CelxResp.hasta))
        ))
        .order_by(Responsable.responsable).all()
    )
    motivos = Motivo.query.order_by(Motivo.motivo).all()
    return render_template('celulares/ver.html',
        cel=cel, marca=marca, modelo=modelo,
        historial=historial, motivos=motivos, responsables_libres=responsables_libres)


# ── Editar ─────────────────────────────────────────────────────────────────────

@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    cel = Celular.query.get_or_404(id)
    if request.method == 'POST':
        cambios = []
        for attr, label, getter in [
            ('imei',    'imei',   lambda: request.form.get('imei','').strip()),
            ('serie',   'serie',  lambda: request.form.get('serie','').strip() or None),
            ('idmarca', 'marca',  lambda: request.form.get('idmarca', type=int)),
            ('idmodelo','modelo', lambda: request.form.get('idmodelo','').strip()),
        ]:
            nuevo_val = getter()
            if str(getattr(cel, attr) or '') != str(nuevo_val or ''):
                cambios.append(f'{label}: {getattr(cel, attr)} → {nuevo_val}')
                setattr(cel, attr, nuevo_val)
        if cambios:
            audit('EDITAR', 'celular', id, ' | '.join(cambios))
        db.session.commit()
        flash('Celular actualizado.', 'success')
        return redirect(url_for('celulares.ver', id=id))
    marcas = Marca.query.order_by(Marca.marca).all()
    return render_template('celulares/form.html', cel=cel, marcas=marcas,
                           responsables=[], motivos=[])


# ── Dar de baja ────────────────────────────────────────────────────────────────

@bp.route('/<int:id>/dar-baja', methods=['POST'])
@login_required
def dar_baja(id):
    cel = Celular.query.get_or_404(id)
    if cel.baja:
        flash('El celular ya está dado de baja.', 'warning')
        return redirect(url_for('celulares.ver', id=id))
    idmotivo = request.form.get('idmotivo', type=int)
    asign = CelxResp.query.filter(CelxResp.idcelular == id, _sin_hasta(CelxResp.hasta)).first()
    if asign:
        asign.hasta    = date.today()
        asign.idmotivo = idmotivo
    cel.baja     = date.today()
    cel.idmotivo = idmotivo
    audit('BAJA', 'celular', id, f'IMEI={cel.imei} | motivo={idmotivo}')
    db.session.commit()
    flash('Celular dado de baja.', 'info')
    return redirect(url_for('celulares.ver', id=id))


# ── Asignar (desde ver.html) ───────────────────────────────────────────────────

@bp.route('/<int:id>/asignar', methods=['POST'])
@login_required
def asignar(id):
    cel = Celular.query.get_or_404(id)
    if cel.baja:
        flash('No se puede asignar un celular dado de baja.', 'danger')
        return redirect(url_for('celulares.ver', id=id))
    if CelxResp.query.filter(CelxResp.idcelular == id, _sin_hasta(CelxResp.hasta)).first():
        flash('El celular ya tiene una asignación activa.', 'warning')
        return redirect(url_for('celulares.ver', id=id))

    idresponsable = request.form.get('idresponsable', type=int)
    idchip        = request.form.get('idchip', type=int) or None
    desde_str     = request.form.get('desde', '')
    desde         = date.fromisoformat(desde_str) if desde_str else date.today()
    condicion     = request.form.get('condicion', 'BUENO')
    observaciones = request.form.get('observaciones', '').strip() or None

    # Reemplazar teléfono viejo si el chip ya tiene uno activo
    if idchip:
        old_asign = CelxResp.query.filter(CelxResp.idchip == idchip, _sin_hasta(CelxResp.hasta)).first()
        if old_asign and old_asign.idcelular != id:
            idmotivo_reemplazo = request.form.get('idmotivo_reemplazo', type=int) or None
            old_cel = Celular.query.get(old_asign.idcelular)
            old_asign.hasta    = desde
            old_asign.idmotivo = idmotivo_reemplazo
            if old_cel:
                old_cel.baja     = desde
                old_cel.idmotivo = idmotivo_reemplazo
                audit('BAJA', 'celular', old_cel.idcelular,
                      f'reemplazado | motivo={idmotivo_reemplazo}')

    nueva = CelxResp(idresponsable=idresponsable, idcelular=id, idchip=idchip,
                     desde=desde, condicion=condicion, observaciones=observaciones)
    db.session.add(nueva)
    db.session.flush()
    resp = Responsable.query.get(idresponsable)
    audit('ASIGNAR', 'celular', id,
          f'→ {resp.responsable.strip() if resp else idresponsable} | chip={idchip} | desde={desde} | condicion={condicion}')
    db.session.commit()
    flash('Celular asignado correctamente.', 'success')
    return redirect(url_for('celulares.acta_pdf', asign_id=nueva.id))


# ── Devolver ───────────────────────────────────────────────────────────────────

@bp.route('/devolver/<int:asign_id>', methods=['POST'])
@login_required
def devolver(asign_id):
    asign = CelxResp.query.get_or_404(asign_id)
    if asign.hasta:
        flash('Esta asignación ya fue cerrada.', 'warning')
        return redirect(url_for('celulares.ver', id=asign.idcelular))
    hasta_str      = request.form.get('hasta', '')
    idmotivo       = request.form.get('idmotivo', type=int)
    asign.hasta    = date.fromisoformat(hasta_str) if hasta_str else date.today()
    asign.idmotivo = idmotivo or None
    resp = Responsable.query.get(asign.idresponsable)
    audit('DEVOLVER', 'celular', asign.idcelular,
          f'devuelto por {resp.responsable.strip() if resp else asign.idresponsable} | hasta={asign.hasta}')
    db.session.commit()
    flash('Devolución registrada.', 'success')
    return redirect(url_for('celulares.ver', id=asign.idcelular))


# ── AJAX: modelos por marca ────────────────────────────────────────────────────

@bp.route('/modelos/<int:idmarca>')
@login_required
def modelos_por_marca(idmarca):
    modelos = Modelo.query.filter_by(idmarca=idmarca).order_by(Modelo.modelo).all()
    return jsonify([{'idmodelo': m.idmodelo, 'modelo': m.modelo.strip()} for m in modelos])


# ── AJAX: chips activos de un responsable ─────────────────────────────────────

@bp.route('/api/responsable/<int:idresp>/chips')
@login_required
def chips_de_responsable(idresp):
    sin_baja = db.or_(Chip.baja.is_(None), Chip.baja == '', Chip.baja == '0000-00-00')
    rows = (
        db.session.query(RespxChip, Chip)
        .join(Chip, RespxChip.idchip == Chip.idchip)
        .filter(RespxChip.idresponsable == idresp, _sin_hasta(RespxChip.hasta))
        .filter(sin_baja)
        .all()
    )
    return jsonify([
        {'idchip': c.idchip, 'nrolinea': c.nrolinea, 'plan': (c.plan or '').strip()}
        for _, c in rows
    ])


# ── AJAX: celular activo vinculado a un chip ───────────────────────────────────

@bp.route('/api/chip/<int:idchip>/celular-activo')
@login_required
def celular_activo_en_chip(idchip):
    asign = CelxResp.query.filter(CelxResp.idchip == idchip, _sin_hasta(CelxResp.hasta)).first()
    if not asign:
        return jsonify({'encontrado': False})
    cel   = Celular.query.get(asign.idcelular)
    marca = Marca.query.get(cel.idmarca) if cel else None
    return jsonify({
        'encontrado': True,
        'idcelular':  cel.idcelular,
        'imei':       cel.imei,
        'marca':      marca.marca.strip() if marca else '?',
    })


# ── PDF Acta de entrega ────────────────────────────────────────────────────────

@bp.route('/acta/<int:asign_id>.pdf')
@login_required
def acta_pdf(asign_id):
    from app.utils.pdf_acta import generar_acta_celular
    asign  = CelxResp.query.get_or_404(asign_id)
    cel    = Celular.query.get_or_404(asign.idcelular)
    resp   = Responsable.query.get_or_404(asign.idresponsable)
    marca  = Marca.query.get(cel.idmarca)
    modelo = Modelo.query.filter_by(idmarca=cel.idmarca, idmodelo=cel.idmodelo).first()
    # Usa el chip vinculado directamente; si no, busca cualquier activo del responsable
    if asign.idchip:
        chip = Chip.query.get(asign.idchip)
    else:
        chip_asign = (RespxChip.query
                      .join(Chip, RespxChip.idchip == Chip.idchip)
                      .filter(RespxChip.idresponsable == resp.idresponsable,
                              _sin_hasta(RespxChip.hasta),
                              _sin_baja(Chip.baja))
                      .first())
        chip = Chip.query.get(chip_asign.idchip) if chip_asign else None
    pdf_bytes = generar_acta_celular(asign, cel, resp, marca, modelo, chip)
    response  = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=acta_celular_{asign_id}.pdf'
    return response
