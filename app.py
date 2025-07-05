import os
import uuid
import threading
import fitz  # PyMuPDF
import traceback
import pytesseract
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from docx import Document

# --- Basic App Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["https://jkmpdf.github.io", "https://www.jkmedit.in", "https://jkmedit.in"]}})

# --- Configuration ---
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}

# === NEW AND IMPROVED OCR CONVERSION FUNCTION ===
def convert_pdf_with_ocr(pdf_path, docx_path):
    try:
        pdf_document = fitz.open(pdf_path)
        word_document = Document()
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # Render page to an image (pixmap)
            pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Use Tesseract to do OCR on the image
            text = pytesseract.image_to_string(img, lang='eng')
            
            # Add the extracted text to the Word document
            word_document.add_paragraph(text)
            if page_num < len(pdf_document) - 1:
                word_document.add_page_break()
        
        word_document.save(docx_path)
        return True, "OCR Conversion successful"
    except Exception as e:
        print(f"!!! OCR CONVERSION THREAD FAILED. Error: {e}")
        traceback.print_exc()
        return False, str(e)

# --- Worker Function for Threading ---
def process_file(job_id, pdf_path, docx_path):
    print(f"--- Starting OCR conversion thread for job {job_id} ---")
    jobs[job_id]['status'] = 'PROCESSING'
    # Call the new OCR function
    success, message = convert_pdf_with_ocr(pdf_path, docx_path)
    if success:
        jobs[job_id]['status'] = 'COMPLETED'
        print(f"--- OCR Conversion COMPLETED for job {job_id} ---")
    else:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = message
        print(f"--- OCR Conversion FAILED for job {job_id} ---")

# --- API Endpoints (No changes from here down) ---
@app.route('/api/ocr/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    if file:
        job_id = str(uuid.uuid4())
        filename = f"{job_id}.pdf"
        output_filename = f"{job_id}.docx"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        docx_path = os.path.join(OUTPUT_FOLDER, output_filename)
        file.save(pdf_path)
        jobs[job_id] = {'status': 'PENDING', 'pdf_path': pdf_path, 'docx_path': docx_path}
        print(f"File saved to {pdf_path}. Starting thread for job {job_id}.")
        thread = threading.Thread(target=process_file, args=(job_id, pdf_path, docx_path))
        thread.start()
        return jsonify({"jobId": job_id})
    return jsonify({"error": "An unknown error occurred"}), 500

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
        return send_from_directory(OUTPUT_FOLDER, f"{job_id}.docx", as_attachment=True, download_name=f"converted_{job_id}.docx")
    except FileNotFoundError:
        return jsonify({"error": "File not found."}), 404

@app.route('/')
def index():
    return "JKM Edit Backend is running!"

if __name__ == '__main__':
    app.run(debug=True)
