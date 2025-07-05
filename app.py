import os
import uuid
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pdf2image import convert_from_path
import pytesseract
from docx import Document
from docx.shared import Inches
from PIL import Image

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}

def clean_text(text):
    return ''.join(c if c.isprintable() else '' for c in text)

# ========== OCR Processing ==========
def process_ocr(job_id, pdf_path, docx_path):
    try:
        jobs[job_id]['status'] = 'PROCESSING'
        images = convert_from_path(pdf_path, dpi=300)
        doc = Document()
        for img in images:
            text = pytesseract.image_to_string(img, lang='eng')
            doc.add_paragraph(clean_text(text))
        doc.save(docx_path)
        jobs[job_id]['status'] = 'COMPLETED'
    except Exception as e:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = str(e)

# ========== Photocopy (Image-based) ==========
def process_photocopy(job_id, pdf_path, docx_path):
    try:
        jobs[job_id]['status'] = 'PROCESSING'
        images = convert_from_path(pdf_path, dpi=200)
        doc = Document()
        for i, img in enumerate(images):
            img_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{i}.jpg")
            img.save(img_path)
            doc.add_picture(img_path, width=Inches(6.0))
        doc.save(docx_path)
        jobs[job_id]['status'] = 'COMPLETED'
    except Exception as e:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = str(e)

# ========== Common Upload Handler ==========
def handle_upload(process_func):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    job_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.pdf")
    docx_path = os.path.join(OUTPUT_FOLDER, f"{job_id}.docx")

    file.save(pdf_path)
    jobs[job_id] = {'status': 'PENDING', 'pdf_path': pdf_path, 'docx_path': docx_path}

    threading.Thread(target=process_func, args=(job_id, pdf_path, docx_path)).start()
    return jsonify({"jobId": job_id})

@app.route('/api/ocr/upload', methods=['POST'])
def upload_ocr():
    return handle_upload(process_ocr)

@app.route('/api/photocopy/upload', methods=['POST'])
def upload_photocopy():
    return handle_upload(process_photocopy)

@app.route('/api/ocr/status/<job_id>')
@app.route('/api/photocopy/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"status": job['status'], "error": job.get('error')})

@app.route('/api/ocr/download/<job_id>')
@app.route('/api/photocopy/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'COMPLETED':
        return jsonify({"error": "Not ready"}), 400
    return send_from_directory(OUTPUT_FOLDER, f"{job_id}.docx", as_attachment=True)

@app.route('/')
def home():
    return "✅ JKM Edit OCR & Photocopy Backend is Running"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
