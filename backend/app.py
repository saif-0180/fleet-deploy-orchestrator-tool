from flask import Flask, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
import json
import os
import uuid
import threading
import time
from datetime import datetime
import subprocess
import logging
import base64

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store active deployments
deployments = {}

# Deployment history
DEPLOYMENT_HISTORY_FILE = 'deployment_history.json'

# Load deployment history from file
def load_deployment_history():
    try:
        with open(DEPLOYMENT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error("Error decoding deployment history JSON. Starting with an empty history.")
        return []

# Save deployment history to file
def save_deployment_history(history):
    with open(DEPLOYMENT_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# Initialize deployment history
deployment_history = load_deployment_history()

# Store the save_deployment_history function in the app's config
app.config['save_deployment_history'] = lambda entry: save_deployment_history(deployment_history + [entry])
app.config['deployments'] = deployments

def execute_file_copy(ft_number, file_path, target_vm, target_path, target_user, deployment_id):
    """Execute file copy operation"""
    deployment = deployments.get(deployment_id)
    if not deployment:
        return False
    
    try:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Copying {file_path} from FT {ft_number} to {target_vm}:{target_path} as {target_user}")
        
        # Simulate file copy operation
        time.sleep(2)
        
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully copied {file_path} to {target_vm}")
        return True
        
    except Exception as e:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        return False

def execute_sql_command(ft_number, sql_file, db_connection, db_user, db_password_encoded, deployment_id):
    """Execute SQL command"""
    deployment = deployments.get(deployment_id)
    if not deployment:
        return False
    
    try:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Executing SQL file: {sql_file}")
        
        # Decode base64 password
        db_password = base64.b64decode(db_password_encoded).decode('utf-8') if db_password_encoded else ''
        
        # Simulate SQL execution
        time.sleep(3)
        
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully executed SQL file: {sql_file}")
        return True
        
    except Exception as e:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        return False

def execute_systemctl_command(ft_number, service, operation, target_vm, deployment_id):
    """Execute systemctl command"""
    deployment = deployments.get(deployment_id)
    if not deployment:
        return False
    
    try:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Performing {operation} on {service} on {target_vm}")
        
        # Simulate systemctl execution
        time.sleep(2)
        
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully performed {operation} on {service} on {target_vm}")
        return True
        
    except Exception as e:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        return False

def execute_command(ft_number, command, target_vm, deployment_id):
    """Execute command"""
    deployment = deployments.get(deployment_id)
    if not deployment:
        return False
    
    try:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Executing command: {command} on {target_vm}")
        
        # Simulate command execution
        time.sleep(5)
        
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully executed command: {command} on {target_vm}")
        return True
        
    except Exception as e:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        return False

def execute_rollback(ft_number, file_path, target_vm, deployment_id):
    """Execute rollback operation"""
    deployment = deployments.get(deployment_id)
    if not deployment:
        return False
    
    try:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Rolling back {file_path} on {target_vm} from FT {ft_number}")
        
        # Simulate rollback operation
        time.sleep(4)
        
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully rolled back {file_path} on {target_vm}")
        return True
        
    except Exception as e:
        deployment['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        return False

def execute_template_background(deployment_id, template_data, ft_number, logged_in_user):
    """Execute template deployment in background thread"""
    try:
        logger.info(f"Starting template deployment {deployment_id} for {ft_number}")
        
        # Get the shared deployments dictionary
        deployments = current_app.config.get('deployments', {})
        
        if deployment_id not in deployments:
            logger.error(f"Deployment {deployment_id} not found in deployments")
            return
        
        deployments[deployment_id]['status'] = 'running'
        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting template deployment for {ft_number}")
        
        steps = template_data.get('steps', [])
        total_steps = len(steps)
        
        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Total steps to execute: {total_steps}")
        
        # Execute steps in order
        for step in sorted(steps, key=lambda x: x.get('order', 0)):
            if deployments[deployment_id]['status'] != 'running':
                break
            
            step_type = step.get('type')
            deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Executing step {step.get('order')}: {step.get('description')}")
            
            if step_type == 'file_deployment':
                # Execute file deployment
                files = step.get('files', [])
                target_path = step.get('targetPath', '/home/users/abpwrk1/pbin/app')
                target_user = step.get('targetUser', 'abpwrk1')
                target_vms = step.get('targetVMs', [])
                
                for vm in target_vms:
                    for file in files:
                        success = execute_file_copy(ft_number, file, vm, target_path, target_user, deployment_id)
                        if not success:
                            deployments[deployment_id]['status'] = 'failed'
                            deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment failed at step {step.get('order')}")
                            return
            
            elif step_type == 'sql_deployment':
                # Execute SQL deployment
                files = step.get('files', [])
                db_connection = step.get('dbConnection')
                db_user = step.get('dbUser')
                db_password = step.get('dbPassword', '')
                
                for sql_file in files:
                    success = execute_sql_command(ft_number, sql_file, db_connection, db_user, db_password, deployment_id)
                    if not success:
                        deployments[deployment_id]['status'] = 'failed'
                        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment failed at step {step.get('order')}")
                        return
            
            elif step_type == 'service_restart':
                # Execute service restart
                service = step.get('service', 'docker.service')
                operation = step.get('operation', 'restart')
                target_vms = step.get('targetVMs', [])
                
                for vm in target_vms:
                    success = execute_systemctl_command(ft_number, service, operation, vm, deployment_id)
                    if not success:
                        deployments[deployment_id]['status'] = 'failed'
                        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment failed at step {step.get('order')}")
                        return
            
            elif step_type == 'command_execution':
                # Execute command
                command = step.get('command', '')
                target_vms = step.get('targetVMs', [])
                
                for vm in target_vms:
                    success = execute_command(ft_number, command, vm, deployment_id)
                    if not success:
                        deployments[deployment_id]['status'] = 'failed'
                        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment failed at step {step.get('order')}")
                        return
            
            deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Step {step.get('order')} completed successfully")
        
        deployments[deployment_id]['status'] = 'success'
        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Template deployment completed successfully")
        
        # At the end of successful execution, save to deployment history
        if deployments[deployment_id]['status'] == 'success':
            try:
                # Create deployment history entry for template
                deployment_entry = {
                    'id': deployment_id,
                    'type': 'template',
                    'status': 'success',
                    'timestamp': datetime.now().isoformat(),
                    'ft': ft_number,
                    'logs': deployments[deployment_id]['logs'],
                    'logged_in_user': logged_in_user
                }
                
                # Save to deployment history
                save_deployment_history_func = current_app.config.get('save_deployment_history')
                if save_deployment_history_func:
                    save_deployment_history_func(deployment_entry)
                    logger.info(f"Saved template deployment {deployment_id} to history")
                
            except Exception as e:
                logger.error(f"Failed to save template deployment to history: {e}")
        
        # Also save if failed
        elif deployments[deployment_id]['status'] == 'failed':
            try:
                deployment_entry = {
                    'id': deployment_id,
                    'type': 'template',
                    'status': 'failed',
                    'timestamp': datetime.now().isoformat(),
                    'ft': ft_number,
                    'logs': deployments[deployment_id]['logs'],
                    'logged_in_user': logged_in_user
                }
                
                save_deployment_history_func = current_app.config.get('save_deployment_history')
                if save_deployment_history_func:
                    save_deployment_history_func(deployment_entry)
                    logger.info(f"Saved failed template deployment {deployment_id} to history")
                
            except Exception as e:
                logger.error(f"Failed to save failed template deployment to history: {e}")
        
    except Exception as e:
        logger.error(f"Error in template execution background thread: {e}")
        deployments[deployment_id]['status'] = 'failed'
        deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")

@app.route('/api/deploy', methods=['POST'])
def deploy():
    """Start a deployment"""
    try:
        data = request.get_json()
        ft_number = data.get('ft_number')
        file_path = data.get('file_path')
        target_vm = data.get('target_vm')
        target_path = data.get('target_path')
        target_user = data.get('target_user')
        operation_type = data.get('operation_type')
        command = data.get('command')
        logged_in_user = data.get('logged_in_user')
        
        if not ft_number or not target_vm:
            return jsonify({'error': 'Missing ft_number or target_vm'}), 400
        
        # Generate deployment ID
        deployment_id = str(uuid.uuid4())
        
        # Initialize deployment tracking
        deployments[deployment_id] = {
            'id': deployment_id,
            'type': operation_type,
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'ft': ft_number,
            'file': file_path,
            'target_vm': target_vm,
            'target_path': target_path,
            'target_user': target_user,
            'command': command,
            'logs': [],
            'logged_in_user': logged_in_user
        }
        
        # Start deployment in background thread
        def execute_deployment(deployment_id):
            try:
                if operation_type == 'file':
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting file copy from FT {ft_number} to {target_vm}:{target_path} as {target_user}")
                    success = execute_file_copy(ft_number, file_path, target_vm, target_path, target_user, deployment_id)
                elif operation_type == 'sql':
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting SQL command execution")
                    success = execute_sql_command(ft_number, file_path, target_vm, target_path, target_user, deployment_id)
                elif operation_type == 'systemd':
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting systemctl command execution")
                    success = execute_systemctl_command(ft_number, file_path, target_vm, target_path, deployment_id)
                elif operation_type == 'command':
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting command execution")
                    success = execute_command(ft_number, command, target_vm, deployment_id)
                elif operation_type == 'rollback':
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting rollback operation")
                    success = execute_rollback(ft_number, file_path, target_vm, deployment_id)
                else:
                    deployments[deployment_id]['status'] = 'failed'
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Unknown operation type")
                    return
                
                if success:
                    deployments[deployment_id]['status'] = 'success'
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment completed successfully")
                else:
                    deployments[deployment_id]['status'] = 'failed'
                    deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment failed")
                
                # Save to deployment history
                try:
                    deployment_entry = {
                        'id': deployment_id,
                        'type': operation_type,
                        'status': deployments[deployment_id]['status'],
                        'timestamp': datetime.now().isoformat(),
                        'ft': ft_number,
                        'file': file_path,
                        'target_vm': target_vm,
                        'target_path': target_path,
                        'target_user': target_user,
                        'command': command,
                        'logs': deployments[deployment_id]['logs'],
                        'logged_in_user': logged_in_user
                    }
                    
                    save_deployment_history_func = current_app.config.get('save_deployment_history')
                    if save_deployment_history_func:
                        save_deployment_history_func(deployment_entry)
                        logger.info(f"Saved deployment {deployment_id} to history")
                    
                except Exception as e:
                    logger.error(f"Failed to save deployment to history: {e}")
                
            except Exception as e:
                deployments[deployment_id]['status'] = 'failed'
                deployments[deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        
        deployment_thread = threading.Thread(target=execute_deployment, args=(deployment_id,))
        deployment_thread.daemon = True
        deployment_thread.start()
        
        return jsonify({
            'deploymentId': deployment_id,
            'message': 'Deployment started',
            'status': 'running'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deploy/<deployment_id>/logs', methods=['GET'])
def get_deployment_logs(deployment_id):
    """Get logs for a deployment"""
    try:
        deployment = deployments.get(deployment_id)
        
        if not deployment:
            return jsonify({'error': 'Deployment not found'}), 404
        
        return jsonify({
            'logs': deployment['logs'],
            'status': deployment['status'],
            'ft_number': deployment['ft'],
            'file': deployment['file'],
            'target_vm': deployment['target_vm'],
            'target_path': deployment['target_path'],
            'target_user': deployment['target_user'],
            'command': deployment['command'],
            'timestamp': deployment['timestamp'],
            'type': deployment['type'],
            'logged_in_user': deployment['logged_in_user']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments/history', methods=['GET'])
def get_deployment_history():
    """Get deployment history"""
    try:
        return jsonify(load_deployment_history())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deployments/clear', methods=['POST'])
def clear_deployment_history():
    """Clear deployment history"""
    try:
        data = request.get_json()
        days = data.get('days', 30)  # Default to 30 days
        
        if days == 0:
            # Clear all logs
            global deployment_history
            deployment_history = []
            save_deployment_history(deployment_history)
            return jsonify({'message': 'Deployment history cleared successfully'})
        
        # Calculate the date before which deployments should be removed
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter out deployments older than the cutoff date
        global deployment_history
        deployment_history = [
            d for d in deployment_history
            if datetime.fromisoformat(d['timestamp']) >= cutoff_date
        ]
        
        save_deployment_history(deployment_history)
        
        return jsonify({'message': f'Deployment history cleared (older than {days} days)'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deploy/<deployment_id>/rollback', methods=['POST'])
def rollback_deployment(deployment_id):
    """Rollback a deployment"""
    try:
        # Find the deployment in history
        deployment_to_rollback = next(
            (d for d in deployment_history if d['id'] == deployment_id), None
        )
        
        if not deployment_to_rollback:
            return jsonify({'error': 'Deployment not found in history'}), 404
        
        # Create a new deployment ID for the rollback
        rollback_deployment_id = str(uuid.uuid4())
        
        # Initialize rollback deployment tracking
        deployments[rollback_deployment_id] = {
            'id': rollback_deployment_id,
            'type': 'rollback',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'ft': deployment_to_rollback['ft'],
            'file': deployment_to_rollback['file'],
            'target_vm': deployment_to_rollback['target_vm'],
            'target_path': deployment_to_rollback['target_path'],
            'target_user': deployment_to_rollback['target_user'],
            'command': deployment_to_rollback['command'],
            'logs': [],
            'original_deployment': deployment_id,
            'logged_in_user': deployment_to_rollback['logged_in_user']
        }
        
        # Simulate rollback operation in background thread
        def execute_rollback(rollback_deployment_id):
            try:
                deployments[rollback_deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting rollback operation for {deployment_id}")
                
                # Simulate rollback (replace with actual rollback logic)
                time.sleep(5)
                
                deployments[rollback_deployment_id]['status'] = 'success'
                deployments[rollback_deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Rollback completed successfully")
                
                # Save rollback to deployment history
                try:
                    rollback_entry = {
                        'id': rollback_deployment_id,
                        'type': 'rollback',
                        'status': 'success',
                        'timestamp': datetime.now().isoformat(),
                        'ft': deployment_to_rollback['ft'],
                        'file': deployment_to_rollback['file'],
                        'target_vm': deployment_to_rollback['target_vm'],
                        'target_path': deployment_to_rollback['target_path'],
                        'target_user': deployment_to_rollback['target_user'],
                        'command': deployment_to_rollback['command'],
                        'logs': deployments[rollback_deployment_id]['logs'],
                        'original_deployment': deployment_id,
                        'logged_in_user': deployment_to_rollback['logged_in_user']
                    }
                    
                    save_deployment_history_func = current_app.config.get('save_deployment_history')
                    if save_deployment_history_func:
                        save_deployment_history_func(rollback_entry)
                        logger.info(f"Saved rollback deployment {rollback_deployment_id} to history")
                    
                except Exception as e:
                    logger.error(f"Failed to save rollback deployment to history: {e}")
                
            except Exception as e:
                deployments[rollback_deployment_id]['status'] = 'failed'
                deployments[rollback_deployment_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        
        rollback_thread = threading.Thread(target=execute_rollback, args=(rollback_deployment_id,))
        rollback_thread.daemon = True
        rollback_thread.start()
        
        return jsonify({
            'deploymentId': rollback_deployment_id,
            'message': f'Rollback started for deployment {deployment_id}',
            'status': 'running'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Static files route
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    return send_from_directory(static_dir, path)

if __name__ == '__main__':
    from datetime import timedelta
    app.run(debug=True, port=5000)
