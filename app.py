from flask import Flask, request, render_template, send_file
import os
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename

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

        root = ET.Element("reporte")
        for r in resultados:
            entrada = ET.SubElement(root, "entrada")
            ET.SubElement(entrada, "clave").text = r['clave']
            ET.SubElement(entrada, "contenido").text = r['linea']
        xml_path = os.path.join(OUTPUT_FOLDER, nombre + '.xml')
        ET.ElementTree(root).write(xml_path, encoding='utf-8', xml_declaration=True)

        return f"""
        <p>Procesado con éxito</p>
        <a href="/descargar/pdf/{nombre}.pdf">Descargar PDF</a><br>
        <a href="/descargar/xml/{nombre}.xml">Descargar XML</a>
        """

@app.route('/descargar/pdf/<nombre>')
def descargar_pdf(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

@app.route('/descargar/xml/<nombre>')
def descargar_xml(nombre):
    return send_file(os.path.join(OUTPUT_FOLDER, nombre), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
