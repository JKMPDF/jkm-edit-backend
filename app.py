import subprocess

def process_file(job_id, pdf_path, docx_path):
    try:
        jobs[job_id]['status'] = 'PROCESSING'

        # LibreOffice outputs to same folder as PDF
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'docx',
            '--outdir', OUTPUT_FOLDER,
            pdf_path
        ], check=True)

        jobs[job_id]['status'] = 'COMPLETED'
    except Exception as e:
        jobs[job_id]['status'] = 'FAILED'
        jobs[job_id]['error'] = str(e)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
