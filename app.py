import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pdf2image import convert_from_path
import pytesseract
from docx import Document
from PIL import Image

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["https://jkmpdf.github.io", "https://www.jkmedit.in", "https://jkmedit.in"]}})

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}

# === OCR Word: Editable ===
def process_ocr(job_id, pdf_path, docx_path):
    try:
        jobs[job_id]['status'] = 'PROCESSING'
        images = convert_from_path(pdf_path, dpi=300)
        doc = Document()
        for img in images:
            text = pytesseract.image_to_string(img, lang='eng')
            doc.add_paragraph(text)
        doc.save(docx_path)
        jobs[job_id]['status'] = 'COMPLETED'
    except Exception as e:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = str(e)

@app.route('/api/ocr/upload', methods=['POST'])
def upload_ocr():
    return handle_upload(process_ocr, "ocr")

# === Photocopy-style Word ===
def process_photocopy(job_id, pdf_path, docx_path):
    try:
        jobs[job_id]['status'] = 'PROCESSING'
        images = convert_from_path(pdf_path, dpi=300)
        doc = Document()
        for img in images:
            img_path = f"{UPLOAD_FOLDER}/{job_id}_page.jpg"
            img.save(img_path)
            doc.add_picture(img_path, width=docx.shared.Inches(6.2))
        doc.save(docx_path)
        jobs[job_id]['status'] = 'COMPLETED'
    except Exception as e:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = str(e)

@app.route('/api/photocopy/upload', methods=['POST'])
def upload_photocopy():
    return handle_upload(process_photocopy, "photocopy")

# === Common Upload Logic ===
def handle_upload(process_func, job_type):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    job_id = str(uuid.uuid4())
    filename = f"{job_id}.pdf"
    output_filename = f"{job_id}.docx"
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    docx_path = os.path.join(OUTPUT_FOLDER, output_filename)

    file.save(pdf_path)
    jobs[job_id] = {'status': 'PENDING', 'pdf_path': pdf_path, 'docx_path': docx_path}
    thread = threading.Thread(target=process_func, args=(job_id, pdf_path, docx_path))
    thread.start()

    return jsonify({"jobId": job_id})

# === Status & Download ===
@app.route('/api/ocr/status/<job_id>')
@app.route('/api/photocopy/status/<job_id>')
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"status": job['status'], "error": job.get('error')})

@app.route('/api/ocr/download/<job_id>')
@app.route('/api/photocopy/download/<job_id>')
def download_file(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'COMPLETED':
        return jsonify({"error": "File not ready or job failed"}), 404
    return send_from_directory(OUTPUT_FOLDER, f"{job_id}.docx", as_attachment=True, download_name=f"{job_id}.docx")

@app.route('/')
def home():
    return "JKM Edit OCR & Photocopy backend is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
