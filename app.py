
from flask import Flask, request, render_template, send_file
import os
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import KeepTogether
from reportlab.platypus import PageBreak
from collections import Counter

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    archivo = request.files['archivo']
    if archivo:
        nombre = secure_filename(archivo.filename)
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

        # Programas instalados
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

        # Estados finales
        estados = ['SUCCESS', 'FAILED', 'STUCK']
        estado_detectado = next((e for e in estados if any(e in line for line in contenido)), "No detectado")

        # Palabras clave
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

        # PDF Gen
        pdf_path = os.path.join(OUTPUT_FOLDER, nombre + '.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        flow = []

        flow.append(Paragraph("<b>Reporte detallado</b>", styles['Title']))
        flow.append(Spacer(1, 12))

        flow.append(Paragraph("<b>Información General</b>", styles['Heading2']))
        flow.append(Paragraph(f"<b>Archivo procesado:</b> {nombre}", styles['Normal']))
        flow.append(Paragraph(f"<b>Total de líneas analizadas:</b> {len(contenido)}", styles['Normal']))
        if path_line != "-":
            flow.append(Paragraph(f"<b>Path del archivo:</b> {path_line}", styles['Normal']))
            flow.append(Paragraph(f"<b>Program installed:</b> {prog_str}", styles['Normal']))
            flow.append(Paragraph(f"<b>Programas abiertos:</b> {abiertos_str}", styles['Normal']))
        flow.append(Spacer(1, 12))

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

        if netdata_metrica:
            netdata_title = Paragraph("<b>Métricas con Netdata</b>", styles['Heading2'])
            netdata_tabla = Table([["Métrica", "Valor"]] + netdata_metrica)
            netdata_tabla.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT')
            ]))

            flow.append(PageBreak())  # forzando 
            flow.append(netdata_title)
            flow.append(Spacer(1, 6))
            flow.append(netdata_tabla)

        else:
            flow.append(Paragraph("<b>Métricas con Netdata</b>", styles['Heading2']))
            flow.append(Paragraph("No se encontraron métricas Netdata en el archivo.", styles['Normal']))

        #Status Test
        flow.append(Spacer(1, 12))
        flow.append(Paragraph("<b>Test Completion Status</b>", styles['Heading2']))

        # Buscar estado en contenido
        estados = ['SUCCESS', 'FAILED', 'STUCK']
        estado_detectado = next((e for e in estados if any(e in line for line in contenido)), "No detectado")
        flow.append(Paragraph(estado_detectado, styles['Normal']))

        doc.build(flow)

        return render_template('resultado.html', nombre=nombre)

@app.route('/descargar/pdf/<nombre>')
def descargar_pdf(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

@app.route('/descargar/xml/<nombre>')
def descargar_xml(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
