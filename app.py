from flask import Flask, request, render_template, send_file
import os
from flask import Flask, request, render_template, send_file, session, redirect, url_for
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from collections import Counter

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.secret_key = 'clave_secreta_para_sesion'  # Necesario para usar session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    tipo_reporte = request.form.get('tipo_reporte')
    secciones = request.form.getlist('secciones')

    archivo = request.files['archivo']
    if archivo:
        nombre = secure_filename(archivo.filename)
        _, extension = os.path.splitext(nombre)
        if extension.lower() not in ['.txt', '.log']:
            return render_template('resultado.html', error="Ese formato de archivo no está permitido para convertir con este sistema.", nombre=None)

        ruta = os.path.join(UPLOAD_FOLDER, nombre)
        archivo.save(ruta)

        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.readlines()

        # Procesar Netdata dinámico desde === NETDATA ===
        netdata_metrica = []
        netdata_activa = False
        for line in contenido:
            line = line.strip()
            if "=== NETDATA ===" in line:
                netdata_activa = True
                continue
            if netdata_activa:
                if line == "" or "=" not in line:
                    break
                try:
                    k, v = line.split("=", 1)
                    netdata_metrica.append([k.strip(), v.strip()])
                except ValueError:
                    continue

        raw_data = {}
        path_line = "-"
        for line in contenido:
            if "details" in line.lower():
                parts = line.split("Details", 1)
                if len(parts) > 1:
                    valores = parts[1].strip()
                    for par in valores.split(";"):
                        if "=" in par:
                            k, v = par.strip().split("=", 1)
                            raw_data[k.strip().lower()] = v.strip()
            if "Logs collected and stored at" in line:
                if "/var/" in line:
                    path_line = line[line.index("/var/"):].strip()

        programas = []
        for line in contenido:
            if "INSTALL" in line:
                partes = line.split()
                if "INSTALL" in partes:
                    idx = partes.index("INSTALL")
                    if idx > 0:
                        programas.append(partes[idx - 1])
        prog_str = ", ".join(programas) if programas else "-"

        programas_abiertos = []
        for line in contenido:
            if "OPEN" in line:
                partes = line.split()
                if "OPEN" in partes:
                    idx = partes.index("OPEN")
                    if idx < len(partes) - 1:
                        programas_abiertos.append(partes[idx + 1])
        abiertos_str = ", ".join(programas_abiertos) if programas_abiertos else "-"

        estados = ['SUCCESS', 'FAILED', 'STUCK']
        estado_detectado = next((e for e in estados if any(e in line for line in contenido)), "No detectado")

        alias_claves = {
            "os_version": ["os_version", "osversion"],
            "ifwi_version": ["ifwi_version", "ifwiversion"],
            "kernel_version": ["kernel_version", "kernelversion"],
            "bios_version": ["bios_version", "biosversion"],
            "vm_config": ["vm_config", "vmconfig"],
            "bmc": ["bmc"]
        }

        data = {}
        for clave, variantes in alias_claves.items():
            for variante in variantes:
                if variante in raw_data:
                    data[clave] = raw_data[variante]
                    break
            else:
                data[clave] = "-"

        claves = ['ERROR', 'SUCCESS', 'WARNING']
        resultados = []
        for linea in contenido:
            for clave in claves:
                if clave in linea:
                    resultados.append({'clave': clave, 'linea': linea.strip()})
                    break

        pdf_path = os.path.join(OUTPUT_FOLDER, nombre + '.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        flow = []

        flow.append(Paragraph("<b>Reporte detallado</b>", styles['Title']))
        flow.append(Spacer(1, 12))

        mostrar_basico = tipo_reporte == "especifico" and len(secciones) == 0
        incluir = lambda campo: tipo_reporte == "detallado" or campo in secciones

        if incluir("lineas") or incluir("path") or incluir("instalados"):
            flow.append(Paragraph("<b>Información General</b>", styles['Heading2']))
        if incluir("lineas"):
            flow.append(Paragraph(f"<b>Total de líneas analizadas:</b> {len(contenido)}", styles['Normal']))
        if incluir("path"):
            flow.append(Paragraph(f"<b>Path del archivo:</b> {path_line}", styles['Normal']))
        if incluir("instalados"):
            flow.append(Paragraph(f"<b>Program installed:</b> {prog_str}", styles['Normal']))
            flow.append(Paragraph(f"<b>Programas abiertos:</b> {abiertos_str}", styles['Normal']))
        flow.append(Spacer(1, 12))

        if tipo_reporte == "detallado" or tipo_reporte == "especifico":
            flow.append(Paragraph("<b>Resumen de ocurrencias por palabra clave</b>", styles['Heading2']))
            contador = Counter([r['clave'] for r in resultados])
            tabla_resumen = Table([["Palabra clave", "Ocurrencias"]] + [[k, str(v)] for k, v in contador.items()])
            tabla_resumen.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
            ]))
            flow.append(tabla_resumen)
            flow.append(Spacer(1, 12))

            flow.append(Paragraph("<b>Detalles de coincidencias encontradas</b>", styles['Heading2']))
            for r in resultados:
                flow.append(Paragraph(f"[{r['clave']}] {r['linea']}", styles['Normal']))
                flow.append(Spacer(1, 4))

            flow.append(Spacer(1, 12))
            flow.append(Paragraph("<b>Ingredient Information</b>", styles['Heading2']))
            campos_info = list(alias_claves.keys())
            tabla_info = [["Campo", "Valor"]] + [[campo, data.get(campo, "-")] for campo in campos_info]
            tabla = Table(tabla_info)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ]))
            flow.append(tabla)
            flow.append(Spacer(1, 12))

            flow.append(Paragraph("<b>Anomalías detectadas</b>", styles['Heading2']))
            alertas = [line.strip() for line in contenido if 'WARNING' in line or 'overheat' in line or 'latency' in line]
            if any(path_line in a for a in alertas):
                alertas = [a for a in alertas if path_line not in a]
            if alertas:
                for alerta in alertas:
                    flow.append(Paragraph(alerta, styles['Normal']))
            else:
                flow.append(Paragraph("No se detectaron anomalías en el archivo.", styles['Normal']))
            flow.append(Spacer(1, 12))

        if incluir("netdata"):
            netdata_title = Paragraph("<b>Métricas con Netdata</b>", styles['Heading2'])
            if netdata_metrica:
                netdata_tabla = Table([["Métrica", "Valor"]] + netdata_metrica)
                netdata_tabla.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT')
                ]))
                bloque = [netdata_title, Spacer(1, 4), netdata_tabla]
                if len(netdata_metrica) < 10:
                    flow.append(KeepTogether(bloque))
                else:
                    flow.extend(bloque)
            else:
                flow.append(netdata_title)
                flow.append(Paragraph("No se encontraron métricas Netdata en el archivo.", styles['Normal']))

        flow.append(Spacer(1, 12))
        flow.append(Paragraph("<b>Test Completion Status</b>", styles['Heading2']))
        flow.append(Paragraph(estado_detectado, styles['Normal']))

        # Guardar opciones seleccionadas en sesión
        session['tipo_reporte'] = tipo_reporte
        session['secciones'] = secciones

        doc.build(flow)
        return render_template('resultado.html', nombre=nombre)

