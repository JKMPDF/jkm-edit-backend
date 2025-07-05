FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install LibreOffice and dependencies
RUN apt-get update && apt-get install -y \
    libreoffice \
    python3 \
    python3-pip \
    fonts-dejavu \
    curl unzip && \
    apt-get clean

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app files
COPY . /app

EXPOSE 10000
CMD ["python3", "app.py"]
