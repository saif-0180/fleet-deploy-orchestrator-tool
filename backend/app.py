import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.services import file_service, sql_service, systemctl_service
from backend.services import user_service
from backend.utils import security
from backend.config import config

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = config.SECRET_KEY

# ======================= FILE OPERATIONS =======================
@app.route('/api/files/read', methods=['POST'])
@security.auth_required
def read_file():
    data = request.get_json()
    path = data.get('path')
    if not path:
        return jsonify({'error': 'Path is required'}), 400
    try:
        content = file_service.read_file(path)
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/write', methods=['POST'])
@security.auth_required
def write_file():
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')
    if not path or content is None:
        return jsonify({'error': 'Path and content are required'}), 400
    try:
        file_service.write_file(path, content)
        return jsonify({'message': 'File written successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/execute', methods=['POST'])
@security.auth_required
def execute_file():
    data = request.get_json()
    path = data.get('path')
    if not path:
        return jsonify({'error': 'Path is required'}), 400
    try:
        result = file_service.execute_file(path)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= SQL OPERATIONS =======================
@app.route('/api/sql/execute', methods=['POST'])
@security.auth_required
def execute_sql():
    data = request.get_json()
    connection_string = data.get('connection_string')
    query = data.get('query')
    if not connection_string or not query:
        return jsonify({'error': 'Connection string and query are required'}), 400
    try:
        result = sql_service.execute_query(connection_string, query)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= SYSTEMCTL OPERATIONS =======================
@app.route('/api/systemctl/status', methods=['POST'])
@security.auth_required
def systemctl_status():
    data = request.get_json()
    service_name = data.get('service_name')
    if not service_name:
        return jsonify({'error': 'Service name is required'}), 400
    try:
        status = systemctl_service.get_service_status(service_name)
        return jsonify({'status': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systemctl/start', methods=['POST'])
@security.auth_required
def systemctl_start():
    data = request.get_json()
    service_name = data.get('service_name')
    if not service_name:
        return jsonify({'error': 'Service name is required'}), 400
    try:
        systemctl_service.start_service(service_name)
        return jsonify({'message': f'{service_name} started successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systemctl/stop', methods=['POST'])
@security.auth_required
def systemctl_stop():
    data = request.get_json()
    service_name = data.get('service_name')
    if not service_name:
        return jsonify({'error': 'Service name is required'}), 400
    try:
        systemctl_service.stop_service(service_name)
        return jsonify({'message': f'{service_name} stopped successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systemctl/restart', methods=['POST'])
@security.auth_required
def systemctl_restart():
    data = request.get_json()
    service_name = data.get('service_name')
    if not service_name:
        return jsonify({'error': 'Service name is required'}), 400
    try:
        systemctl_service.restart_service(service_name)
        return jsonify({'message': f'{service_name} restarted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= USER MANAGEMENT =======================
@app.route('/api/users/create', methods=['POST'])
@security.auth_required
@security.admin_required
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    try:
        user_service.create_user(username, password, role)
        return jsonify({'message': 'User created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/list', methods=['GET'])
@security.auth_required
@security.admin_required
def list_users():
    try:
        users = user_service.list_users()
        # Remove passwords from the user list
        users_without_passwords = [{'id': user['id'], 'username': user['username'], 'role': user['role']} for user in users]
        return jsonify({'users': users_without_passwords})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/delete/<int:user_id>', methods=['DELETE'])
@security.auth_required
@security.admin_required
def delete_user(user_id):
    try:
        user_service.delete_user(user_id)
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/update/<int:user_id>', methods=['PUT'])
@security.auth_required
@security.admin_required
def update_user(user_id):
    data = request.get_json()
    role = data.get('role')
    if not role:
        return jsonify({'error': 'Role is required'}), 400
    try:
        user_service.update_user(user_id, role)
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= AUTHENTICATION =======================
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    try:
        token = user_service.login(username, password)
        if token:
            return jsonify({'token': token})
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify', methods=['POST'])
@security.auth_required
def verify():
    # If we reach here, the token is valid
    return jsonify({'message': 'Token is valid'})

# ======================= DEPLOYMENT HISTORY =======================
@app.route('/api/deployments', methods=['GET'])
@security.auth_required
def list_deployments():
    try:
        deployments = file_service.list_deployments()
        return jsonify({'deployments': deployments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments/save', methods=['POST'])
@security.auth_required
def save_deployment():
    data = request.get_json()
    name = data.get('name')
    content = data.get('content')
    if not name or not content:
        return jsonify({'error': 'Name and content are required'}), 400
    try:
        file_service.save_deployment(name, content)
        return jsonify({'message': 'Deployment saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments/load/<string:name>', methods=['GET'])
@security.auth_required
def load_deployment(name):
    try:
        content = file_service.load_deployment(name)
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments/delete/<string:name>', methods=['DELETE'])
@security.auth_required
def delete_deployment(name):
    try:
        file_service.delete_deployment(name)
        return jsonify({'message': 'Deployment deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update the logs summarize route
@app.route('/api/logs/summarize', methods=['POST'])
def summarize_logs():
    try:
        data = request.get_json()
        logs = data.get('logs', [])
        deployment_id = data.get('deployment_id')
        
        if not logs:
            return jsonify({'success': False, 'error': 'No logs provided'})
        
        print(f"Received {len(logs)} logs for analysis")
        
        # Use the new AI-powered analyzer
        from backend.services.ai_log_analyzer import AILogAnalyzer
        
        analyzer = AILogAnalyzer()
        analysis = analyzer.analyze_logs(logs, deployment_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"Error in summarize_logs: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
