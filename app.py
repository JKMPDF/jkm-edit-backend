import os
import uuid
import threading
import subprocess
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

def process_file(job_id, pdf_path, docx_path):
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

@app.route('/')
def index():
    return "JKM Edit OCR Backend is running."

@app.route('/api/ocr/upload', methods=['POST'])
def upload_file():
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
    thread = threading.Thread(target=process_file, args=(job_id, pdf_path, docx_path))
    thread.start()

    return jsonify({"jobId": job_id})

@app.route('/api/ocr/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"status": job['status'], "error": job.get('error')})

@app.route('/api/ocr/download/<job_id>', methods=['GET'])
def download_file(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'COMPLETED':
        return jsonify({"error": "File not ready or job failed"}), 404
    return send_from_directory(OUTPUT_FOLDER, f"{job_id}.docx", as_attachment=True, download_name=f"converted_{job_id}.docx")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
