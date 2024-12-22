FROM python:3.11-slim

WORKDIR /app

# Install OpenSSL
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make certificate generation script executable and generate certificates
RUN chmod +x scripts/generate-certs.py && \
    python scripts/generate-certs.py

EXPOSE 27182

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "27182", "--ssl-keyfile", "certs/key.pem", "--ssl-certfile", "certs/cert.pem"]