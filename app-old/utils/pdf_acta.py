"""
Generador de Acta de Entrega de Equipo Celular - REFSA  (una sola pagina A4)
"""
from fpdf import FPDF
import os

LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'Logo_REFSA.jpg')

CLAUSULAS = [
    ("1. OBJETO",
     "REFSA entrega al responsable, en calidad de COMODATO, el equipo detallado. "
     "La empresa conserva la propiedad del equipo en todo momento."),

    ("2. USO EXCLUSIVO",
     "El equipo debera ser utilizado exclusivamente para fines laborales. "
     "Queda prohibido su uso personal, comercial o ajeno a las actividades de REFSA."),

    ("3. RESPONSABILIDAD",
     "El responsable asume plena responsabilidad por el cuidado y conservacion del equipo. "
     "En caso de dano, perdida o robo por negligencia, debera notificar al area de Sistemas "
     "y asumira el costo de reposicion o reparacion."),

    ("4. CUSTODIA",
     "Ante robo o perdida debera realizarse la denuncia policial correspondiente y "
     "presentar copia a REFSA dentro de las 48 horas de ocurrido el hecho."),

    ("5. MODIFICACIONES",
     "Queda prohibida cualquier modificacion o formateo del equipo sin autorizacion del "
     "area de Sistemas. REFSA se reserva el derecho de inspeccionarlo en cualquier momento."),

    ("6. DEVOLUCION",
     "El responsable se obliga a restituir el equipo al ser requerido por la empresa, "
     "al finalizar su relacion laboral o ante cambio de funciones."),

    ("7. VIGENCIA",
     "El presente comodato rige desde la fecha de entrega hasta que REFSA requiera "
     "la devolucion del equipo."),
]


def _formato_fecha(d):
    if not d:
        return "-"
    meses = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    return f"{d.day} de {meses[d.month-1]} de {d.year}"


class ActaPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-10)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4, 'REFSA - Recursos Energeticos Formosa S.A. - Documento de uso interno',
                  align='C')
        self.set_text_color(0, 0, 0)


