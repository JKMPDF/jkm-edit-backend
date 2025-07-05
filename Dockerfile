# ✅ Use Ubuntu base
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ✅ Install LibreOffice and dependencies
RUN apt-get update && apt-get install -y \
    libreoffice \
    python3 \
    python3-pip \
    python3-setuptools \
    fonts-dejavu \
    curl \
    unzip \
    && apt-get clean

# ✅ Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# ✅ Copy your code
COPY . /app

# ✅ Expose the correct port
EXPOSE 10000

# ✅ Start the app
CMD ["python3", "app.py"]

git add .
git commit -m "Fix Dockerfile for Render LibreOffice"
git push origin main
