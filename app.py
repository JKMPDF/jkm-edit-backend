import os
import uuid
import threading
import fitz  # PyMuPDF
import traceback
import io
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

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

# === THE NEW HIGH-FIDELITY "PAGE FLOW" CONVERSION FUNCTION ===
def convert_with_page_flow(pdf_path, docx_path):
    try:
        pdf_document = fitz.open(pdf_path)
        word_document = Document()
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # === THE KEY CHANGE: GET ALL ELEMENTS (TEXT AND IMAGES) AND SORT THEM ===
            # The 'sort=True' argument is crucial. It sorts blocks by their top-to-bottom position.
            blocks = page.get_text("dict", sort=True)["blocks"]
            
            for b in blocks:
                # --- CHECK THE TYPE OF ELEMENT ---
                if b['type'] == 0: # This is a text block
                    # --- Improved paragraph handling to remove extra spaces ---
                    p = word_document.add_paragraph()
                    
                    # Reconstruct the paragraph correctly
                    full_paragraph_text = ""
                    for l in b["lines"]:
                        for s in l["spans"]:
                            full_paragraph_text += s["text"]
                        # Add a space between lines, not a newline, to form a proper paragraph
                        full_paragraph_text += " "
                    
                    # Add the complete, reconstructed paragraph to the document
                    p.add_run(full_paragraph_text.strip())

                    # Apply alignment based on the block's position
                    bbox = b["bbox"]
                    page_width = page.rect.width
                    if bbox[0] > page_width * 0.6:
                        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    elif (bbox[0] > page_width * 0.35 and bbox[2] < page_width * 0.65):
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    else:
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                elif b['type'] == 1: # This is an image block
                    try:
                        # Extract the image bytes from the block
                        image_bytes = b["image"]
                        image_stream = io.BytesIO(image_bytes)
                        # Add the image in its correct position in the flow
                        word_document.add_picture(image_stream)
                    except Exception as e:
                        print(f"Could not process image in block: {e}")

            if page_num < len(pdf_document) - 1:
                word_document.add_page_break()
        
        word_document.save(docx_path)
        return True, "High-fidelity conversion successful"
    except Exception as e:
        print(f"!!! PAGE FLOW CONVERSION FAILED. Error: {e}")
        traceback.print_exc()
        return False, str(e)

# --- Worker Function for Threading (now calls the new function) ---
def process_file(job_id, pdf_path, docx_path):
    print(f"--- Starting High-Fidelity conversion for job {job_id} ---")
    jobs[job_id]['status'] = 'PROCESSING'
    success, message = convert_with_page_flow(pdf_path, docx_path)
    if success:
        jobs[job_id]['status'] = 'COMPLETED'
        print(f"--- High-Fidelity Conversion COMPLETED for job {job_id} ---")
    else:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = message
        print(f"--- High-Fidelity Conversion FAILED for job {job_id} ---")

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

# ... (the rest of the file: get_status, download_file, etc. remains the same) ...

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
