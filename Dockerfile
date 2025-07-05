FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    poppler-utils \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libjpeg-dev \
    zlib1g-dev \
    fonts-dejavu-core \
    ghostscript \
    curl \
    unzip && \
    apt-get clean

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt

COPY . /app

EXPOSE 10000
CMD ["python3", "app.py"]
