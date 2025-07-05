import os
import uuid
import threading
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- NEW: Define the base directory of the application ---
# This makes our file paths absolute and reliable on Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- BASIC APP SETUP ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://jkmpdf.github.io"}})

# --- CONFIGURATION (Now using absolute paths) ---
# This joins the base directory path with our folder names
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# --- NEW: Ensure directories exist on startup ---
# This is a fallback in case the build command has issues.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


jobs = {}

# --- THE CORE CONVERSION LOGIC (No changes here, but included for completeness) ---
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
        # --- MODIFIED: More detailed error logging ---
        print(f"!!! CONVERSION THREAD FAILED for job. Error: {e}")
        import traceback
        traceback.print_exc() # This will print the full error to the logs
        return False, str(e)

# --- WORKER FUNCTION FOR THREADING ---
def process_file(job_id, pdf_path, docx_path):
    # --- MODIFIED: Add a print statement to see if the thread starts ---
    print(f"--- Starting conversion thread for job {job_id} ---")
    jobs[job_id]['status'] = 'PROCESSING'
    success, message = convert_pdf_with_layout(pdf_path, docx_path)
    if success:
        jobs[job_id]['status'] = 'COMPLETED'
        print(f"--- Conversion COMPLETED for job {job_id} ---")
    else:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = message
        print(f"--- Conversion FAILED for job {job_id} ---")

# --- API ENDPOINTS (No changes here, but included for completeness) ---
@app.route('/api/ocr/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    if file:
        job__id = str(uuid.uuid4())
        filename = f"{job_id}.pdf"
        output_filename = f"{job_id}.docx"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        docx_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        file.save(pdf_path)
        jobs[job_id] = {'status': 'PENDING', 'pdf_path': pdf_path, 'docx_path': docx_path}
        # --- MODIFIED: Add a print statement before starting thread ---
        print(f"File saved to {pdf_path}. Starting thread for job {job_id}.")
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