@app.route('/descargar/pdf/<nombre>')
def descargar_pdf(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

@app.route('/descargar/xml/<nombre>')
def descargar_xml(nombre):
    ruta = os.path.join(UPLOAD_FOLDER, nombre)
    if not os.path.exists(ruta):
        return "Archivo original no encontrado", 404

    tipo_reporte = session.get('tipo_reporte', 'detallado')
    secciones = session.get('secciones', [])

    with open(ruta, 'r', encoding='utf-8') as f:
        contenido = f.readlines()

    incluir = lambda campo: tipo_reporte == "detallado" or campo in secciones

    root = ET.Element("reporte")
    ET.SubElement(root, "archivo").text = nombre

    if incluir("lineas"):
        ET.SubElement(root, "total_lineas").text = str(len(contenido))

    if incluir("path"):
        for line in contenido:
            if "Logs collected and stored at" in line and "/var/" in line:
                path = line[line.index("/var/"):].strip()
                ET.SubElement(root, "path_archivo").text = path
                break

    if incluir("instalados"):
        instalados = []
        abiertos = []
        for line in contenido:
            if "INSTALL" in line:
                partes = line.split()
                if "INSTALL" in partes:
                    idx = partes.index("INSTALL")
                    if idx > 0:
                        instalados.append(partes[idx - 1])
            if "OPEN" in line:
                partes = line.split()
                if "OPEN" in partes:
                    idx = partes.index("OPEN")
                    if idx < len(partes) - 1:
                        abiertos.append(partes[idx + 1])
        ET.SubElement(root, "programas_instalados").text = ", ".join(instalados) if instalados else "-"
        ET.SubElement(root, "programas_abiertos").text = ", ".join(abiertos) if abiertos else "-"

    if incluir("netdata"):
        netdata = ET.SubElement(root, "netdata")
        netdata_activa = False
        for line in contenido:
            line = line.strip()
            if "=== NETDATA ===" in line:
                netdata_activa = True
                continue
            if netdata_activa:
                if line == "" or "=" not in line:
                    break
                try:
                    k, v = line.split("=", 1)
                    metrica = ET.SubElement(netdata, "metrica", nombre=k.strip())
                    metrica.text = v.strip()
                except ValueError:
                    continue

    # Test completion status siempre se incluye
    estados = ['SUCCESS', 'FAILED', 'STUCK']
    estado = next((e for e in estados if any(e in l for l in contenido)), "No detectado")
    ET.SubElement(root, "estado_final").text = estado

    # Guardar XML
    xml_path = os.path.join(OUTPUT_FOLDER, nombre + ".xml")
    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding='utf-8', xml_declaration=True)

    return send_file(xml_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
