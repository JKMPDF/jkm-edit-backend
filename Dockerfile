# Use Ubuntu base
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libreoffice \
    python3 \
    python3-pip \
    python3-setuptools \
    fonts-dejavu \
    curl \
    unzip \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app

# Expose the port used in app.py
EXPOSE 10000

# Start the app
CMD ["python3", "app.py"]
