
# Use Node.js as the base image for building the React app
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the frontend code and build it
COPY . .
RUN npm run build

# Use Python for the Flask backend
FROM python:3.9-slim

WORKDIR /app

# Install Ansible
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ansible \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Flask backend requirements and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built frontend from the previous stage
COPY --from=frontend-builder /app/dist /app/dist

# Copy the Flask backend code
COPY backend /app/backend

# Expose port for the application
EXPOSE 5000

# Command to run the application
CMD ["python", "backend/app.py"]
