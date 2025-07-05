FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    && apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 10000
CMD ["python", "app.py"]