def generar_acta_celular(asign, cel, resp, marca, modelo, chip=None):
    pdf = ActaPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(15, 12, 15)
    pdf.set_auto_page_break(auto=False)   # sin salto automatico
    pdf.add_page()

    W = 180   # ancho util total
    C1 = 30   # ancho columna label
    H  = 5    # altura de fila de datos
    HS = 5    # altura de titulo de seccion

    # ── ENCABEZADO ─────────────────────────────────────────────────────────
    # Logo reducido a 24mm de ancho para que no invada el area de contenido
    try:
        pdf.image(LOGO_PATH, x=15, y=8, w=24)
    except Exception:
        pass

    # Bloque de texto a la derecha del logo (a partir de x=44)
    pdf.set_xy(44, 9)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(13, 71, 161)
    pdf.cell(0, 7, 'ACTA DE ENTREGA DE EQUIPO CELULAR', ln=True)

    pdf.set_xy(44, 17)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, 'Recursos Energeticos Formosa S.A.', ln=True)

    pdf.set_xy(44, 22)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(55, 4, f'Acta N: {asign.id:05d}')
    pdf.cell(0,  4, f'Fecha: {_formato_fecha(asign.desde)}', ln=True)

    # Linea divisora a y=34 — deja margen suficiente incluso si el logo es alto
    pdf.set_draw_color(13, 71, 161)
    pdf.set_line_width(0.6)
    pdf.line(15, 34, 195, 34)
    pdf.set_y(36)

    # ── helpers ────────────────────────────────────────────────────────────
    def seccion(txt):
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(227, 242, 253)
        pdf.set_text_color(13, 71, 161)
        pdf.cell(W, HS, f'  {txt}', fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)

    def fila(label, valor, l2='', v2=''):
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(C1, H, label + ':', border='B')
        pdf.set_font('Helvetica', '', 8)
        if l2:
            ancho_v1 = 42
            pdf.cell(ancho_v1, H, str(valor), border='B')
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(26, H, l2 + ':', border='B')
            pdf.set_font('Helvetica', '', 8)
            pdf.cell(W - C1 - ancho_v1 - 26, H, str(v2), border='B', ln=True)
        else:
            pdf.cell(W - C1, H, str(valor), border='B', ln=True)

    # ── DATOS DEL EQUIPO + RESPONSABLE (dos columnas) ──────────────────────
    y_sec = pdf.get_y()
    mitad = W // 2   # 90mm cada columna

    # ---- columna izquierda: equipo ----------------------------------------
    seccion('DATOS DEL EQUIPO')
    marca_txt  = marca.marca.strip()  if marca  else '-'
    modelo_txt = modelo.modelo.strip() if modelo else cel.idmodelo
    fila('Marca',    marca_txt,                  'Modelo',   modelo_txt)
    fila('IMEI',     cel.imei,                   'N Serie',  cel.serie.strip() if cel.serie else '-')
    fila('Condicion',asign.condicion or 'BUENO', 'ID',       f'CEL-{cel.idcelular:04d}')

    if chip:
        pdf.ln(1)
        seccion('CHIP / LINEA')
        fila('Nro. Linea', chip.nrolinea,
             'Prestadora', chip.prestadora.prestadora if chip.prestadora else '-')
        fila('Servicio', chip.servicio.servicio if chip.servicio else '-',
             'Plan',     chip.plan or '-')
        fila('Nro. SIM', chip.nrochip.strip() if chip.nrochip else '-')

    pdf.ln(2)

    # ── DATOS DEL RESPONSABLE ─────────────────────────────────────────────
    seccion('DATOS DEL RESPONSABLE')
    loc = resp.localidad_rel
    sec = resp.sector_rel
    fila('Apellido y Nombre', resp.responsable.strip())
    fila('Localidad', loc.localidad.strip() if loc else '-',
         'Sector',   sec.sector.strip() if sec else '-')
    fila('Fecha de entrega', _formato_fecha(asign.desde))

    if asign.observaciones:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(C1, H, 'Observaciones:', border='B')
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(W - C1, H, str(asign.observaciones)[:80], border='B', ln=True)

    pdf.ln(2)

    # ── CLAUSULAS (2 columnas) ─────────────────────────────────────────────
    seccion('TERMINOS Y CONDICIONES')
    pdf.ln(1)

    col_w   = (W - 4) // 2    # ancho de cada columna de clausulas
    x_left  = 15
    x_right = 15 + col_w + 4

    clausulas_izq = CLAUSULAS[:4]
    clausulas_der = CLAUSULAS[4:]

    y_ini = pdf.get_y()

    # Columna izquierda
    pdf.set_x(x_left)
    for titulo, texto in clausulas_izq:
        pdf.set_x(x_left)
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_text_color(13, 71, 161)
        pdf.cell(col_w, 4, titulo, ln=True)
        pdf.set_x(x_left)
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(col_w, 3.5, texto)
        pdf.set_x(x_left)
        pdf.ln(1)

    y_fin_izq = pdf.get_y()

    # Columna derecha (vuelve al inicio Y de clausulas)
    pdf.set_xy(x_right, y_ini)
    for titulo, texto in clausulas_der:
        pdf.set_x(x_right)
        pdf.set_font('Helvetica', 'B', 7)
        pdf.set_text_color(13, 71, 161)
        pdf.cell(col_w, 4, titulo, ln=True)
        pdf.set_x(x_right)
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(col_w, 3.5, texto)
        pdf.set_x(x_right)
        pdf.ln(1)

    pdf.set_y(max(y_fin_izq, pdf.get_y()) + 2)
    pdf.set_text_color(0, 0, 0)

    # ── FIRMAS ──────────────────────────────────────────────────────────────
    pdf.set_draw_color(13, 71, 161)
    pdf.set_line_width(0.4)

    y_f = pdf.get_y() + 12
    c1x, c2x = 20, 110

    pdf.line(c1x, y_f, c1x + 70, y_f)
    pdf.line(c2x, y_f, c2x + 70, y_f)

    pdf.set_xy(c1x, y_f + 1)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(70, 4, 'ENTREGO', align='C')
    pdf.set_xy(c2x, y_f + 1)
    pdf.cell(70, 4, 'RECIBI CONFORME', align='C', ln=True)

    pdf.set_xy(c1x, y_f + 6)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(70, 3.5, 'Firma y aclaracion', align='C')
    pdf.set_xy(c2x, y_f + 6)
    pdf.cell(70, 3.5, resp.responsable.strip(), align='C', ln=True)

    pdf.set_xy(c1x, y_f + 10)
    pdf.cell(70, 3.5, 'Area de Sistemas - REFSA', align='C')
    pdf.set_xy(c2x, y_f + 10)
    pdf.cell(70, 3.5, _formato_fecha(asign.desde), align='C', ln=True)

    # Texto de conformidad
    pdf.set_y(y_f + 16)
    pdf.set_font('Helvetica', 'I', 6.5)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(W, 3.5,
        'Con la firma del presente documento el responsable declara haber leido, comprendido '
        'y aceptado en su totalidad los terminos y condiciones establecidos, asumiendo las '
        'obligaciones y responsabilidades que de el se derivan.')

    return bytes(pdf.output())
