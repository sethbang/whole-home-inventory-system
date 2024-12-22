# Deploying WHIS on Synology NAS

This guide explains how to deploy the Whole Home Inventory System (WHIS) on a Synology NAS at 192.168.1.122.

## Prerequisites

1. Synology NAS with Docker package installed
2. Git installed on the NAS (can be installed via Package Center)
3. Docker Compose installed on the NAS

## Setup Steps

1. Ensure you have the correct permissions:
   - Log into DSM web interface
   - Go to Control Panel > User & Group
   - Add your user to the 'docker' group:
     ```bash
     sudo synogroup --add docker $(whoami)
     ```
   - Log out and log back in for the changes to take effect

2. Clone the repository to your NAS:
```bash
git clone https://github.com/sethbang/whole-home-inventory-system.git
cd /volume1/docker/whole-home-inventory-system
```

2. Create the following directory structure on your NAS for persistent storage:
```bash
mkdir -p /volume1/docker/whole-home-inventory-system/database
mkdir -p /volume1/docker/whole-home-inventory-system/uploads
mkdir -p /volume1/docker/whole-home-inventory-system/backups
```

3. Create a `docker-compose.nas.yml` file with the following content:
```yaml
services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "27182:27182"
    environment:
      - DATABASE_URL=sqlite:///./app.db
      - CORS_ORIGINS=http://192.168.1.122:5173
    volumes:
      - /volume1/docker/whole-home-inventory-system/database:/app/database
      - /volume1/docker/whole-home-inventory-system/uploads:/app/backend/uploads
      - /volume1/docker/whole-home-inventory-system/backups:/app/backend/backups
    networks:
      - whis-network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:80"
    depends_on:
      - backend
    networks:
      - whis-network
    restart: unless-stopped

networks:
  whis-network:
    driver: bridge
```

4. Update the frontend nginx configuration (`frontend/nginx.conf`):
```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:27182;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Deployment

There are two ways to deploy the application:

### Method 1: Command Line

1. SSH into your Synology NAS or use the terminal in DSM.

2. Navigate to the project directory:
```bash
cd /volume1/docker/whole-home-inventory-system
```

3. Build and start the containers (choose one of these methods):
```bash
# If you've added your user to the docker group:
docker-compose -f docker-compose.nas.yml up -d --build

# If you need to use sudo:
sudo docker-compose -f docker-compose.nas.yml up -d --build
```

### Method 2: Synology Docker UI

You can also use the Synology DSM interface:

1. Open DSM in your web browser
2. Go to Package Center > Docker
3. Open Docker
4. Go to Registry
5. Import both Dockerfiles:
   - Click "Add File" and select the backend Dockerfile
   - Repeat for the frontend Dockerfile
6. Go to Containers
7. Create both containers using the settings from docker-compose.nas.yml:
   - Use the same ports (27182:27182 for backend, 5173:80 for frontend)
   - Add the environment variables for the backend
   - Map the volumes as specified
   - Enable auto-restart

4. Verify the deployment:
- Backend API should be accessible at: `http://192.168.1.122:27182`
- Frontend interface should be accessible at: `http://192.168.1.122:5173`

## Maintenance

### Viewing Logs
```bash
# If you've added your user to the docker group:
docker-compose -f docker-compose.nas.yml logs

# If you need to use sudo:
sudo docker-compose -f docker-compose.nas.yml logs

# View specific service logs (with sudo if needed)
docker-compose -f docker-compose.nas.yml logs backend
docker-compose -f docker-compose.nas.yml logs frontend
```

### Updating the Application
1. Pull the latest changes:
```bash
git pull origin main
```

2. Rebuild and restart the containers:
```bash
# If you've added your user to the docker group:
docker-compose -f docker-compose.nas.yml up -d --build

# If you need to use sudo:
sudo docker-compose -f docker-compose.nas.yml up -d --build
```

### Managing Containers
```bash
# Stop containers (with sudo if needed)
docker-compose -f docker-compose.nas.yml down

# Remove containers and networks (with sudo if needed)
docker-compose -f docker-compose.nas.yml down --volumes
```

### Backup Data
The following directories contain persistent data:
- `/volume1/docker/whole-home-inventory-system/database`: SQLite database
- `/volume1/docker/whole-home-inventory-system/uploads`: Uploaded files
- `/volume1/docker/whole-home-inventory-system/backups`: System backups

Regular backups of these directories are recommended using Synology's built-in backup tools.

## Troubleshooting

1. Docker Permission Issues:
   - Error "permission denied while trying to connect to the Docker daemon socket":
     ```bash
     # Add your user to the docker group
     sudo synogroup --add docker $(whoami)
     # Log out and log back in, or alternatively:
     su - $(whoami)
     ```
   - If still having issues, use `sudo` with Docker commands or use the Synology Docker UI

2. If the frontend can't connect to the backend:
   - Verify both containers are running: `docker-compose -f docker-compose.nas.yml ps` (with sudo if needed)
   - Check backend logs for errors: `docker-compose -f docker-compose.nas.yml logs backend`
   - Ensure the CORS_ORIGINS environment variable matches your NAS IP

3. If volumes are not accessible:
   - Verify the directories exist on the NAS:
     ```bash
     ls -la /volume1/docker/whole-home-inventory-system/
     ```
   - Fix permissions if needed:
     ```bash
     sudo chown -R $(whoami):docker /volume1/docker/whole-home-inventory-system/
     sudo chmod -R 755 /volume1/docker/whole-home-inventory-system/
     ```
   - Ensure the Docker user has access to these directories

4. For other issues:
   - Check container logs (use sudo if needed)
   - Verify network connectivity between containers
   - Ensure ports are not being used by other services on the NAS
   - Check DSM Docker UI for container status and resource usage