FROM node:20-slim

WORKDIR /app

# Install OpenSSL
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install

COPY . .

# Create certs directory and generate certificates
RUN mkdir -p certs && \
    node scripts/generate-certs.js

EXPOSE 5173

CMD ["npm", "run", "dev"]