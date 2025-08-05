# Backend Build Stage
FROM python:3.10-slim AS backend-build
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# GPT4All Model Download Stage
FROM python:3.10-slim AS model-download
WORKDIR /app
RUN pip install gpt4all>=2.5.0
# Pre-download models during build
RUN python3 -c "
from gpt4all import GPT4All
import os

# Create models directory
os.makedirs('/app/models', exist_ok=True)

# Download models
print('Downloading orca-mini-3b model...')
model1 = GPT4All('orca-mini-3b-gguf2-q4_0.gguf', model_path='/app/models')
print('orca-mini-3b downloaded successfully')

print('Downloading Meta-Llama-3-8B model...')
model2 = GPT4All('Meta-Llama-3-8B-Instruct.Q4_0.gguf', model_path='/app/models')
print('Meta-Llama-3-8B downloaded successfully')

# Verify models are downloaded
import glob
models = glob.glob('/app/models/*.gguf')
print(f'Downloaded models: {models}')
"

# Final Stage
FROM python:3.10-slim
WORKDIR /app

# Create user and group with same IDs as host infadm user
ARG USER_ID=1003
ARG GROUP_ID=1002
ARG USERNAME=infadm
ARG GROUP_NAME=aimsys

RUN groupadd -g $GROUP_ID $GROUP_NAME && \
    useradd -u $USER_ID -g $GROUP_NAME -m -s /bin/bash $USERNAME

# Copy frontend build from frontend stage
COPY --from=frontend-build /app/dist /app/frontend/dist

# Copy backend from backend stage
COPY --from=backend-build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY backend /app/backend

# Copy pre-downloaded models
COPY --from=model-download /app/models /app/models

# Install system dependencies
RUN apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false && \
    apt-get install -y \
        ansible \
        openssh-client \
        sshpass \
        procps \
        sudo \
        postgresql-client \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories with proper ownership
RUN mkdir -p /home/users/$USERNAME/.ssh \
             /app/fixfiles/AllFts \
             /app/logs \
             /tmp/ansible-ssh \
             /app/ssh-keys && \
    chmod 700 /home/users/$USERNAME/.ssh && \
    chmod -R 777 /tmp/ansible-ssh && \
    chown -R $USERNAME:$GROUP_NAME /app && \
    chown -R $USERNAME:$GROUP_NAME /home/users/$USERNAME

# Copy entrypoint script and set permissions
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown $USERNAME:$GROUP_NAME /entrypoint.sh

# Give sudo access to infadm user
RUN echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to the infadm user
USER $USERNAME

# Set environment variables
ENV HOME=/home/users/$USERNAME
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV ANSIBLE_HOST_KEY_CHECKING=False
ENV ANSIBLE_SSH_CONTROL_PATH=/tmp/ansible-ssh/%h-%p-%r
ENV ANSIBLE_SSH_CONTROL_PATH_DIR=/tmp/ansible-ssh
ENV PYTHONUNBUFFERED=1
ENV LOG_FILE_PATH=/app/logs/application.log
ENV DEPLOYMENT_LOGS_DIR=/app/logs
# GPT4All configuration
ENV GPT4ALL_MODEL_PATH=/app/models
ENV GPT4ALL_MODEL=orca-mini-3b-gguf2-q4_0.gguf

# Expose ports
EXPOSE 5000

# Start with entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "backend/app.py"]
