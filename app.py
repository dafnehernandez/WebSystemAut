from flask import Flask, request, render_template, send_file
import os
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
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

        claves = ['ERROR', 'SUCCESS', 'WARNING']
        resultados = []
        for linea in contenido:
            for clave in claves:
                if clave in linea:
                    resultados.append({'clave': clave, 'linea': linea.strip()})
                    break

        pdf_path = os.path.join(OUTPUT_FOLDER, nombre + '.pdf')
        c = canvas.Canvas(pdf_path)
        y = 800
        for r in resultados:
            c.drawString(50, y, f"[{r['clave']}] {r['linea']}")
            y -= 15
        c.save()

        pdf_path = os.path.join(OUTPUT_FOLDER, nombre + '.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        flow = []

        # Título
        flow.append(Paragraph(f"<b>Reporte de Análisis de Log</b>", styles['Title']))
        flow.append(Spacer(1, 12))

        # Información general
        flow.append(Paragraph(f"<b>Archivo procesado:</b> {nombre}", styles['Normal']))
        flow.append(Paragraph(f"<b>Total de líneas analizadas:</b> {len(contenido)}", styles['Normal']))
        flow.append(Spacer(1, 12))

        # Contar ocurrencias
        contador = Counter([r['clave'] for r in resultados])

        # Tabla resumen
        flow.append(Paragraph("<b>Resumen de ocurrencias por palabra clave:</b>", styles['Heading2']))
        tabla = Table([["Palabra clave", "Ocurrencias"]] + [[k, str(v)] for k, v in contador.items()])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        flow.append(tabla)
        flow.append(Spacer(1, 12))

        # Detalles línea por línea
        flow.append(Paragraph("<b>Detalles de coincidencias encontradas:</b>", styles['Heading2']))
        for r in resultados:
            line = f"[{r['clave']}] {r['linea']}"
            flow.append(Paragraph(line, styles['Normal']))
            flow.append(Spacer(1, 6))

        doc.build(flow)

        root = ET.Element("reporte")
        for r in resultados:
            entrada = ET.SubElement(root, "entrada")
            ET.SubElement(entrada, "clave").text = r['clave']
            ET.SubElement(entrada, "contenido").text = r['linea']
        xml_path = os.path.join(OUTPUT_FOLDER, nombre + '.xml')
        ET.ElementTree(root).write(xml_path, encoding='utf-8', xml_declaration=True)

        return render_template('resultado.html', nombre=nombre)

@app.route('/descargar/pdf/<nombre>')
def descargar_pdf(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

@app.route('/descargar/xml/<nombre>')
def descargar_xml(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
