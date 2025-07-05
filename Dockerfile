# Start with a standard Python 3.10 environment
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# --- Install Tesseract and its English language pack ---
# This runs as the 'root' user to install system software
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng

# Copy our requirements file into the container
COPY requirements.txt .

# Install the Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of our application code into the container
COPY . .

# Tell the container to run our Gunicorn server when it starts
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
