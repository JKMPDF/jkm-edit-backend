import os
import uuid
import threading
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- BASIC APP SETUP ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://jkmpdf.github.io"}})

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

jobs = {}

# --- THE CORE CONVERSION LOGIC ---
def convert_pdf_with_layout(pdf_path, docx_path):
    try:
        pdf_document = fitz.open(pdf_path)
        word_document = Document()
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_width = page.rect.width
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_BLOCKS)["blocks"]
            for b in blocks:
                if "lines" in b:
                    full_text = ""
                    for l in b["lines"]:
                        for s in l["spans"]:
                            full_text += s["text"]
                        full_text += "\n"
                    p = word_document.add_paragraph()
                    bbox = b["bbox"]
                    if bbox[0] > page_width * 0.6:
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    elif (page_width * 0.3 < bbox[0]) and (bbox[2] < page_width * 0.7):
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    else:
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.add_run(full_text.strip())
            if page_num < len(pdf_document) - 1:
                word_document.add_page_break()
        word_document.save(docx_path)
        return True, "Conversion successful"
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False, str(e)

# --- WORKER FUNCTION FOR THREADING ---
def process_file(job_id, pdf_path, docx_path):
    jobs[job_id]['status'] = 'PROCESSING'
    success, message = convert_pdf_with_layout(pdf_path, docx_path)
    if success:
        jobs[job_id]['status'] = 'COMPLETED'
    else:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = message

# --- API ENDPOINTS ---
@app.route('/api/ocr/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    if file:
        job_id = str(uuid.uuid4())
        filename = f"{job_id}.pdf"
        output_filename = f"{job_id}.docx"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        docx_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        file.save(pdf_path)
        jobs[job_id] = {'status': 'PENDING', 'pdf_path': pdf_path, 'docx_path': docx_path}
        thread = threading.Thread(target=process_file, args=(job_id, pdf_path, docx_path))
        thread.start()
        return jsonify({"jobId": job_id})

@app.route('/api/ocr/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({"error": "Job not found"}), 404
    response = {"status": job['status']}
    if job['status'] == 'FAILED': response['error'] = job.get('error', 'An unknown error occurred.')
    return jsonify(response)

@app.route('/api/ocr/download/<job_id>', methods=['GET'])
def download_file(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'COMPLETED': return jsonify({"error": "File not ready or job failed"}), 404
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], f"{job_id}.docx", as_attachment=True, download_name=f"converted_{job_id}.docx")
    except FileNotFoundError:
        return jsonify({"error": "File not found."}), 404

@app.route('/')
def index():
    return "JKM Edit Backend is running!"

if __name__ == '__main__':
    app.run(debug=True)
