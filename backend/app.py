
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import subprocess
import os
import time
import threading
import json

app = Flask(__name__, static_folder='../dist')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Mock FT data
ft_data = {
    "ft-001": {
        "name": "FT Alpha",
        "description": "Core platform services",
        "files": [
            "config/app.config.json",
            "config/db.config.json",
            "src/modules/core/main.py",
            "src/modules/core/utils.py",
            "src/modules/api/routes.py",
            "src/modules/api/middleware.py",
            "tests/unit/test_core.py"
        ]
    },
    "ft-002": {
        "name": "FT Beta",
        "description": "User authentication and identity",
        "files": [
            "auth/login.py",
            "auth/register.py",
            "auth/middleware.py",
            "templates/login.html",
            "templates/register.html"
        ]
    }
}

# Mock VM data
vm_data = [
    {"id": "vm-001", "name": "web-server-01", "ip": "192.168.1.101", "environment": "dev", "status": "online"},
    {"id": "vm-002", "name": "web-server-02", "ip": "192.168.1.102", "environment": "dev", "status": "online"},
    {"id": "vm-003", "name": "app-server-01", "ip": "192.168.1.103", "environment": "staging", "status": "online"}
]

# API routes
@app.route('/api/ft', methods=['GET'])
def get_feature_teams():
    return jsonify([
        {"id": ft_id, "name": data["name"], "description": data["description"]}
        for ft_id, data in ft_data.items()
    ])

@app.route('/api/ft/<ft_id>/files', methods=['GET'])
def get_ft_files(ft_id):
    if ft_id in ft_data:
        return jsonify(ft_data[ft_id]["files"])
    return jsonify({"error": "Feature team not found"}), 404

@app.route('/api/targets', methods=['GET'])
def get_targets():
    return jsonify(vm_data)

@app.route('/api/deploy', methods=['POST'])
def deploy():
    data = request.json
    ft_id = data.get('ftId')
    files = data.get('files', [])
    targets = data.get('targets', [])
    
    if not ft_id or not files or not targets:
        return jsonify({"error": "Missing required parameters"}), 400
    
    deployment_id = f"dep-{int(time.time())}"
    
    # Start deployment in background thread
    thread = threading.Thread(target=run_deployment, args=(deployment_id, ft_id, files, targets))
    thread.daemon = True
    thread.start()
    
    return jsonify({"deploymentId": deployment_id, "status": "started"})

def run_deployment(deployment_id, ft_id, files, targets):
    """Simulate running an Ansible deployment with real-time logs"""
    
    # Initial log
    log_message(deployment_id, f"Deployment started for FT: {ft_id}")
    log_message(deployment_id, f"Files selected: {', '.join(files)}")
    log_message(deployment_id, f"Target VMs: {', '.join(targets)}")
    
    # Simulate connection to VMs
    time.sleep(2)
    log_message(deployment_id, "Connecting to target VMs...")
    
    # Simulate preparing files
    time.sleep(2)
    log_message(deployment_id, "Preparing files for deployment...")
    
    # Simulate running Ansible playbook
    time.sleep(1)
    log_message(deployment_id, "Running ansible playbook...")
    
    # Sample Ansible output
    ansible_output = """
PLAY [Deploy files] ************************************************************

TASK [Gathering Facts] *********************************************************
ok: [192.168.1.101]
ok: [192.168.1.102]

TASK [Ensure target directory exists] ******************************************
changed: [192.168.1.101]
changed: [192.168.1.102]

TASK [Copy files to targets] ***************************************************
changed: [192.168.1.101]
changed: [192.168.1.102]
    """
    
    for line in ansible_output.strip().split('\n'):
        time.sleep(0.2)
        log_message(deployment_id, line)
    
    # Simulate copying files
    time.sleep(1)
    log_message(deployment_id, "Copying files to target VMs...")
    
    # Success logs for each target
    for target in targets:
        time.sleep(1)
        log_message(deployment_id, f"✓ Successfully deployed to {target}", status="success")
    
    # Final success message
    time.sleep(1)
    log_message(deployment_id, "✓ Deployment completed successfully!", status="success")

def log_message(deployment_id, message, status="info"):
    """Send log message via websocket"""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    formatted_message = message
    if status == "success":
        formatted_message = f"<span class=\"ansi-green-fg\">[{timestamp}] {message}</span>"
    elif status == "error":
        formatted_message = f"<span class=\"ansi-red-fg\">[{timestamp}] {message}</span>"
    elif status == "warning":
        formatted_message = f"<span class=\"ansi-yellow-fg\">[{timestamp}] {message}</span>"
    else:
        formatted_message = f"[{timestamp}] {message}"
    
    socketio.emit('deployment_log', {
        'deploymentId': deployment_id,
        'message': formatted_message
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
