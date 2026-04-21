# Dev-mode Dockerfile: Vite dev server with HMR. Used by docker-compose.yml.
# Certs come from a mounted volume (the host runs
# `node scripts/generate-certs.js` once before bringing compose up).
FROM node:20-slim

# Install curl for HEALTHCHECK + openssl for the certs fallback path.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# node:20-slim already provisions a non-root `node` user (uid 1000).
# Make sure the working dir is owned by it so npm install doesn't fight
# permissions with bind-mounted host files.
RUN chown -R node:node /app
USER node

COPY --chown=node:node package*.json ./
RUN npm install

COPY --chown=node:node . .

EXPOSE 5173

# The dev server doesn't serve HTTP on /healthz; hit the root path over
# HTTPS and accept self-signed certs. Generous start-period because
# Vite's first bundle can take 10-20s on a cold cache.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -kfsS https://localhost:5173/ || exit 1

CMD ["npm", "run", "dev"]
