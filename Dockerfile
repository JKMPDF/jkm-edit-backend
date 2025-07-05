# Dockerfile
FROM ubuntu:22.04

# Set environment
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y libreoffice python3 python3-pip && \
    apt-get clean

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy your app files
COPY . /app

# Expose port
EXPOSE 10000

# Run the app
CMD ["python3", "app.py"]
