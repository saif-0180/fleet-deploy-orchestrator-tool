# Dockerfile - Application image built on top of base
FROM your-registry/fleet-orchestrator-base:latest

WORKDIR /app

# Switch to root temporarily for file operations
USER root

# Frontend Build Stage (can be done separately if needed)
FROM node:18-alpine AS frontend-build
WORKDIR /app
COPY package*.json ./
RUN npm install && npm install -g vite
COPY . .
RUN vite build

# Back to main application build
FROM your-registry/fleet-orchestrator-base:latest
WORKDIR /app

# Switch to root temporarily for copying files
USER root

# Copy frontend build
COPY --from=frontend-build /app/dist /app/frontend/dist

# Copy backend application code
COPY backend /app/backend

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fix ownership of new files
RUN chown -R infadm:aimsys /app && \
    chown infadm:aimsys /entrypoint.sh

# Switch back to infadm user
USER infadm

# Set Flask app environment
ENV FLASK_APP=backend/app.py

# Expose ports
EXPOSE 5000

# Start with entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "backend/app.py"]
