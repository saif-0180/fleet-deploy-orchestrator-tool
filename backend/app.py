
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import os
import json
import subprocess
import time
import uuid
import threading
import logging
import glob
import tempfile
import re
import base64
import select
import pytz
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
from routes.auth_routes import auth_bp
from datetime import datetime, timedelta, timezone
from routes.auth_routes import get_current_user
#from routes.db_routes import db_routes
# Import DB routes
from routes.db_routes import db_routes
from routes.template_routes import template_bp
# Register the blueprint
#app.register_blueprint(db_blueprint, url_prefix='/api')

#retore_save_checkpoint

app = Flask(__name__, static_folder='../frontend/dist')


# Register the blueprint
app.register_blueprint(db_routes)
app.register_blueprint(auth_bp)
app.register_blueprint(template_bp)
#app.register_blueprint(db_routes)



# Directory where fix files are stored
FIX_FILES_DIR = os.environ.get('FIX_FILES_DIR', '/app/fixfiles')

# Directory for deployment logs
DEPLOYMENT_LOGS_DIR = os.environ.get('DEPLOYMENT_LOGS_DIR', '/app/logs')
APP_LOG_FILE = os.environ.get('APP_LOG_FILE', os.path.join(DEPLOYMENT_LOGS_DIR, 'application.log'))
DEPLOYMENT_HISTORY_FILE = os.path.join(DEPLOYMENT_LOGS_DIR, 'deployment_history.json')


# Configure application logging
logger = logging.getLogger('fix_deployment_orchestrator')
logger.setLevel(logging.DEBUG)
# Add this logger configuration near the top of your app.py
deploy_template_logger = logging.getLogger('deploy_template')
deploy_template_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
os.makedirs(DEPLOYMENT_LOGS_DIR, exist_ok=True)
os.makedirs('/tmp/ansible-ssh', exist_ok=True)  # Ensure ansible control path directory exists
# os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path

try:
    os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path
except PermissionError:
    logger.info("Could not set permissions on /tmp/ansible-ssh - continuing with existing permissions")



# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

# File handler (with rotation)
os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)  # Ensure log directory exists
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=10485760, backupCount=10) # 10MB per file, keep 10 files
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info("Starting Fix Deployment Orchestrator with enhanced logging")
logger.debug(f"Application environment: FLASK_ENV={os.environ.get('FLASK_ENV', 'production')}")
logger.debug(f"Fix files directory: {FIX_FILES_DIR}")
logger.debug(f"Deployment logs directory: {DEPLOYMENT_LOGS_DIR}")
logger.debug(f"Application log file: {APP_LOG_FILE}")

# Dictionary to store deployment information
deployments = {}

# Store deployments in app config so it can be accessed via current_app
app.config['deployments'] = deployments
# Also store as app attribute for direct access
app.deployments = deployments

# Functions to save and access deployment data
def save_deployment_history():
    """Save deployment history to file"""
    app.config.get('save_deployment_history_func', lambda: None)()

def log_message(deployment_id, message):
    """Log a message to deployment logs"""
    app.config.get('log_message_func', lambda d, m: None)(deployment_id, message)

# Try to load previous deployments if they exist
try:
    if os.path.exists(DEPLOYMENT_HISTORY_FILE):
        with open(DEPLOYMENT_HISTORY_FILE, 'r') as f:
            try:
                deployments = json.load(f)
                logger.info(f"Loaded {len(deployments)} previous deployments from history file")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing deployment history file: {str(e)}")
                # Create a backup of the corrupted file
                backup_file = os.path.join(DEPLOYMENT_LOGS_DIR, f'deployment_history_corrupt_{int(time.time())}.json')
                os.rename(DEPLOYMENT_HISTORY_FILE, backup_file)
                logger.info(f"Renamed corrupted history file to {backup_file}")
                deployments = {}
    else:
        # Look for backup history files in the logs directory
        backup_files = sorted(glob.glob(os.path.join(DEPLOYMENT_LOGS_DIR, 'deployment_history_*.json')), reverse=True)
        if backup_files:
            logger.info(f"Found {len(backup_files)} backup deployment history files, loading most recent")
            for backup_file in backup_files:
                try:
                    with open(backup_file, 'r') as f:
                        deployments = json.load(f)
                    logger.info(f"Loaded {len(deployments)} previous deployments from backup file {backup_file}")
                    break
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Error loading from backup file {backup_file}: {str(e)}")
                    continue
        else:
            logger.info("No deployment history file found, creating new one")
            # Create an empty history file
            with open(DEPLOYMENT_HISTORY_FILE, 'w') as f:
                json.dump({}, f)
except Exception as e:
    logger.error(f"Failed to load deployment history: {str(e)}")

# Load inventory from file or create a default one
INVENTORY_FILE = os.environ.get('INVENTORY_FILE', '/app/inventory/inventory.json')
os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)

try:
    with open(INVENTORY_FILE, 'r') as f:
        inventory = json.load(f)
    logger.info(f"Loaded inventory with {len(inventory.get('vms', []))} VMs")
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Error loading inventory: {str(e)} - Please create/fix inventory.json manually")
    inventory = {"vms": [], "users": [], "systemd_services": []}
    # Don't save the empty inventory - let user create it manually

# Function to save deployment history with backup


def save_deployment_history():
    try:
        logger.info(f"Starting to save deployment history. Current deployments count: {len(deployments)}")
        
        # Ensure the deployment logs directory exists
        try:
            os.makedirs(DEPLOYMENT_LOGS_DIR, exist_ok=True)
            logger.debug(f"Ensured directory exists: {DEPLOYMENT_LOGS_DIR}")
        except Exception as e:
            logger.error(f"Failed to create DEPLOYMENT_LOGS_DIR: {e}")
            raise
        
        # Create a backup of the current history file if it exists
        if os.path.exists(DEPLOYMENT_HISTORY_FILE):
            # timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
            backup_file = os.path.join(DEPLOYMENT_LOGS_DIR, f'deployment_history_{timestamp}.json')
            try:
                with open(DEPLOYMENT_HISTORY_FILE, 'r') as src:
                    with open(backup_file, 'w') as dst:
                        dst.write(src.read())
                logger.debug(f"Created backup of deployment history: {backup_file}")
            except Exception as e:
                logger.error(f"Error creating backup of history file: {str(e)}")
                # Don't raise here, continue with saving
        
        # Ensure the directory for the main history file exists
        history_dir = os.path.dirname(DEPLOYMENT_HISTORY_FILE)
        if history_dir:
            os.makedirs(history_dir, exist_ok=True)
        
        # Save the current deployment history
        try:
            with open(DEPLOYMENT_HISTORY_FILE, 'w') as f:
                json.dump(deployments, f, default=str, indent=2)
            logger.info(f"Saved {len(deployments)} deployments to history file: {DEPLOYMENT_HISTORY_FILE}")
        except Exception as e:
            logger.error(f"Failed to write deployment history file: {e}")
            raise
        
        # Clean up old backup files (keep only last 10)
        try:
            backup_files = sorted(glob.glob(os.path.join(DEPLOYMENT_LOGS_DIR, 'deployment_history_*.json')))
            if len(backup_files) > 10:
                for old_file in backup_files[:-10]:
                    try:
                        os.remove(old_file)
                        logger.debug(f"Removed old backup file: {old_file}")
                    except Exception as e:
                        logger.error(f"Error removing old backup file {old_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            # Don't raise here, the main save was successful
            
    except Exception as e:
        logger.error(f"Failed to save deployment history: {str(e)}")
        raise  # Re-raise so the API returns 500



# Helper function to log message to deployment log
def log_message(deployment_id, message):
    """Log a message to the deployment logs and the application log"""
    if deployment_id in deployments:
        # Add to deployment logs
        if "logs" not in deployments[deployment_id]:
            deployments[deployment_id]["logs"] = []
        deployments[deployment_id]["logs"].append(message)
        
        # Also log to application log
        logger.debug(f"[{deployment_id}] {message}")


# Check SSH key permissions and setup
def check_ssh_setup():
    try:
        # Check if SSH keys exist
        ssh_key_path = "/home/users/infadm/.ssh/id_rsa"
        if os.path.exists(ssh_key_path):
            # Ensure correct permissions
            os.chmod(ssh_key_path, 0o600)
            logger.info("SSH private key found and permissions set to 600")
            
            # Also check that the .ssh directory has proper permissions
            os.chmod("/home/users/infadm/.ssh", 0o700)
            logger.info("SSH directory permissions set to 700")

            # Check control_path_dir permissions
            control_path = "/tmp/ansible-ssh"
            if os.path.exists(control_path):
                os.chmod(control_path, 0o777)
                logger.info(f"Ansible SSH control path directory permissions set to 777: {control_path}")
            else:
                os.makedirs(control_path, exist_ok=True)
                os.chmod(control_path, 0o777)
                logger.info(f"Created Ansible SSH control path directory with permissions 777: {control_path}")
            
            # Test SSH key with ssh-keygen -l
            result = subprocess.run(
                ["ssh-keygen", "-l", "-f", ssh_key_path], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                logger.info(f"SSH key validated: {result.stdout.strip()}")
            else:
                logger.warning(f"SSH key validation failed: {result.stderr.strip()}")
        else:
            logger.critical(f"SSH private key not found at {ssh_key_path}")
    except Exception as e:
        logger.error(f"Error during SSH setup check: {str(e)}")

# Test SSH connection to each VM
def test_ssh_connections():
    for vm in inventory.get("vms", []):
        try:
            vm_name = vm.get("name")
            vm_ip = vm.get("ip")
            if not vm_name or not vm_ip:
                continue
                
            logger.info(f"Testing SSH connection to {vm_name} ({vm_ip})")
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", 
                  "-i", "/home/users/infadm/.ssh/id_rsa", f"infadm@{vm_ip}", "echo 'SSH Connection Test'"]
                
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"SSH connection to {vm_name} ({vm_ip}) successful")
            else:
                logger.warning(f"SSH connection to {vm_name} ({vm_ip}) failed: {result.stderr.strip()}")
        except Exception as e:
            logger.error(f"Error testing SSH connection to {vm_name}: {str(e)}")

# Run SSH setup check at startup
check_ssh_setup()
# Test SSH connections at startup
test_ssh_connections()

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    logger.debug(f"Serving static path: {path}")
    if path and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# API to get all FTs
@app.route('/api/fts')
def get_fts():
    ft_type = request.args.get('type', None)
    logger.info(f"Getting FTs with type filter: {ft_type}")
    
    all_fts = []
    fts_dir = os.path.join(FIX_FILES_DIR, 'AllFts')
    
    if os.path.exists(fts_dir):
        all_fts = [d for d in os.listdir(fts_dir) if os.path.isdir(os.path.join(fts_dir, d))]
        logger.debug(f"Found {len(all_fts)} FTs in directory")
    else:
        logger.warning(f"FTs directory does not exist: {fts_dir}")
    
    if ft_type == 'sql':
        # Filter FTs that have SQL files
        filtered_fts = []
        for ft in all_fts:
            ft_dir = os.path.join(fts_dir, ft)
            if any(f.endswith('.sql') for f in os.listdir(ft_dir)):
                filtered_fts.append(ft)
        logger.debug(f"Filtered to {len(filtered_fts)} SQL FTs")
        return jsonify(filtered_fts)
    
    return jsonify(all_fts)

# API to get files for an FT
@app.route('/api/fts/<ft>/files')
def get_ft_files(ft):
    ft_type = request.args.get('type', None)
    logger.info(f"Getting files for FT: {ft} with type filter: {ft_type}")
    
    ft_dir = os.path.join(FIX_FILES_DIR, 'AllFts', ft)
    
    if not os.path.exists(ft_dir):
        logger.warning(f"FT directory does not exist: {ft_dir}")
        return jsonify([])
    
    if ft_type == 'sql':
        # Return only SQL files
        sql_files = [f for f in os.listdir(ft_dir) if f.endswith('.sql')]
        logger.debug(f"Found {len(sql_files)} SQL files in FT: {ft}")
        return jsonify(sql_files)
    
    # Return all files
    files = [f for f in os.listdir(ft_dir) if os.path.isfile(os.path.join(ft_dir, f))]
    logger.debug(f"Found {len(files)} files in FT: {ft}")
    return jsonify(files)

# API to get VMs
@app.route('/api/vms')
def get_vms():
    logger.info("Getting list of VMs")
    return jsonify(inventory["vms"])

# API to get DB users
@app.route('/api/db/users')
def get_db_users():
    logger.info("Getting list of DB users")
    return jsonify(inventory["db_users"])

# API to get systemd services
@app.route('/api/systemd/services')
def get_systemd_services():
    logger.info("Getting list of systemd services")
    return jsonify(inventory["systemd_services"])


# # New APIs for template generator and Oneclick deploy using template



#================================================================
# Log Summarizer

class ComplexLogSummarizer:
    def __init__(self):
        self.severity_levels = {
            'critical': ['fatal', 'panic', 'emergency', 'critical'],
            'high': ['exception', 'error', 'fail', 'crash', 'abort'],
            'medium': ['warn', 'warning', 'deprecated', 'invalid'],
            'low': ['info', 'debug', 'trace', 'notice', 'success', 'complete']
        }

        self.common_causes = {
            'DeploymentSuccess': 'Deployment completed successfully',
            'TemplateSuccess': 'Template deployment completed successfully', 
            'FileSuccess': 'File operations completed successfully',
            'NullPointerException': 'Accessing a null object reference',
            'OutOfMemoryError': 'Insufficient memory or memory leak',
            'ConnectionError': 'Service not reachable, connection refused or timed out',
            'FileNotFound': 'Missing file or incorrect path',
            'PermissionError': 'Permission denied on file or resource',
            'SSLError': 'Certificate issue or TLS handshake failure',
            'DNSError': 'DNS resolution or lookup failure',
            'DeploymentError': 'Service configuration or deployment issue',
            'ConfigurationError': 'Configuration mismatch or missing settings',
            'GeneralError': 'Unspecified error condition'
        }

        self.recommendations = {
            'DeploymentSuccess': [
                'Deployment completed successfully',
                'Monitor application performance post-deployment',
                'Verify all services are functioning correctly'
            ],
            'TemplateSuccess': [
                'Template deployment completed successfully', 
                'Verify all template steps executed correctly',
                'Check deployed services are running as expected'
            ],
            'FileSuccess': [
                'File operations completed successfully',
                'Verify file permissions and ownership are correct',
                'Check file content matches expectations'
            ],
            'NullPointerException': [
                'Check if objects are initialized before use',
                'Review stack trace for where null was accessed',
                'Add null checks in code'
            ],
            'OutOfMemoryError': [
                'Increase heap size',
                'Check for memory leaks in application',
                'Profile memory usage patterns'
            ],
            'ConnectionError': [
                'Verify service is up and port is open',
                'Check firewall/network rules',
                'Review connection timeout settings'
            ],
            'DeploymentError': [
                'Verify service configuration files are consistent',
                'Check environment-specific variables',
                'Review deployment pipeline for configuration drift',
                'Implement configuration validation in CI/CD'
            ],
            'GeneralError': [
                'Review the logs for more details',
                'Check system resources and status',
                'Verify service dependencies'
            ]
        }

    def summarize(self, logs):
        """Main summarization method that returns the format expected by frontend"""
        if not logs or len(logs) == 0:
            return self._create_no_logs_response()
            
        combined = '\n'.join(logs)
        lower = combined.lower()

        # Analyze the content more thoroughly
        error_type = self.detect_error_type(lower, combined)
        severity = self.detect_severity(lower)
        category = self.categorize(lower)
        
        # Map severity to urgency
        urgency_map = {
            'critical': 'critical',
            'high': 'high', 
            'medium': 'medium',
            'low': 'low'
        }
        urgency = urgency_map.get(severity, 'medium')

        root_cause = self.common_causes.get(error_type, 'Analysis completed')
        recommendations = self.recommendations.get(error_type, ['Review the logs for details'])

        # Create more detailed summary based on content
        if 'success' in lower or 'completed' in lower or 'finished' in lower:
            if 'template' in lower:
                summary_text = f"Template deployment analysis completed - Status: SUCCESS"
                short_summary = "Template Deployment Success"
            elif 'file' in lower:
                summary_text = f"File operation analysis completed - Status: SUCCESS" 
                short_summary = "File Operation Success"
            else:
                summary_text = f"Deployment analysis completed - Status: SUCCESS"
                short_summary = "Deployment Success"
        else:
            summary_text = f"{severity.upper()} {error_type} detected during execution"
            short_summary = f"{error_type} Analysis"

        return {
            'summary': summary_text,
            'shortSummary': short_summary,
            'category': category,
            'severity': severity,
            'errorType': error_type,
            'rootCause': {
                'cause': root_cause,
                'description': f"Analysis suggests this is related to {category} operations",
                'confidence': 'high' if error_type in self.common_causes else 'medium'
            },
            'recommendations': recommendations,
            'urgency': urgency,
            'context': {
                'error_type': error_type,
                'category': category,
                'analyzed_logs': len(logs),
                'timestamp': datetime.utcnow().isoformat(),
                'log_sample': logs[0][:100] + '...' if logs and len(logs[0]) > 100 else logs[0] if logs else 'No logs'
            }
        }

    def _create_no_logs_response(self):
        return {
            'summary': 'No logs provided for analysis',
            'shortSummary': 'No Logs',
            'category': 'system',
            'severity': 'low',
            'errorType': 'NoLogs',
            'rootCause': {
                'cause': 'No log data available',
                'description': 'No log entries were provided for analysis',
                'confidence': 'high'
            },
            'recommendations': ['Ensure logs are being captured properly', 'Check log collection configuration'],
            'urgency': 'low',
            'context': {
                'error_type': 'NoLogs',
                'category': 'system',
                'analyzed_logs': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
        }

    def detect_error_type(self, content_lower, original_content):
        """Detect the type of error from log content with more detailed analysis"""
        
        # Check for success patterns first, but be more specific
        if any(keyword in content_lower for keyword in ['success', 'completed successfully', 'finished successfully']):
            if 'template' in content_lower:
                return 'TemplateSuccess'
            elif 'file' in content_lower:
                return 'FileSuccess'
            else:
                return 'DeploymentSuccess'
        
        # Check for error patterns
        if 'nullpointer' in content_lower or 'null reference' in content_lower:
            return 'NullPointerException'
        elif 'outofmemory' in content_lower or 'out of memory' in content_lower:
            return 'OutOfMemoryError'
        elif 'connection refused' in content_lower or 'connection timed out' in content_lower or 'unable to connect' in content_lower:
            return 'ConnectionError'
        elif 'no such file' in content_lower or 'filenotfound' in content_lower or 'enoent' in content_lower:
            return 'FileNotFound'
        elif 'permission denied' in content_lower or 'access denied' in content_lower:
            return 'PermissionError'
        elif 'ssl' in content_lower or 'certificate' in content_lower or 'tls' in content_lower:
            return 'SSLError'
        elif 'dns' in content_lower or 'name resolution' in content_lower:
            return 'DNSError'
        elif any(keyword in content_lower for keyword in ['deploy', 'deployment']) and any(keyword in content_lower for keyword in ['error', 'fail', 'failed']):
            return 'DeploymentError'
        elif 'config' in content_lower or 'configuration' in content_lower:
            return 'ConfigurationError'
        else:
            # Analyze the actual content for more insights
            if len(original_content) > 50:  # If we have substantial content
                return 'GeneralAnalysis'
            else:
                return 'GeneralError'

    def detect_severity(self, content):
        """Detect severity level from log content"""
        for level, keywords in self.severity_levels.items():
            for keyword in keywords:
                if keyword in content:
                    return level
        return 'medium'

    def categorize(self, content):
        """Categorize the error based on content"""
        if 'sql' in content or 'database' in content or 'postgres' in content or 'mysql' in content:
            return 'database'
        elif 'connection' in content or 'port' in content or 'timeout' in content or 'network' in content:
            return 'network'
        elif 'memory' in content or 'heap' in content or 'oom' in content:
            return 'memory'
        elif 'file' in content or 'disk' in content or 'filesystem' in content:
            return 'filesystem'
        elif 'permission' in content or 'access' in content or 'auth' in content:
            return 'security'
        elif 'deploy' in content or 'build' in content or 'deployment' in content or 'template' in content:
            return 'deployment'
        return 'application'


# Initialize summarizer
log_summarizer = ComplexLogSummarizer()

@app.route('/api/logs/summarize', methods=['POST'])
def summarize_logs():
    """Summarize deployment logs"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        logs = data.get('logs', [])
        deployment_id = data.get('deployment_id', '')
        print("Received logs:", logs[:2])
        
        if not logs:
            return jsonify({'error': 'No logs provided'}), 400
        
        if not isinstance(logs, list):
            return jsonify({'error': 'Logs must be an array'}), 400
        
        print(f"Received logs for analysis: {len(logs)} entries")
        print(f"Sample log: {logs[0][:200] if logs else 'No logs'}")
        
        # Analyze logs using the summarizer
        analysis = log_summarizer.summarize(logs)
        
        # Add deployment context if provided
        if deployment_id:
            analysis['context']['deployment'] = deployment_id
        
        print(f"Analysis result: {analysis['summary']}")
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'deployment_id': deployment_id,
            'analyzed_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error summarizing logs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# =============================================================================

def load_inventory():
    """Load inventory data from JSON files"""
    try:
        with open('/app/inventory/inventory.json', 'r') as f:
            inventory = json.load(f)
        with open('/app/inventory/db_inventory.json', 'r') as f:
            db_inventory = json.load(f)
        return inventory, db_inventory
    except Exception as e:
        deploy_template_logger.error(f"Error loading inventory: {str(e)}")
        return None, None

def get_vm_ip(vm_name, inventory):
    """Get VM IP from inventory"""
    for vm in inventory.get('vms', []):
        if vm['name'] == vm_name:
            return vm['ip']
    return None

def get_db_connection_details(db_connection, db_inventory):
    """Get database connection details from inventory"""
    for conn in db_inventory.get('db_connections', []):
        if conn['db_connection'] == db_connection:
            return conn
    return None

def get_playbook_details(playbook_name, inventory):
    """Get playbook details from inventory"""
    for playbook in inventory.get('playbooks', []):
        if playbook['name'] == playbook_name:
            return playbook
    return None

def get_helm_command(helm_type, inventory):
    """Get helm command from inventory"""
    for helm in inventory.get('helm_upgrades', []):
        if helm['pod_name'] == helm_type:
            return helm['command']
    return None

def run_ansible_command(command, logs):
    """Run ansible command and capture output"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            logs.extend(result.stdout.split('\n'))
        if result.stderr:
            logs.extend(result.stderr.split('\n'))
        
        if result.returncode == 0:
            logs.append(f"Command executed successfully: {' '.join(command)}")
            return True
        else:
            logs.append(f"Command failed with return code {result.returncode}: {' '.join(command)}")
            return False
            
    except subprocess.TimeoutExpired:
        logs.append(f"Command timed out: {' '.join(command)}")
        return False
    except Exception as e:
        logs.append(f"Error executing command: {str(e)}")
        return False

def run_command_with_logging(command, logs):
    """Run command and capture output with logging"""
    try:
        logs.append(f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    logs.append(f"STDOUT: {line}")
        
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    logs.append(f"STDERR: {line}")
        
        if result.returncode == 0:
            logs.append(f"Command completed successfully")
            return True
        else:
            logs.append(f"Command failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        logs.append(f"Command timed out after 10 minutes")
        return False
    except Exception as e:
        logs.append(f"Error executing command: {str(e)}")
        return False


def execute_file_deployment_step(step, inventory, deployment_id):
    deployment = deployments[deployment_id]
    """Execute file deployment step using ansible"""
    logs = []
    success = True

    try:
        logs.append(f"=== Executing File Deployment Step {step['order']} ===")
        logs.append(f"Description: {step.get('description', '')}")

        file_list = step.get('files', [])
        ft_number = step.get('ftNumber')  # CamelCase from template
        target_path = step.get('targetPath', '/tmp')
        target_user = step.get('targetUser', 'root')
        sudo = step.get('sudo', False)
        create_backup = step.get('createBackup', True)
        vms = step.get('targetVMs', [])

        if not file_list:
            logs.append("ERROR: No files specified in 'files' field")
            return False, logs
        if not ft_number:
            logs.append("ERROR: 'ftNumber' is missing")
            return False, logs
        for file_name in file_list:
                src_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft_number, file_name)
                dest_file = os.path.join(target_path, file_name)

                if not os.path.exists(src_file):
                    logs.append(f"ERROR: File not found: {src_file}")
                    success = False
                    save_deployment_history()
                    continue    

        # Generate an ansible playbook for file deployment            
        playbook_file = f"/tmp/file_deploy_{deployment_id}.yml"
        # Generate the playbook
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Deploy multiple files via template step
  hosts: deployment_targets
  gather_facts: false
  become: true
  become_method: sudo
  become_user: {target_user}
  tasks:
    - name: Ensure target directory exists
      ansible.builtin.file:
        path: "{target_path}"
        state: directory
        mode: '0755'
      become: "true"
      become_user: {target_user}

    # Check if file exists first to support backup
    - name: Check if file already exists
      ansible.builtin.stat:
        path: "{target_path}"
      register: file_stat
      
    # Create backup of existing file if requested
    - name: Create backup of existing file if it exists
      ansible.builtin.copy:
        src: "{target_path}"
        dest: "{target_path}.bak.{{ ansible_date_time.epoch }}"
        remote_src: yes
      when: file_stat.stat.exists and {str(create_backup).lower()}
      register: backup_result 

    # Log backup creation
    - name: Log backup result
      ansible.builtin.debug:
        msg: "Created backup at {{ backup_result.dest }} "
      when: backup_result.changed is defined and backup_result.changed

    # Copy the file to the target location
    - name: Copy file to target VMs
      ansible.builtin.copy:
        src: "{src_file}"
        dest: "{target_path}"
        mode: '0644'
        owner: "{target_user}"
      register: copy_result
      
    - name: Log copy result
      ansible.builtin.debug:
        msg: "File copied successfully to {vms}"
      when: copy_result.changed
""")
        logger.debug(f"Created Ansible playbook: {playbook_file}")
        
        # Generate inventory file for ansible
        inventory_file = f"/tmp/inventory_{deployment_id}"

        with open(inventory_file, 'w') as f:
            f.write("[deployment_targets]\n")
            for vm_name in vms:
                vm = get_vm_ip(vm_name, inventory)
                if not vm:
                    logs.append(f"Warning: VM {vm_name} not found in inventory")
                    continue
                f.write(f"{vm_name} ansible_host={vm} ansible_user=infadm "
                        f"ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa "
                        f"ansible_ssh_common_args='-o StrictHostKeyChecking=no "
                        f"-o UserKnownHostsFile=/dev/null -o ControlMaster=auto "
                        f"-o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
                logs.append(f"Target VM {vm_name}: {vm}")

        if not os.path.exists('/tmp/ansible-ssh'):
            os.makedirs('/tmp/ansible-ssh', exist_ok=True)
        try:
            os.chmod('/tmp/ansible-ssh', 0o777)
        except PermissionError:
            logs.append("Could not set permissions on /tmp/ansible-ssh")

        # Prepare environment and run
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"

        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-vvv"]
        # logs.append(f"Executing: {' '.join(cmd)}")
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")

        # result = subprocess.run(cmd, capture_output=True, text=True, env=env_vars)

        # if result.stdout:
        #     logs.append("=== ANSIBLE OUTPUT ===")
        #     logs.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
        # if result.stderr:
        #     logs.append("=== ANSIBLE STDERR ===")
        #     logs.extend(line.strip() for line in result.stderr.splitlines() if line.strip())

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)

        for line in process.stdout:
            line_stripped = line.strip()
            log_message(deployment_id, line_stripped)
            logger.debug(f"[{deployment_id}] {line_stripped}")

        process.wait()

        if process.returncode == 0:
            log_message(deployment_id, f"SUCCESS: All files deployed successfully")
            deployments[deployment_id]["status"] = "success"
            logger.info(f"File deployment {deployment_id} succeeded")
        else:
            log_message(deployment_id, f"ERROR: Deployment failed with return code {process.returncode}")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"File deployment {deployment_id} failed with return code {process.returncode}")

            success = False

        # Cleanup
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logs.append(deployment_id, f"Warning: Error cleaning up temp files: {str(e)}")
        save_deployment_history()
        return success, logs

    # except Exception as e:
    #     log_message(f"Exception during file deployment step: {str(e)}")
    #     success = False
    #     save_deployment_history()
    # return success, logs
    except Exception as e:
        log_message(deployment_id, f"ERROR: Exception during File deployment: {str(e)}")
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in File deployment {deployment_id}: {str(e)}")
        save_deployment_history()
        return success, logs


def execute_sql_deployment_step(step, db_inventory, deployment_id):
    """Execute SQL deployment step"""
    deployment = deployments[deployment_id]
    logs = []
    success = True
    
    try:
        logs.append(f"=== Executing SQL Deployment Step {step['order']} ===")
        logs.append(f"Description: {step['description']}")
        
        # Get database connection details
        ft_number = step.get('ftNumber')
        db_conn_name = step.get('dbConnection')
        db_details = get_db_connection_details(db_conn_name, db_inventory)
        
        if not db_details:
            logs.append(f"Error: Database connection {db_conn_name} not found")
            return False, logs
        
        # Decode password
        db_password = base64.b64decode(step.get('dbPassword', '')).decode('utf-8')
        db_user = step.get('dbUser')
        
        logs.append(f"Database: {db_details['hostname']}:{db_details['port']}/{db_details['db_name']}")
        logs.append(f"User: {db_user}")
        
        # Process SQL files
        for file_name in step.get('files', []):
            sql_file_path = f"/app/fixfiles/AllFts/{ft_number}/{file_name}"
            
            if not os.path.exists(sql_file_path):
                logs.append(f"Error: SQL file {sql_file_path} not found")
                success = False
                continue
            
            logs.append(f"Executing SQL file: {file_name}")
            
            # Create psql command
            psql_cmd = [
                'psql',
                '-h', db_details['hostname'],
                '-p', db_details['port'],
                '-d', db_details['db_name'],
                '-U', db_user,
                '-f', sql_file_path,
                '-v', 'ON_ERROR_STOP=1'
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            try:
                result = subprocess.run(psql_cmd, capture_output=True, text=True, env=env, timeout=200)
                
                if result.stdout:
                    logs.extend(result.stdout.split('\n'))
                if result.stderr:
                    logs.extend(result.stderr.split('\n'))
                
                if result.returncode == 0:
                    logs.append(f"SQL file {file_name} executed successfully")
                    log_message(deployment_id, f"SUCCESS: Template deployment completed successfully ")
                    deployments[deployment_id]["status"] = "success"
                    logger.info(f"SQL deployment {deployment_id} succeeded")
                else:
                    logs.append(f"SQL file {file_name} failed with return code {result.returncode}")
                    log_message(deployment_id, f"ERROR: SQL deployment failed ")
                    deployments[deployment_id]["status"] = "failed"
                    logger.error(f"SQL deployment {deployment_id} failed with return code {result.returncode}")
                    success = False
                    
            except subprocess.TimeoutExpired:
                logs.append(f"SQL execution timed out for file {file_name}")
                success = False
            except Exception as e:
                logs.append(f"Error executing SQL file {file_name}: {str(e)}")
                success = False
        save_deployment_history()
        logs.append(f"=== SQL Deployment Step {step['order']} {'Completed Successfully' if success else 'Failed'} ===")
        
    except Exception as e:
        logs.append(f"Error in SQL deployment step: {str(e)}")
        success = False
    
    return success, logs

def execute_service_restart_step(step, inventory, deployment_id):
    """Execute service restart step using systemctl"""
    logs = []
    success = True
    
    try:
        logs.append(f"=== Executing Service Restart Step {step['order']} ===")
        logs.append(f"Description: {step['description']}")
        
        service_name = step.get('service')
        operation = step.get('operation', 'status')
        
        logs.append(f"Service: {service_name}")
        logs.append(f"Operation: {operation}")
        

        # Generate an ansible playbook for systemd operation
        playbook_file = f"/tmp/systemd_{deployment_id}.yml"
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Systemd {operation} operation for {service_name} 
  hosts: systemd_targets
  gather_facts: true
#   become: true
  vars:
    service_name: "{service_name}"
    operation_type: "{operation}"
  tasks:
    - name: Test connection
      ansible.builtin.ping:
      
    - name: Check if service unit file exists
      ansible.builtin.stat:
        path: "/etc/systemd/system/{{{{ service_name }}}}"
      register: service_file_etc
      
    - name: Check if service unit file exists in lib
      ansible.builtin.stat:
        path: "/usr/lib/systemd/system/{{{{ service_name }}}}"
      register: service_file_lib
      
    - name: Check if service unit file exists in local
      ansible.builtin.stat:
        path: "/usr/local/lib/systemd/system/{{{{ service_name }}}}"
      register: service_file_local
      
    - name: Set service exists fact
      ansible.builtin.set_fact:
        service_exists: "{{{{ service_file_etc.stat.exists or service_file_lib.stat.exists or service_file_local.stat.exists }}}}"
        
    - name: Report if service doesn't exist
      ansible.builtin.debug:
        msg: "ERROR: Service '{{{{ service_name }}}}' unit file not found on {{{{ inventory_hostname }}}}"
      when: not service_exists
      
    - name: Get detailed service status
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: service_status
      when: service_exists
      failed_when: false
      
    - name: Get service status with systemctl
      ansible.builtin.shell: |
        systemctl status {{{{ service_name }}}} --no-pager -l || true
        echo "---SEPARATOR---"
        systemctl show {{{{ service_name }}}} --property=ActiveState,SubState,LoadState,UnitFileState,ExecMainStartTimestamp,ExecMainPID,MainPID || true
      register: service_details
      when: service_exists
      
    - name: Parse service uptime
      ansible.builtin.shell: |
        if systemctl is-active {{{{ service_name }}}} >/dev/null 2>&1; then
          start_time=$(systemctl show {{{{ service_name }}}} --property=ExecMainStartTimestamp --value)
          if [ -n "$start_time" ] && [ "$start_time" != "n/a" ]; then
            echo "Service started at: $start_time"
            # Calculate uptime
            start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo "0")
            current_epoch=$(date +%s)
            if [ "$start_epoch" -gt 0 ]; then
              uptime_seconds=$((current_epoch - start_epoch))
              uptime_days=$((uptime_seconds / 86400))
              uptime_hours=$(((uptime_seconds % 86400) / 3600))
              uptime_minutes=$(((uptime_seconds % 3600) / 60))
              echo "Uptime: ${{uptime_days}}d ${{uptime_hours}}h ${{uptime_minutes}}m"
            else
              echo "Uptime: Unable to calculate"
            fi
          else
            echo "Service start time: Not available"
            echo "Uptime: Not available"
          fi
        else
          echo "Service is not active"
        fi
      register: service_uptime
      when: service_exists
      
    - name: Display comprehensive service status
      ansible.builtin.debug:
        msg: |
          ===========================================
          SERVICE STATUS REPORT for {{{{ inventory_hostname }}}}
          ===========================================
          Service Name: {{{{ service_name }}}}
          Active State: {{{{ service_status.status.ActiveState | default('unknown') }}}}
          Sub State: {{{{ service_status.status.SubState | default('unknown') }}}}
          Load State: {{{{ service_status.status.LoadState | default('unknown') }}}}
          Unit File State: {{{{ service_status.status.UnitFileState | default('unknown') }}}}
          Main PID: {{{{ service_status.status.MainPID | default('N/A') }}}}
          
          {{{{ service_uptime.stdout | default('Uptime info not available') }}}}
          
          Status: {{{{ 'ACTIVE' if service_status.status.ActiveState == 'active' else 'INACTIVE/DEAD' }}}}
          Enabled: {{{{ 'YES' if service_status.status.UnitFileState in ['enabled', 'enabled-runtime'] else 'NO' }}}}
          ===========================================
      when: service_exists and operation_type == 'status'

    - name: Perform systemd START operation
      ansible.builtin.shell: |
        sudo systemctl start {{{{ service_name }}}}
      register: start_result
      when: service_exists and operation_type == 'start'
      

    - name: Perform systemd STOP operation
      ansible.builtin.shell: |
        sudo systemctl stop {{{{ service_name }}}}
      register: stop_result
      when: service_exists and operation_type == 'stop'
      

    - name: Perform systemd RESTART operation
      ansible.builtin.shell: |
        sudo systemctl restart {{{{ service_name }}}}
      register: restart_result
      when: service_exists and operation_type == 'restart'
      
    - name: Verify operation result
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: post_operation_status
      when: service_exists and operation_type in ['start', 'stop', 'restart']
      failed_when: false
      
    - name: Report operation success
      ansible.builtin.debug:
        msg: |
          ===========================================
          OPERATION RESULT for {{{{ inventory_hostname }}}}
          ===========================================
          Service: {{{{ service_name }}}}
          Operation: {{{{ operation_type | upper }}}}
          Result: SUCCESS
          New Status: {{{{ post_operation_status.status.ActiveState | default('unknown') }}}} ({{{{ post_operation_status.status.SubState | default('unknown') }}}})
          Enabled: {{{{ 'YES' if post_operation_status.status.UnitFileState in ['enabled', 'enabled-runtime'] else 'NO' }}}}
          ===========================================
      when: service_exists and operation_type in ['start', 'stop', 'restart']
      
    - name: Get final service status for logging
      ansible.builtin.shell: systemctl is-active {{{{ service_name }}}} || echo "inactive"
      register: final_status
      when: service_exists
      
    - name: Log final status
      ansible.builtin.debug:
        msg: "Final service status on {{{{ inventory_hostname }}}}: {{{{ final_status.stdout | default('unknown') }}}}"
      when: service_exists
""")

        # Generate inventory file for ansible
        inventory_file = f"/tmp/inventory_{deployment_id}"

                # Get target VMs
        with open(inventory_file, 'w') as f:
            f.write("[systemd_targets]\n")
            target_hosts = []
            for vm_name in step.get('targetVMs', []):
                vm = get_vm_ip(vm_name, inventory)
                if vm:
                    target_hosts.append(vm)
                    logs.append(f"Target VM {vm_name}: {vm}")
                    f.write(f"{vm_name} ansible_host={vm} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
                     
            if not target_hosts:
                logs.append("Error: No valid target VMs found")
                return False, logs
        
        # Run ansible playbook
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
        
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")
        logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
        # Use subprocess.run with capture_output=True instead of Popen
        result = subprocess.run(cmd, capture_output=True, text=True, env=env_vars, timeout=300)
        
        # Log the output line by line
        if result.stdout:
            log_message(deployment_id, "=== ANSIBLE OUTPUT ===")
            for line in result.stdout.splitlines():
                if line.strip():  # Only log non-empty lines
                    log_message(deployment_id, line.strip())
        
        if result.stderr:
            log_message(deployment_id, "=== ANSIBLE STDERR ===")
            for line in result.stderr.splitlines():
                if line.strip():  # Only log non-empty lines
                    log_message(deployment_id, line.strip())
        
        # Check result and update status
        if result.returncode == 0:
            log_message(deployment_id, f"SUCCESS: Systemd {operation} operation completed successfully ")
            deployments[deployment_id]["status"] = "completed"
            logger.info(f"Systemd operation {deployment_id} completed successfully ")
        else:
            log_message(deployment_id, f"ERROR: Systemd {operation} operation failed with return code {result.returncode} ")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"Systemd operation {deployment_id} failed with return code {result.returncode} ")
        
        # Clean up temporary files
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # Save deployment history after completion
        save_deployment_history()
        
        logs.append(f"=== Service Restart Step {step['order']} {'Completed Successfully' if success else 'Failed'} ===")
        
    except Exception as e:
        logs.append(f"Error in service restart step: {str(e)}")
        success = False
    
    return success, logs

# def execute_ansible_playbook_step(step, inventory, deployment_id):
#     """Execute ansible playbook step"""
#     logs = []
#     success = True
    
#     try:
#         logs.append(f"=== Executing Ansible Playbook Step {step['order']} ===")
#         logs.append(f"Description: {step['description']}")
        
#         playbook_name = step.get('playbook')
#         playbook_details = get_playbook_details(playbook_name, inventory)
        
#         if not playbook_details:
#             logs.append(f"Error: Playbook {playbook_name} not found in inventory")
#             return False, logs
        
#         logs.append(f"Playbook: {playbook_details['name']}")
#         logs.append(f"Path: {playbook_details['path']}")
        
#         # Build ansible-playbook command
#         ansible_cmd = [
#             'ansible-playbook',
#             playbook_details['path'],
#             '-i', playbook_details['inventory'],
#             '-f', str(playbook_details.get('forks', 10))
#         ]
        
#         # Add extra vars
#         for extra_var_file in playbook_details.get('extra_vars', []):
#             ansible_cmd.extend(['-e', f'@{extra_var_file}'])
        
#         # Add vault password file if present
#         if playbook_details.get('vault_password_file'):
#             ansible_cmd.extend(['--vault-password-file', playbook_details['vault_password_file']])
        
#         logs.append(f"Executing playbook command: {' '.join(ansible_cmd)}")
        
#         if not run_command_with_logging(ansible_cmd, logs):
#             success = False
        
#         logs.append(f"=== Ansible Playbook Step {step['order']} {'Completed Successfully' if success else 'Failed'} ===")
        
#     except Exception as e:
#         logs.append(f"Error in ansible playbook step: {str(e)}")
#         success = False
    
#     return success, logs

# def execute_ansible_playbook_step(step, inventory, deployment_id):
#     deployment = deployments[deployment_id]
#     logs = []
#     success = True

#     try:
#         logs.append(f"=== Executing Ansible Playbook Step {step['order']} ===")
#         logs.append(f"Description: {step['description']}")

#         vms = ["batch1"]
#         playbook_name = step.get('playbook')
#         playbook_details = get_playbook_details(playbook_name, inventory)

#         if not playbook_details:
#             error_msg = f"Playbook {playbook_name} not found in inventory"
#             logs.append(f"Error: {error_msg}")
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         logs.append(f"Playbook: {playbook_details['name']}")
#         logs.append(f"Path: {playbook_details['path']}")

#         ssh_user = "infadm"
#         batch1_ip = next((vm["ip"] for vm in inventory["vms"] if vm["name"] == "batch1"), None)
#         if not batch1_ip:
#             error_msg = "Could not find IP for batch1 in inventory"
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         temp_playbook_file = f"/tmp/ansible_deploy_{deployment_id}.yml"
#         inventory_file = f"/tmp/inventory_{deployment_id}"

#         with open(temp_playbook_file, 'w') as f:
#             f.write(f"""---
# - name: Wrapper to run playbook on localhost
#   hosts: deployment_targets
#   gather_facts: false
#   become: true
#   become_user: infadm
#   tasks:
#     - name: Execute original playbook on localhost
#       ansible.builtin.shell: |
#         cd $(dirname "{playbook_details['path']}")
#         ansible-playbook "{playbook_details['path']}" {"-i " + str(playbook_details.get('inventory')) if playbook_details.get('inventory') else ""} \
#         {"-f " + str(playbook_details.get('forks', 10)) if playbook_details.get('forks') else ""} \
#         {"--vault-password-file " + playbook_details['vault_password_file'] if playbook_details.get('vault_password_file') else ""} \
#         {"-e env_type=" + playbook_details['env_type'] if playbook_details.get('env_type') else ""} \
#         {" ".join(["-e@" + var for var in playbook_details.get('extra_vars', [])])}
#       register: playbook_result
#       failed_when: playbook_result.rc != 0

#     - name: Show playbook output
#       ansible.builtin.debug:
#         var: playbook_result.stdout_lines

#     - name: Show stderr if any
#       ansible.builtin.debug:
#         var: playbook_result.stderr_lines
#       when: playbook_result.stderr_lines is defined and playbook_result.stderr_lines | length > 0
# """)

#         with open(inventory_file, 'w') as f:
#             f.write("[deployment_targets]\n")
#             for vm in vms:
#                 f.write(f"{vm} ansible_host={batch1_ip} ansible_user={ssh_user} "
#                         f"ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa "
#                         f"ansible_ssh_common_args='-o StrictHostKeyChecking=no "
#                         f"-o UserKnownHostsFile=/dev/null "
#                         f"-o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r "
#                         f"-o ControlPersist=60s'\n")

#         os.makedirs("/tmp/ansible-ssh", exist_ok=True)
#         try:
#             os.chmod("/tmp/ansible-ssh", 0o777)
#         except PermissionError:
#             logger.warning("Permission denied setting mode on /tmp/ansible-ssh")

#         env_vars = os.environ.copy()
#         env_vars.update({
#             "ANSIBLE_CONFIG": "/etc/ansible/ansible.cfg",
#             "ANSIBLE_HOST_KEY_CHECKING": "False",
#             "ANSIBLE_SSH_CONTROL_PATH": "/tmp/ansible-ssh/%h-%p-%r",
#             "ANSIBLE_SSH_CONTROL_PATH_DIR": "/tmp/ansible-ssh",
#             "ANSIBLE_SSH_PIPELINING": "True",
#             "ANSIBLE_PERSISTENT_CONNECT_TIMEOUT": "60",
#             "ANSIBLE_COMMAND_TIMEOUT": "300",
#             "ANSIBLE_GATHERING": "smart",
#             "ANSIBLE_FACT_CACHING": "memory"
#         })

#         cmd = ["ansible-playbook", "-i", inventory_file, temp_playbook_file]
#         cmd.extend(["-f", str(min(playbook_details.get('forks', 10), 5))])
#         cmd.append("-v")  # if verbosity is desired


#         log_message(deployment_id, f"Executing: {' '.join(cmd)}")
#         logs.append(f"Executing playbook command: {' '.join(cmd)}")

#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
#                                    text=True, env=env_vars, bufsize=1, universal_newlines=True)

#         deployments[deployment_id]["status"] = "running"
#         save_deployment_history()
#         log_message(deployment_id, "Ansible playbook execution started...")

#         last_heartbeat = time.time()
#         heartbeat_interval = 300

#         try:
#             while True:
#                 output = process.stdout.readline()
#                 if output == '' and process.poll() is not None:
#                     break
#                 if output:
#                     line_stripped = output.strip()
#                     log_message(deployment_id, line_stripped)
#                     logger.debug(f"[{deployment_id}] {line_stripped}")
#                     last_heartbeat = time.time()
#                 elif time.time() - last_heartbeat > heartbeat_interval:
#                     log_message(deployment_id, "Playbook still running... (heartbeat)")
#                     last_heartbeat = time.time()
#                 time.sleep(1)

#         except KeyboardInterrupt:
#             process.terminate()
#             log_message(deployment_id, "Playbook execution interrupted")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         process.wait()

#         if process.returncode == 0:
#             log_message(deployment_id, "SUCCESS: Playbook completed")
#             deployments[deployment_id]["status"] = "success"
#             success = True
#         else:
#             log_message(deployment_id, "ERROR: Playbook failed")
#             deployments[deployment_id]["status"] = "failed"
#             success = False

#         try:
#             os.remove(temp_playbook_file)
#             os.remove(inventory_file)
#         except Exception as e:
#             logger.warning(f"Cleanup failed: {e}")

#         save_deployment_history()
#         logs.append(f"=== Step {step['order']} {'Succeeded' if success else 'Failed'} ===")

#     except Exception as e:
#         log_message(deployment_id, f"Exception: {str(e)}")
#         deployments[deployment_id]["status"] = "failed"
#         logger.exception(f"Exception in deployment {deployment_id}: {str(e)}")
#         logs.append(f"Error: {str(e)}")
#         save_deployment_history()
#         success = False

#     return success, logs

# def execute_ansible_playbook_step(step, inventory, deployment_id):
#     deployment = deployments[deployment_id]
#     logs = []
#     success = True

#     try:
#         logs.append(f"=== Executing Ansible Playbook Step {step['order']} ===")
#         logs.append(f"Description: {step['description']}")

#         playbook_name = step.get('playbook')
#         playbook_details = get_playbook_details(playbook_name, inventory)

#         if not playbook_details:
#             error_msg = f"Playbook {playbook_name} not found in inventory"
#             logs.append(f"Error: {error_msg}")
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         logs.append(f"Playbook: {playbook_details['name']}")
#         logs.append(f"Path: {playbook_details['path']}")

#         cmd = ["ansible-playbook", playbook_details['path']]

#         # ✅ Use inventory from playbook metadata
#         inventory_path = playbook_details.get("inventory")
#         if inventory_path:
#             cmd.extend(["-i", inventory_path])
#         else:
#             cmd.extend(["-i", "localhost,", "-c", "local"])  # fallback

#         # Forks
#         cmd.extend(["-f", str(playbook_details.get("forks", 10))])

#         # Vault password file
#         if playbook_details.get("vault_password_file"):
#             cmd.extend(["--vault-password-file", playbook_details["vault_password_file"]])

#         # Environment type
#         if playbook_details.get("env_type"):
#             cmd.extend(["-e", f"env_type={playbook_details['env_type']}"])

#         # Extra vars
#         for var_file in playbook_details.get("extra_vars", []):
#             cmd.append(f"-e@{var_file}")

#         # Verbosity
#         cmd.append("-v")

#         log_message(deployment_id, f"Executing: {' '.join(cmd)}")
#         logs.append(f"Executing playbook command: {' '.join(cmd)}")

#         env_vars = os.environ.copy()
#         env_vars.update({
#             "ANSIBLE_CONFIG": "/etc/ansible/ansible.cfg",
#             "ANSIBLE_HOST_KEY_CHECKING": "False",
#             "ANSIBLE_SSH_CONTROL_PATH": "/tmp/ansible-ssh/%h-%p-%r",
#             "ANSIBLE_SSH_CONTROL_PATH_DIR": "/tmp/ansible-ssh",
#             "ANSIBLE_SSH_PIPELINING": "True",
#             "ANSIBLE_PERSISTENT_CONNECT_TIMEOUT": "60",
#             "ANSIBLE_COMMAND_TIMEOUT": "300",
#             "ANSIBLE_GATHERING": "smart",
#             "ANSIBLE_FACT_CACHING": "memory"
#         })

#         os.makedirs("/tmp/ansible-ssh", exist_ok=True)
#         try:
#             os.chmod("/tmp/ansible-ssh", 0o777)
#         except PermissionError:
#             logger.warning("Permission denied setting mode on /tmp/ansible-ssh")

#         deployments[deployment_id]["status"] = "running"
#         save_deployment_history()
#         log_message(deployment_id, "Ansible playbook execution started...")

#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
#                                    text=True, env=env_vars, bufsize=1, universal_newlines=True)

#         last_heartbeat = time.time()
#         heartbeat_interval = 300

#         try:
#             while True:
#                 output = process.stdout.readline()
#                 if output == '' and process.poll() is not None:
#                     break
#                 if output:
#                     line_stripped = output.strip()
#                     log_message(deployment_id, line_stripped)
#                     logger.debug(f"[{deployment_id}] {line_stripped}")
#                     last_heartbeat = time.time()
#                 elif time.time() - last_heartbeat > heartbeat_interval:
#                     log_message(deployment_id, "Playbook still running... (heartbeat)")
#                     last_heartbeat = time.time()
#                 time.sleep(1)

#         except KeyboardInterrupt:
#             process.terminate()
#             log_message(deployment_id, "Playbook execution interrupted")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         process.wait()

#         if process.returncode == 0:
#             log_message(deployment_id, "SUCCESS: Playbook completed")
#             deployments[deployment_id]["status"] = "success"
#             success = True
#         else:
#             log_message(deployment_id, "ERROR: Playbook failed")
#             deployments[deployment_id]["status"] = "failed"
#             success = False

#         save_deployment_history()
#         logs.append(f"=== Step {step['order']} {'Succeeded' if success else 'Failed'} ===")

#     except Exception as e:
#         log_message(deployment_id, f"Exception: {str(e)}")
#         deployments[deployment_id]["status"] = "failed"
#         logger.exception(f"Exception in deployment {deployment_id}: {str(e)}")
#         logs.append(f"Error: {str(e)}")
#         save_deployment_history()
#         success = False

#     return success, logs

# def execute_ansible_playbook_step(step, inventory, deployment_id):
#     deployment = deployments[deployment_id]
#     logs = []
#     success = True

#     try:
#         logs.append(f"=== Executing Ansible Playbook Step {step['order']} ===")
#         logs.append(f"Description: {step['description']}")

#         playbook_name = step.get('playbook')
#         playbook_details = get_playbook_details(playbook_name, inventory)

#         if not playbook_details:
#             error_msg = f"Playbook {playbook_name} not found in inventory"
#             logs.append(f"Error: {error_msg}")
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         logs.append(f"Playbook: {playbook_details['name']}")
#         logs.append(f"Path: {playbook_details['path']}")

#         ssh_user = "infadm"
#         ssh_key_path = "/home/users/infadm/.ssh/id_rsa"

#         batch1_ip = next((vm["ip"] for vm in inventory["vms"] if vm["name"] == "batch1"), None)
#         if not batch1_ip:
#             error_msg = "Could not find IP for batch1 in inventory"
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             save_deployment_history()
#             return False, logs

#         run_path = playbook_details.get("run_path", "/home/users/infadm/rm-acd")  # Default just in case

#         # Construct the remote ansible-playbook command
#         remote_ansible_cmd = f"cd '{run_path}' && ansible-playbook '{playbook_details['path']}'"

#         if playbook_details.get('inventory'):
#             remote_ansible_cmd += f" -i '{playbook_details['inventory']}'"
#         if playbook_details.get('forks'):
#             remote_ansible_cmd += f" -f {playbook_details['forks']}"
#         if playbook_details.get('vault_password_file'):
#             remote_ansible_cmd += f" --vault-password-file '{playbook_details['vault_password_file']}'"
#         if playbook_details.get('env_type'):
#             remote_ansible_cmd += f" -e env_type={playbook_details['env_type']}"
#         if playbook_details.get('extra_vars'):
#             extra_vars_str = " ".join([f"-e@'{var}'" for var in playbook_details['extra_vars']])
#             remote_ansible_cmd += f" {extra_vars_str}"

#         # Full SSH command
#         ssh_cmd = [
#             "ssh", "-o", "StrictHostKeyChecking=no",
#             "-o", "UserKnownHostsFile=/dev/null",
#             "-i", ssh_key_path,
#             f"{ssh_user}@{batch1_ip}",
#             remote_ansible_cmd
#         ]

#         deployments[deployment_id]["status"] = "running"
#         save_deployment_history()

#         log_message(deployment_id, f"Executing remotely on batch1: {remote_ansible_cmd}")
#         logs.append(f"Executing via SSH: {' '.join(ssh_cmd)}")

#         process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
#                                    text=True, bufsize=1, universal_newlines=True)

#         last_heartbeat = time.time()
#         heartbeat_interval = 300

#         while True:
#             output = process.stdout.readline()
#             if output == '' and process.poll() is not None:
#                 break
#             if output:
#                 line_stripped = output.strip()
#                 log_message(deployment_id, line_stripped)
#                 logger.debug(f"[{deployment_id}] {line_stripped}")
#                 last_heartbeat = time.time()
#             elif time.time() - last_heartbeat > heartbeat_interval:
#                 log_message(deployment_id, "Playbook still running... (heartbeat)")
#                 last_heartbeat = time.time()
#             time.sleep(1)

#         process.wait()

#         if process.returncode == 0:
#             log_message(deployment_id, "SUCCESS: Playbook completed")
#             deployments[deployment_id]["status"] = "success"
#             success = True
#         else:
#             log_message(deployment_id, "ERROR: Playbook failed")
#             deployments[deployment_id]["status"] = "failed"
#             success = False

#         logs.append(f"=== Step {step['order']} {'Succeeded' if success else 'Failed'} ===")
#         save_deployment_history()

#     except Exception as e:
#         log_message(deployment_id, f"Exception: {str(e)}")
#         deployments[deployment_id]["status"] = "failed"
#         logger.exception(f"Exception in deployment {deployment_id}: {str(e)}")
#         logs.append(f"Error: {str(e)}")
#         save_deployment_history()
#         success = False

#     return success, logs

def execute_ansible_playbook_step(step, inventory, deployment_id):
    deployment = deployments[deployment_id]
    logs = []
    success = True

    try:
        logs.append(f"=== Executing Ansible Playbook Step {step['order']} ===")
        logs.append(f"Description: {step['description']}")

        playbook_name = step.get('playbook')
        playbook_details = get_playbook_details(playbook_name, inventory)

        if not playbook_details:
            error_msg = f"Playbook {playbook_name} not found in inventory"
            logs.append(f"Error: {error_msg}")
            log_message(deployment_id, f"ERROR: {error_msg}")
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return False, logs

        logs.append(f"Playbook: {playbook_details['name']}")
        logs.append(f"Path: {playbook_details['path']}")

        ssh_user = "infadm"
        ssh_key_path = "/home/users/infadm/.ssh/id_rsa"

        batch1_ip = next((vm["ip"] for vm in inventory["vms"] if vm["name"] == "batch1"), None)
        if not batch1_ip:
            error_msg = "Could not find IP for batch1 in inventory"
            log_message(deployment_id, f"ERROR: {error_msg}")
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return False, logs

        run_path = playbook_details.get("run_path", "/home/users/infadm/rm-acd")

        # Construct the remote ansible-playbook command
        remote_ansible_cmd = f"cd '{run_path}' && ansible-playbook '{playbook_details['path']}'"

        if playbook_details.get('inventory'):
            remote_ansible_cmd += f" -i '{playbook_details['inventory']}'"
        if playbook_details.get('forks'):
            remote_ansible_cmd += f" -f {playbook_details['forks']}"
        if playbook_details.get('vault_password_file'):
            remote_ansible_cmd += f" --vault-password-file '{playbook_details['vault_password_file']}'"
        if playbook_details.get('env_type'):
            remote_ansible_cmd += f" -e env_type={playbook_details['env_type']}"
        if playbook_details.get('extra_vars'):
            extra_vars_str = " ".join([f"-e@'{var}'" for var in playbook_details['extra_vars']])
            remote_ansible_cmd += f" {extra_vars_str}"

        # Add verbose output and timeout handling to ansible command
        remote_ansible_cmd += " -v"  # Add verbose output for better monitoring

        # Full SSH command with connection timeout and keep-alive
        ssh_cmd = [
            "ssh", 
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=60",  # Send keep-alive every 60 seconds
            "-o", "ServerAliveCountMax=10",  # Allow 10 failed keep-alives before disconnect
            "-o", "ConnectTimeout=30",       # Connection timeout
            "-i", ssh_key_path,
            f"{ssh_user}@{batch1_ip}",
            remote_ansible_cmd
        ]

        deployments[deployment_id]["status"] = "running"
        save_deployment_history()

        log_message(deployment_id, f"Executing remotely on batch1: {remote_ansible_cmd}")
        logs.append(f"Executing via SSH: {' '.join(ssh_cmd)}")

        # Enhanced process execution with better error handling
        process = subprocess.Popen(
            ssh_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True, 
            bufsize=1, 
            universal_newlines=True,
            preexec_fn=None  # Ensure proper signal handling
        )

        # Enhanced monitoring with shorter heartbeat and better timeout handling
        last_heartbeat = time.time()
        last_output_time = time.time()
        heartbeat_interval = 60  # Reduced from 300 to 60 seconds
        max_silence_duration = 1800  # 30 minutes max without any output
        output_buffer = []
        
        log_message(deployment_id, "Starting playbook execution monitoring...")

        try:
            while True:
                # Use select for non-blocking read (Unix/Linux only)
                # For Windows compatibility, you might need to use threading
                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                
                if ready:
                    output = process.stdout.readline()
                    if output:
                        line_stripped = output.strip()
                        if line_stripped:  # Only log non-empty lines
                            log_message(deployment_id, line_stripped)
                            logger.debug(f"[{deployment_id}] {line_stripped}")
                            output_buffer.append(line_stripped)
                            last_output_time = time.time()
                            last_heartbeat = time.time()
                            
                            # Keep only last 100 lines in buffer to prevent memory issues
                            if len(output_buffer) > 100:
                                output_buffer = output_buffer[-100:]
                
                # Check if process is still running
                if process.poll() is not None:
                    # Process has finished, read any remaining output
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        for line in remaining_output.strip().split('\n'):
                            if line.strip():
                                log_message(deployment_id, line.strip())
                                logger.debug(f"[{deployment_id}] {line.strip()}")
                    break
                
                current_time = time.time()
                
                # Send heartbeat message
                if current_time - last_heartbeat > heartbeat_interval:
                    heartbeat_msg = f"Playbook still running... (heartbeat) - Last output: {int(current_time - last_output_time)}s ago"
                    log_message(deployment_id, heartbeat_msg)
                    logger.info(f"[{deployment_id}] {heartbeat_msg}")
                    last_heartbeat = current_time
                
                # Check for excessive silence (possible hang)
                if current_time - last_output_time > max_silence_duration:
                    warning_msg = f"WARNING: No output received for {max_silence_duration} seconds. Playbook may be hanging."
                    log_message(deployment_id, warning_msg)
                    logger.warning(f"[{deployment_id}] {warning_msg}")
                    
                    # Optionally terminate the process if it's been silent too long
                    # Uncomment the following lines if you want to auto-terminate hanging processes
                    # log_message(deployment_id, "Terminating potentially hanging process...")
                    # process.terminate()
                    # time.sleep(10)
                    # if process.poll() is None:
                    #     process.kill()
                    # break
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.1)

        except Exception as monitoring_error:
            logger.error(f"Error during process monitoring: {str(monitoring_error)}")
            log_message(deployment_id, f"Monitoring error: {str(monitoring_error)}")

        # Wait for process completion with timeout
        try:
            process.wait(timeout=30)  # Wait up to 30 seconds for clean shutdown
        except subprocess.TimeoutExpired:
            logger.warning(f"Process didn't terminate cleanly, killing it")
            process.kill()
            process.wait()

        # Enhanced result handling
        return_code = process.returncode
        
        if return_code == 0:
            success_msg = "SUCCESS: Playbook completed successfully"
            log_message(deployment_id, success_msg)
            logger.info(f"[{deployment_id}] {success_msg}")
            deployments[deployment_id]["status"] = "success"
            success = True
        else:
            error_msg = f"ERROR: Playbook failed with return code {return_code}"
            log_message(deployment_id, error_msg)
            logger.error(f"[{deployment_id}] {error_msg}")
            deployments[deployment_id]["status"] = "failed"
            success = False

        # Log final summary
        final_msg = f"=== Step {step['order']} {'Succeeded' if success else 'Failed'} ==="
        logs.append(final_msg)
        log_message(deployment_id, final_msg)
        
        save_deployment_history()

    except Exception as e:
        error_msg = f"Exception during playbook execution: {str(e)}"
        log_message(deployment_id, error_msg)
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in deployment {deployment_id}: {str(e)}")
        logs.append(f"Error: {str(e)}")
        save_deployment_history()
        success = False

    return success, logs

def execute_helm_upgrade_step(step, inventory, deployment_id):
    deployment = deployments[deployment_id]
    """Execute helm upgrade step"""
    logs = []
    success = True
    
    try:
        logs.append(f"=== Executing Helm Upgrade Step {step['order']} ===")
        logs.append(f"Description: {step['description']}")
        
        vms = ["batch1"]
        helm_type = step.get('helmDeploymentType')
        helm_command = get_helm_command(helm_type, inventory)
    
        
        if not helm_command:
            logs.append(f"Error: Helm command for {helm_type} not found in inventory")
            return False, logs
        
        logs.append(f"Helm deployment type: {helm_type}")
        logs.append(f"Command: {helm_command}")

        ssh_user = "admin"
        batch1_ip = next((vm["ip"] for vm in inventory["vms"] if vm["name"] == "batch1"), None)
        if not batch1_ip:
            error_msg = "Could not find IP for batch1 in inventory"
            log_message(deployment_id, f"ERROR: {error_msg}")
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return False, logs

        playbook_file = f"/tmp/helm_deploy_{deployment_id}.yml"
        inventory_file = f"/tmp/inventory_{deployment_id}"
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Helm chart deployment from Template 
  hosts: deployment_targets
  gather_facts: false
  become: true
  become_user: infadm
  tasks:
    - name: Test connection
      ansible.builtin.ping:

    - name: Run Helm upgrade
      ansible.builtin.shell: "sudo su - admin -c 'cd ~ && {helm_command}'"
      register: helm_result
      failed_when: helm_result.rc != 0

    - name: Log Helm output
      ansible.builtin.debug:
        msg: "{{{{ helm_result.stdout_lines }}}}"
# - name: Helm chart deployment from Template 
#   hosts: deployment_targets
#   gather_facts: false
#   become: true
#   become_user: admin
#   tasks:
#     - name: Test connection
#       ansible.builtin.ping:

#     - name: List files in scripts directory
#       ansible.builtin.shell: "ls -la /opt/amdocs/abp/core/k8s/scripts/"
#       register: scripts_list

#     - name: Show scripts directory contents
#       ansible.builtin.debug:
#         msg: "{{{{ scripts_list.stdout_lines }}}}"

#     - name: Find k8s_Logger.ksh file
#       ansible.builtin.shell: "find /opt/amdocs -name 'k8s_Logger.ksh' -type f 2>/dev/null"
#       register: logger_find
#       ignore_errors: true

#     - name: Show logger file location
#       ansible.builtin.debug:
#         msg: "Found k8s_Logger.ksh at: {{{{ logger_find.stdout_lines }}}}"

#     - name: Check helmFU.Sh content (first 10 lines)
#       ansible.builtin.shell: "head -10 /opt/amdocs/abp/core/k8s/scripts/helmFU.Sh"
#       register: helm_content

#     - name: Show helmFU.Sh header
#       ansible.builtin.debug:
#         msg: "{{{{ helm_content.stdout_lines }}}}"

#     - name: Run Helm upgrade with debug
#       ansible.builtin.shell: "bash -x {helm_command}"
#       args:
#         chdir: "/opt/amdocs/abp/core/k8s/scripts/"
#       register: helm_result
#       failed_when: false

#     - name: Log Helm output
#       ansible.builtin.debug:
#         msg: 
#           - "Return code: {{{{ helm_result.rc }}}}"
#           - "Stdout: {{{{ helm_result.stdout_lines }}}}"
#           - "Stderr: {{{{ helm_result.stderr_lines }}}}"

""")

        logger.debug(f"Created Ansible playbook: {playbook_file}")

        with open(inventory_file, 'w') as f:
            f.write("[deployment_targets]\n")
            for vm_name in vms:
                f.write(f"{vm_name} ansible_host={batch1_ip} ansible_user=infadm "
                            f"ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa "
                            f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                            f"-o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")   

        # with open(inventory_file, 'w') as f:
        #     f.write("[deployment_targets]\n")
        #     for vm_name in vms:
        #         vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
        #         if vm:
        #             f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm "
        #                     f"ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa "
        #                     f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        #                     f"-o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")

        log_message(deployment_id, f"Created inventory file with targets: {', '.join(vms)}")

        os.makedirs("/tmp/ansible-ssh", exist_ok=True)
        try:
            os.chmod("/tmp/ansible-ssh", 0o777)
        except PermissionError:
            logger.info("Could not set permissions on /tmp/ansible-ssh")

        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"

        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)

        for line in process.stdout:
            line_stripped = line.strip()
            log_message(deployment_id, line_stripped)
            logger.debug(f"[{deployment_id}] {line_stripped}")

        process.wait()

        if process.returncode == 0:
            log_message(deployment_id, f"SUCCESS: Helm deployment completed successfully ")
            deployments[deployment_id]["status"] = "success"
            logger.info(f"Helm deployment {deployment_id} succeeded")
        else:
            log_message(deployment_id, f"ERROR: Helm deployment failed ")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"Helm deployment {deployment_id} failed with return code {process.returncode}")

        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")

        save_deployment_history()
        return success, logs

    except Exception as e:
        log_message(deployment_id, f"ERROR: Exception during Helm deployment: {str(e)}")
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in Helm deployment {deployment_id}: {str(e)}")
        save_deployment_history()
        return success, logs

def execute_template_step(step, inventory, db_inventory, deployment_id):
    """Execute a single template step based on its type"""
    step_type = step.get('type')
    
    if step_type == 'file_deployment':
        return execute_file_deployment_step(step, inventory, deployment_id)
    elif step_type == 'sql_deployment':
        return execute_sql_deployment_step(step, db_inventory, deployment_id)
    elif step_type == 'service_restart':
        return execute_service_restart_step(step, inventory, deployment_id)
    elif step_type == 'ansible_playbook':
        return execute_ansible_playbook_step(step, inventory, deployment_id)
    elif step_type == 'helm_upgrade':
        return execute_helm_upgrade_step(step, inventory, deployment_id)
    else:
        return False, [f"Unknown step type: {step_type}"]

# =============================================================================
# FLASK ROUTES - Add these routes to your app.py
# =============================================================================

@app.route('/api/deploy/templates', methods=['GET'])
def get_templates():
    """Get list of available deployment templates"""
    try:
        template_dir = '/app/deployment_templates'
        if not os.path.exists(template_dir):
            deploy_template_logger.warning(f"Template directory {template_dir} does not exist")
            return jsonify({'templates': []})
        
        templates = []
        for filename in os.listdir(template_dir):
            if filename.endswith('_template.json'):
                templates.append(filename)
        
        deploy_template_logger.debug(f"Found templates: {templates}")
        return jsonify({'templates': templates})
        
    except Exception as e:
        deploy_template_logger.error(f"Error listing templates: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/deploy/templates/<template_name>', methods=['GET'])
def get_template(template_name):
    """Get specific deployment template"""
    try:
        template_path = f'/app/deployment_templates/{template_name}'
        
        if not os.path.exists(template_path):
            return jsonify({'error': 'Template not found'}), 404
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        deploy_template_logger.debug(f"Loaded template {template_name}: {template_data}")
        return jsonify({'template': template_data})
        
    except Exception as e:
        deploy_template_logger.error(f"Error loading template {template_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/deploy/templates/execute', methods=['POST'])
def execute_template():
    """Execute a deployment template"""
    try:
        data = request.get_json()
        template_name = data.get('template_name')
        
        if not template_name:
            return jsonify({'error': 'Template name is required'}), 400
        
        # Load template
        template_path = f'/app/deployment_templates/{template_name}'
        if not os.path.exists(template_path):
            return jsonify({'error': 'Template not found'}), 404
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Load inventory
        inventory, db_inventory = load_inventory()
        if not inventory or not db_inventory:
            return jsonify({'error': 'Failed to load inventory'}), 500
        
        # Generate deployment ID
        deployment_id = str(uuid.uuid4())
        
        
        deployments[deployment_id] = {
            'type': 'template_deployment',
            'status': 'running',
            'type': 'template',
            'template': template_name,
            'logs': [],
            'template_name': template_name,
            'ft_number': template_data.get('metadata', {}).get('ft_number', 'unknown'),
            'start_time': datetime.now(timezone.utc).isoformat(),
            'steps_total': len(template_data.get('steps', [])),
            'steps_completed': 0
        }
        save_deployment_history()
        deploy_template_logger.info(f"Starting template deployment {deployment_id} for {template_name}")
        
        # Execute template in background thread
        def execute_template_background(deployment_id, template_data, ft_number, deployments):
            try:
                logger.info(f"Starting template deployment {deployment_id} for {ft_number}")
        
                
                
                if deployment_id not in deployments:
                    logger.error(f"Deployment {deployment_id} not found in deployments")
                    return
                steps = template_data.get('steps', [])
                dependencies = template_data.get('dependencies', [])
                
                # Sort steps by order
                steps.sort(key=lambda x: x.get('order', 0))
                
                overall_success = True
                
                for step in steps:
                    step_order = step.get('order')
                    step_type = step.get('type')
                    
                    deployments[deployment_id]['logs'].append(f"\n=== Starting Step {step_order}: {step_type} ===")
                    deployments[deployment_id]['logs'].append(f"Description: {step.get('description', 'N/A')}")
                    
                    # Execute the step
                    success, step_logs = execute_template_step(step, inventory, db_inventory, deployment_id)
                    
                    # Add step logs to deployment logs
                    deployments[deployment_id]['logs'].extend(step_logs)
                    
                    # Update progress
                    deployments[deployment_id]['steps_completed'] += 1
                    
                    if not success:
                        overall_success = False
                        deployments[deployment_id]['logs'].append(f"Step {step_order} failed - stopping template execution")
                        break
                    
                    deployments[deployment_id]['logs'].append(f"Step {step_order} completed successfully")
                
                # Update final status
                final_status = 'success' if overall_success else 'failed'
                deployments[deployment_id]['status'] = final_status
                deployments[deployment_id]['end_time'] = datetime.now(timezone.utc).isoformat()
                
                deployments[deployment_id]['logs'].append(f"\n=== Template Deployment {final_status.upper()} ===")
                
                deploy_template_logger.info(f"Template deployment {deployment_id} completed with status: {final_status}")
                
                # Save deployment history after completion
                try:
                    save_deployment_history()
                except Exception as save_error:
                    deploy_template_logger.error(f"Failed to save deployment history: {save_error}")
                
            except Exception as e:
                deploy_template_logger.error(f"Error in template execution background thread: {str(e)}")
                deployments[deployment_id]['status'] = 'failed'
                deployments[deployment_id]['logs'].append(f"Template execution failed: {str(e)}")
                deployments[deployment_id]['end_time'] = datetime.now(timezone.utc).isoformat()
                # Save deployment history even on failure
                try:
                    save_deployment_history()
                except Exception as save_error:
                    deploy_template_logger.error(f"Failed to save deployment history: {save_error}")

        ft_number = template_data.get('metadata', {}).get('ft_number', 'unknown')
        # Start background execution
        import threading
        thread = threading.Thread(target=execute_template_background, args=(deployment_id, template_data, ft_number, deployments))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'deployment_id': deployment_id,
            'status': 'started',
            'template_name': template_name
        })
        save_deployment_history()
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
        deploy_template_logger.error(f"Error executing template: {str(e)}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# END OF DEPLOY TEMPLATE CODE 
# =============================================================================
    
# API to deploy a file

@app.route('/api/deploy/file', methods=['POST'])
def deploy_file():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.json
    ft = data.get('ft')
    files = data.get('files', [])  # Changed to expect files array
    user = data.get('user')  # This is the target user for deployment
    target_path = data.get('targetPath')
    vms = data.get('vms')
    sudo = data.get('sudo', False)
    create_backup = data.get('createBackup', True)  # Default to true for safety
    
    logger.info(f"File deployment request received from {current_user['username']}: {len(files)} file(s) from FT {ft} to {len(vms)} VMs")
    
    # Updated validation to check for files array
    if not all([ft, files, user, target_path, vms]) or len(files) == 0:
        logger.error("Missing required parameters for file deployment")
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Generate a unique deployment ID
    deployment_id = str(uuid.uuid4())
    
    # Store deployment information with logged-in user
    deployments[deployment_id] = {
        "id": deployment_id,
        "type": "file",
        "ft": ft,
        "files": files,  # Changed to store files array
        "user": user,  # Target user for deployment
        "logged_in_user": current_user['username'],  # User who initiated the deployment
        "user_role": current_user['role'],  # Role of the user who initiated
        "target_path": target_path,
        "vms": vms,
        "sudo": sudo,
        "create_backup": create_backup,
        "status": "running",
        "timestamp": time.time(),
        "logs": []
    }
    
    # Save deployment history
    save_deployment_history()
    
    # Start deployment in a separate thread
    threading.Thread(target=process_file_deployment, args=(deployment_id,)).start()
    
    logger.info(f"File deployment initiated by {current_user['username']} with ID: {deployment_id} for {len(files)} file(s)")
    return jsonify({
        "deploymentId": deployment_id,
        "initiatedBy": current_user['username'],
        "fileCount": len(files)
    })

def process_file_deployment(deployment_id):
    deployment = deployments[deployment_id]
    
    try:
        ft = deployment["ft"]
        files = deployment["files"]  # Changed to get files array
        user = deployment["user"]  # Target user for deployment
        logged_in_user = deployment["logged_in_user"]  # User who initiated
        target_path = deployment["target_path"]
        vms = deployment["vms"]
        sudo = deployment["sudo"]
        create_backup = deployment.get("create_backup", True)
        
        logger.info(f"Processing file deployment for {len(files)} file(s) initiated by {logged_in_user}")

        # Add debug logging to see actual values
        log_message(deployment_id, f"DEBUG: Deployment initiated by user: {logged_in_user}")
        log_message(deployment_id, f"DEBUG: target_path = {target_path}")
        log_message(deployment_id, f"DEBUG: files = {files}")
        log_message(deployment_id, f"DEBUG: target_user = {user}")
        log_message(deployment_id, f"DEBUG: sudo = {sudo}")
        
        # Validate all source files exist before starting deployment
        missing_files = []
        for file_name in files:
            source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft, file_name)
            if not os.path.exists(source_file):
                missing_files.append(file_name)
        
        if missing_files:
            error_msg = f"Source files not found: {', '.join(missing_files)}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            deployments[deployment_id]["status"] = "failed"
            logger.error(error_msg)
            save_deployment_history()
            return
        
        log_message(deployment_id, f"Starting file deployment for {len(files)} file(s) to {len(vms)} VMs (initiated by {logged_in_user})")
        log_message(deployment_id, f"Files to deploy: {', '.join(files)}")
        
        # Generate an ansible playbook for multi-file deployment
        playbook_file = f"/tmp/file_deploy_{deployment_id}.yml"
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Deploy multiple files to VMs (initiated by {logged_in_user})
  hosts: deployment_targets
  gather_facts: false
  become: {"true" if sudo else "false"}
  become_method: sudo
  become_user: {user}
  tasks:
    # First test SSH connection to ensure it works
    - name: Test connection
      ansible.builtin.ping:
      register: ping_result
      
    # Create the target directory if it does not exist
    - name: Create target directory structure if it does not exist
      ansible.builtin.file:
        path: "{target_path}"
        state: directory
        mode: '0755'
      become: {"true" if sudo else "false"}
      become_user: {user}
""")
            
            # Add tasks for each file
            for file_name in files:
                source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft, file_name)
                final_target_path = os.path.join(target_path, file_name)
                
                f.write(f"""
    # Tasks for file: {file_name}
    - name: Check if {file_name} already exists
      ansible.builtin.stat:
        path: "{final_target_path}"
      register: file_stat_{file_name.replace('.', '_').replace('-', '_')}
      
    - name: Create backup of existing {file_name} if it exists
      ansible.builtin.copy:
        src: "{final_target_path}"
        dest: "{final_target_path}.bak.{{{{ ansible_date_time.epoch }}}}"
        remote_src: yes
      when: file_stat_{file_name.replace('.', '_').replace('-', '_')}.stat.exists and {str(create_backup).lower()}
      register: backup_result_{file_name.replace('.', '_').replace('-', '_')}
      
    - name: Log backup result for {file_name}
      ansible.builtin.debug:
        msg: "Created backup for {file_name} at {{{{ backup_result_{file_name.replace('.', '_').replace('-', '_')}.dest }}}} (deployment by {logged_in_user})"
      when: backup_result_{file_name.replace('.', '_').replace('-', '_')}.changed is defined and backup_result_{file_name.replace('.', '_').replace('-', '_')}.changed
      
    - name: Copy {file_name} to target VMs
      ansible.builtin.copy:
        src: "{source_file}"
        dest: "{final_target_path}"
        mode: '0644'
        owner: "{user}"
      register: copy_result_{file_name.replace('.', '_').replace('-', '_')}
      
    - name: Log copy result for {file_name}
      ansible.builtin.debug:
        msg: "File {file_name} copied successfully (deployment by {logged_in_user})"
      when: copy_result_{file_name.replace('.', '_').replace('-', '_')}.changed
""")
            
            # Add final summary task
            f.write(f"""
    - name: Deployment summary
      ansible.builtin.debug:
        msg: "Deployment completed for {len(files)} file(s): {', '.join(files)} (initiated by {logged_in_user})"
""")
        
        logger.debug(f"Created Ansible playbook: {playbook_file}")
        
        # Generate inventory file for ansible
        inventory_file = f"/tmp/inventory_{deployment_id}"
        
        with open(inventory_file, 'w') as f:
            f.write("[deployment_targets]\n")
            for vm_name in vms:
                # Find VM IP from inventory
                vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
                if vm:
                    # Add ansible_ssh_common_args to disable StrictHostKeyChecking for this connection
                    f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
        
        logger.debug(f"Created Ansible inventory: {inventory_file}")
        log_message(deployment_id, f"Created inventory file with targets: {', '.join(vms)}")
        
        # Test SSH connection to each target VM
        for vm_name in vms:
            vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
            if vm:
                log_message(deployment_id, f"Testing SSH connection to {vm_name} ({vm['ip']})")
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", 
                      "-i", "/home/users/infadm/.ssh/id_rsa", f"infadm@{vm['ip']}", "echo 'SSH Connection Test'"]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        log_message(deployment_id, f"SSH connection to {vm_name} successful")
                    else:
                        log_message(deployment_id, f"SSH connection to {vm_name} failed: {result.stderr.strip()}")
                except Exception as e:
                    log_message(deployment_id, f"SSH connection test error: {str(e)}")
        
        # Create ssh control directory to avoid "cannot bind to path" errors
        os.makedirs('/tmp/ansible-ssh', exist_ok=True)
        try:
            os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path
        except PermissionError:
            logger.info("Could not set permissions on /tmp/ansible-ssh - continuing with existing permissions")
        log_message(deployment_id, "Ensured ansible control path directory exists with permissions 777")
        
        # Run ansible playbook
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-vvv"]
        
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")
        logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)
        
        for line in process.stdout:
            line_stripped = line.strip()
            log_message(deployment_id, line_stripped)
            # Also log to main application log
            logger.debug(f"[{deployment_id}] {line_stripped}")
        
        process.wait()
        
        if process.returncode == 0:
            log_message(deployment_id, f"SUCCESS: Multi-file deployment completed successfully for {len(files)} file(s) (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "success"
            logger.info(f"Multi-file deployment {deployment_id} completed successfully for {len(files)} file(s) (initiated by {logged_in_user})")
        else:
            log_message(deployment_id, f"ERROR: Multi-file deployment failed (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"Multi-file deployment {deployment_id} failed with return code {process.returncode} (initiated by {logged_in_user})")
        
        # Clean up temporary files
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
            logger.debug(f"Cleaned up temporary files for deployment {deployment_id}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # Save deployment history after completion
        save_deployment_history()
        
    except Exception as e:
        log_message(deployment_id, f"ERROR: Exception during multi-file deployment: {str(e)}")
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in multi-file deployment {deployment_id}: {str(e)}")
        save_deployment_history()

# @app.route('/api/deploy/file', methods=['POST'])
# def deploy_file():
#     current_user = get_current_user()
#     if not current_user:
#         return jsonify({"error": "Authentication required"}), 401
    
#     data = request.json
#     ft = data.get('ft')
#     file_name = data.get('file')
#     user = data.get('user')  # This is the target user for deployment
#     target_path = data.get('targetPath')
#     vms = data.get('vms')
#     sudo = data.get('sudo', False)
#     create_backup = data.get('createBackup', True)  # Default to true for safety
    
#     logger.info(f"File deployment request received from {current_user['username']}: {file_name} from FT {ft} to {len(vms)} VMs")
    
#     if not all([ft, file_name, user, target_path, vms]):
#         logger.error("Missing required parameters for file deployment")
#         return jsonify({"error": "Missing required parameters"}), 400
    
#     # Generate a unique deployment ID
#     deployment_id = str(uuid.uuid4())
    
#     # Store deployment information with logged-in user
#     deployments[deployment_id] = {
#         "id": deployment_id,
#         "type": "file",
#         "ft": ft,
#         "file": file_name,
#         "user": user,  # Target user for deployment
#         "logged_in_user": current_user['username'],  # User who initiated the deployment
#         "user_role": current_user['role'],  # Role of the user who initiated
#         "target_path": target_path,
#         "vms": vms,
#         "sudo": sudo,
#         "create_backup": create_backup,
#         "status": "running",
#         "timestamp": time.time(),
#         "logs": []
#     }
    
#     # Save deployment history
#     save_deployment_history()
    
#     # Start deployment in a separate thread
#     threading.Thread(target=process_file_deployment, args=(deployment_id,)).start()
    
#     logger.info(f"File deployment initiated by {current_user['username']} with ID: {deployment_id}")
#     return jsonify({
#         "deploymentId": deployment_id,
#         "initiatedBy": current_user['username']
#     })

# def process_file_deployment(deployment_id):
#     deployment = deployments[deployment_id]
    
#     try:
#         ft = deployment["ft"]
#         file_name = deployment["file"]
#         user = deployment["user"]  # Target user for deployment
#         logged_in_user = deployment["logged_in_user"]  # User who initiated
#         target_path = deployment["target_path"]
#         vms = deployment["vms"]
#         sudo = deployment["sudo"]
#         create_backup = deployment.get("create_backup", True)
        
#         source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft, file_name)
#         logger.info(f"Processing file deployment from {source_file} initiated by {logged_in_user}")

#         # Add debug logging to see actual values
#         log_message(deployment_id, f"DEBUG: Deployment initiated by user: {logged_in_user}")
#         log_message(deployment_id, f"DEBUG: target_path = {target_path}")
#         log_message(deployment_id, f"DEBUG: file_name = {file_name}")
#         log_message(deployment_id, f"DEBUG: target_user = {user}")
#         log_message(deployment_id, f"DEBUG: sudo = {sudo}")
        
#         if not os.path.exists(source_file):
#             error_msg = f"Source file not found: {source_file}"
#             log_message(deployment_id, f"ERROR: {error_msg}")
#             deployments[deployment_id]["status"] = "failed"
#             logger.error(error_msg)
#             save_deployment_history()
#             return
        
#         log_message(deployment_id, f"Starting file deployment for {file_name} to {len(vms)} VMs (initiated by {logged_in_user})")
        
#         # Generate an ansible playbook for file deployment
#         playbook_file = f"/tmp/file_deploy_{deployment_id}.yml"
        
#         # Create a more robust playbook that creates target directory if needed
#         final_target_path = os.path.join(target_path, file_name)
#         target_dir = os.path.dirname(final_target_path)
        
#         with open(playbook_file, 'w') as f:
#             f.write(f"""---
# - name: Deploy file to VMs (initiated by {logged_in_user})
#   hosts: deployment_targets
#   gather_facts: false
#   become: {"true" if sudo else "false"}
#   become_method: sudo
#   become_user: {user}
#   tasks:
#     # First test SSH connection to ensure it works
#     - name: Test connection
#       ansible.builtin.ping:
#       register: ping_result
      
#     # Create the full target directory path if it does not exist
#     - name: Create target directory structure if it does not exist
#       ansible.builtin.file:
#         path: "{target_path}"
#         state: directory
#         mode: '0755'
#       become: {"true" if sudo else "false"}
#       become_user: {user}
      
#     # Check if file exists first to support backup
#     - name: Check if file already exists
#       ansible.builtin.stat:
#         path: "{final_target_path}"
#       register: file_stat
      
#     # Create backup of existing file if requested
#     - name: Create backup of existing file if it exists
#       ansible.builtin.copy:
#         src: "{final_target_path}"
#         dest: "{final_target_path}.bak.{{ ansible_date_time.epoch }}"
#         remote_src: yes
#       when: file_stat.stat.exists and {str(create_backup).lower()}
#       register: backup_result
      
#     # Log backup creation
#     - name: Log backup result
#       ansible.builtin.debug:
#         msg: "Created backup at {{ backup_result.dest }} (deployment by {logged_in_user})"
#       when: backup_result.changed is defined and backup_result.changed
      
#     # Copy the file to the target location
#     - name: Copy file to target VMs
#       ansible.builtin.copy:
#         src: "{source_file}"
#         dest: "{final_target_path}"
#         mode: '0644'
#         owner: "{user}"
#       register: copy_result
      
#     - name: Log copy result
#       ansible.builtin.debug:
#         msg: "File copied successfully to {vms} (deployment by {logged_in_user})"
#       when: copy_result.changed
# """)
#         logger.debug(f"Created Ansible playbook: {playbook_file}")
        
#         # Generate inventory file for ansible
#         inventory_file = f"/tmp/inventory_{deployment_id}"
        
#         with open(inventory_file, 'w') as f:
#             f.write("[deployment_targets]\n")
#             for vm_name in vms:
#                 # Find VM IP from inventory
#                 vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
#                 if vm:
#                     # Add ansible_ssh_common_args to disable StrictHostKeyChecking for this connection
#                     f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
        
#         logger.debug(f"Created Ansible inventory: {inventory_file}")
#         log_message(deployment_id, f"Created inventory file with targets: {', '.join(vms)}")
        
#         # Test SSH connection to each target VM
#         for vm_name in vms:
#             vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
#             if vm:
#                 log_message(deployment_id, f"Testing SSH connection to {vm_name} ({vm['ip']})")
#                 cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", 
#                       "-i", "/home/users/infadm/.ssh/id_rsa", f"infadm@{vm['ip']}", "echo 'SSH Connection Test'"]
                
#                 try:
#                     result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
#                     if result.returncode == 0:
#                         log_message(deployment_id, f"SSH connection to {vm_name} successful")
#                     else:
#                         log_message(deployment_id, f"SSH connection to {vm_name} failed: {result.stderr.strip()}")
#                 except Exception as e:
#                     log_message(deployment_id, f"SSH connection test error: {str(e)}")
        
#         # Create ssh control directory to avoid "cannot bind to path" errors
#         os.makedirs('/tmp/ansible-ssh', exist_ok=True)
#         # os.chmod('/tmp/ansible-ssh', 0o777)
#         try:
#             os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path
#         except PermissionError:
#             logger.info("Could not set permissions on /tmp/ansible-ssh - continuing with existing permissions")
#         log_message(deployment_id, "Ensured ansible control path directory exists with permissions 777")
        
#         # Run ansible playbook
#         env_vars = os.environ.copy()
#         env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
#         env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
#         env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
#         env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
#         cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-vvv"]
        
#         log_message(deployment_id, f"Executing: {' '.join(cmd)}")
#         logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)
        
#         for line in process.stdout:
#             line_stripped = line.strip()
#             log_message(deployment_id, line_stripped)
#             # Also log to main application log
#             logger.debug(f"[{deployment_id}] {line_stripped}")
        
#         process.wait()
        
#         if process.returncode == 0:
#             log_message(deployment_id, f"SUCCESS: File deployment completed successfully (initiated by {logged_in_user})")
#             deployments[deployment_id]["status"] = "success"
#             logger.info(f"File deployment {deployment_id} completed successfully (initiated by {logged_in_user})")
#         else:
#             log_message(deployment_id, f"ERROR: File deployment failed (initiated by {logged_in_user})")
#             deployments[deployment_id]["status"] = "failed"
#             logger.error(f"File deployment {deployment_id} failed with return code {process.returncode} (initiated by {logged_in_user})")
        
#         # Clean up temporary files
#         try:
#             os.remove(playbook_file)
#             os.remove(inventory_file)
#             logger.debug(f"Cleaned up temporary files for deployment {deployment_id}")
#         except Exception as e:
#             logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
#         # Save deployment history after completion
#         save_deployment_history()
        
#     except Exception as e:
#         log_message(deployment_id, f"ERROR: Exception during file deployment: {str(e)}")
#         deployments[deployment_id]["status"] = "failed"
#         logger.exception(f"Exception in file deployment {deployment_id}: {str(e)}")
#         save_deployment_history()


# # API to validate file deployment

@app.route('/api/deploy/<deployment_id>/validate', methods=['POST'])
def validate_deployment(deployment_id):
    logger.info(f"Validating deployment with ID: {deployment_id}")
    
    data = request.json or {}
    use_sudo = data.get('sudo', False)

    if deployment_id not in deployments:
        logger.error(f"Deployment not found with ID: {deployment_id}")
        return jsonify({"error": "Deployment not found"}), 404
    
    deployment = deployments[deployment_id]

    if deployment["type"] != "file":
        logger.error(f"Cannot validate non-file deployment type: {deployment['type']}")
        return jsonify({"error": "Only file deployments can be validated"}), 400
    
    vms = deployment["vms"]
    file_name = deployment["file"]
    target_path = os.path.join(deployment["target_path"], file_name)

    log_message(deployment_id, f"Starting validation for file {file_name} on {len(vms)} VMs")
    
    results = []

    for vm_name in vms:
        vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
        if not vm:
            log_message(deployment_id, f"ERROR: VM {vm_name} not found in inventory")
            results.append({
                "vm": vm_name,
                "status": "ERROR",
                "message": "VM not found"
            })
            continue

        try:
            # Use tempfile to create unique playbook and inventory files
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp_playbook, \
                 tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_inventory:
                
                validate_playbook = tmp_playbook.name
                validate_inventory = tmp_inventory.name

                # Write Ansible playbook
                tmp_playbook.write(f"""---
- name: Validate file
  hosts: {vm_name}
  gather_facts: false
  become: {"true" if use_sudo else "false"}
  tasks:
    - name: Check if file exists
      stat:
        path: "{target_path}"
      register: file_check
      failed_when: not file_check.stat.exists

    - name: Get file checksum
      shell: cksum "{target_path}" | awk '{{print $1, $2}}'
      register: cksum_result
      when: file_check.stat.exists

    - name: Get file permissions
      shell: ls -la "{target_path}" | awk '{{print $1, $3, $4}}'
      register: perm_result
      when: file_check.stat.exists
""")
            # log_message(deployment_id, f"Validation on {vm_name}: {result_message}")
            validate_inventory = f"/tmp/validate_inventory_{deployment_id}_{vm_name}"
            with open(validate_inventory, 'w') as f:
                f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'")

            log_message(deployment_id, f"Running validation on {vm_name}")
            cmd = ["ansible-playbook", "-i", validate_inventory, validate_playbook, "--limit", vm_name, "-v"]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
            logger.debug(f"Validation output for {vm_name}: {output}")
            log_message(deployment_id, f"Raw validation output on {vm_name}: {output}")

            # Initialize defaults
            cksum_info = "File not found"
            perm_info = "N/A"

            # Extract checksum - look for the stdout value in the checksum task
            cksum_match = re.search(r'TASK \[Get file checksum\].*?"stdout": "([^"]*)"', output, re.DOTALL)
            if cksum_match:
                cksum_info = cksum_match.group(1).strip()
                logger.debug(f"Extracted checksum for {vm_name}: {cksum_info}")
            else:
                # Fallback: try to find any stdout with checksum pattern (numbers followed by number)
                fallback_cksum = re.search(r'"stdout": "(\d+\s+\d+)"', output)
                if fallback_cksum:
                    cksum_info = fallback_cksum.group(1).strip()
                    logger.debug(f"Extracted checksum (fallback) for {vm_name}: {cksum_info}")

            # Extract permissions - look for the stdout value in the permissions task  
            perm_match = re.search(r'TASK \[Get file permissions\].*?"stdout": "([^"]*)"', output, re.DOTALL)
            if perm_match:
                perm_info = perm_match.group(1).strip()
                logger.debug(f"Extracted permissions for {vm_name}: {perm_info}")
            else:
                # Fallback: try to find any stdout with file permission pattern
                fallback_perm = re.search(r'"stdout": "(-[rwx-]+\.?\s+\w+\s+\w+)"', output)
                if fallback_perm:
                    perm_info = fallback_perm.group(1).strip()
                    logger.debug(f"Extracted permissions (fallback) for {vm_name}: {perm_info}")

            result_message = f"Checksum={cksum_info}, Permissions={perm_info}"
            log_message(deployment_id, f"Validation on {vm_name}: {result_message}")           
            results.append({
                "vm": vm_name,
                "status": "SUCCESS",
                "message": result_message,
                "cksum": cksum_info,
                "permissions": perm_info
            })

        except subprocess.CalledProcessError as e:
            error = e.output.decode().strip()
            log_message(deployment_id, f"Validation failed on {vm_name}: {error}")
            results.append({
                "vm": vm_name,
                "status": "ERROR",
                "message": "Validation failed",
                "output": error
            })

        finally:
            # Ensure cleanup even on error
            try:
                os.remove(validate_playbook)
                os.remove(validate_inventory)
            except Exception as cleanup_err:
                logger.warning(f"Failed to clean up temp files for {vm_name}: {cleanup_err}")

    logger.info(f"Validation completed for deployment {deployment_id} with {len(results)} results")
    save_deployment_history()
    return jsonify({"results": results})

# API to run shell command
@app.route('/api/command/shell', methods=['POST'])
def run_shell_command():
    # Get current authenticated user
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    command = data.get('command')
    vms = data.get('vms')
    sudo = data.get('sudo', False)
    user = data.get('user', 'infadm')
    working_dir = data.get('workingDir', '')
    
    logger.info(f"Shell command request received: '{command}' on {len(vms)} VMs as user {user}")
    
    if not all([command, vms]):
        logger.error("Missing required parameters for shell command")
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Generate a unique deployment ID
    deployment_id = str(uuid.uuid4())
    
    # Store deployment information
    deployments[deployment_id] = {
        "id": deployment_id,
        "type": "command",
        "command": command,
        "vms": vms,
        "logged_in_user": current_user['username'],  # User who initiated the deployment
        "user_role": current_user['role'],  # Role of the user who initiated
        "sudo": sudo,
        "user": user,
        "working_dir": working_dir,
        "status": "running",
        "timestamp": time.time(),
        "logs": []
    }
    
    # Save deployment history
    save_deployment_history()
    
    # Start command execution in a separate thread
    threading.Thread(target=process_shell_command, args=(deployment_id,)).start()
    
    logger.info(f"Shell command initiated by {current_user['username']} with ID: {deployment_id}")
    return jsonify({
        "deploymentId": deployment_id,
        "initiatedBy": current_user['username'],
        "commandId": deployment_id
        })


def process_shell_command(deployment_id):
    deployment = deployments[deployment_id]
    
    try:
        command = deployment["command"]
        vms = deployment["vms"]
        sudo = deployment["sudo"]
        logged_in_user = deployment["logged_in_user"]  # User who initiated
        user = deployment.get("user", "infadm")
        working_dir = deployment.get("working_dir", "")
        
        log_message(deployment_id, f"Running command on {len(vms)} VMs: {command} initiated by {logged_in_user}")
        
        # Generate an ansible playbook for shell command
        playbook_file = f"/tmp/shell_command_{deployment_id}.yml"
        
        # Enhanced playbook with proper variable handling
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Run shell command on VMs (initiated by {logged_in_user})
  hosts: command_targets
  gather_facts: true
  become: {"true" if sudo else "false"}
  become_method: sudo
  become_user: {user}
  vars:
    working_dir: "{working_dir}"
    target_user: "{user}"
    use_sudo: {"true" if sudo else "false"}
  tasks:
    # Test connection
    - name: Test connection
      ansible.builtin.ping:
      
    # Debug working directory value
    - name: Debug working_dir value
      ansible.builtin.debug:
        msg: "working_dir is '{{{{ working_dir | default('UNDEFINED') }}}}'"

    # Create working directory if specified and doesn't exist
    - name: Ensure working directory exists
      ansible.builtin.file:
        path: "{{{{ working_dir }}}}"
        state: directory
        mode: '0755'
      when: working_dir is defined and working_dir | trim | length > 0
      become: "{{{{ use_sudo }}}}"
      become_user: "{{{{ target_user if use_sudo else omit }}}}"
      
    # Execute the shell command
    - name: Execute shell command
      ansible.builtin.shell: "{command}"
      args:
        executable: /bin/bash
        chdir: "{{{{ working_dir if (working_dir is defined and working_dir | trim | length > 0) else '~' }}}}"
      register: command_result 

    # Log command result
    - name: Log command result
      ansible.builtin.debug:
        var: command_result.stdout_lines
        
    # Also log stderr if there are errors
    - name: Log command errors (if any)
      ansible.builtin.debug:
        var: command_result.stderr_lines
      when: command_result.stderr_lines is defined and command_result.stderr_lines | length > 0
""")
        logger.debug(f"Created Ansible playbook for shell command: {playbook_file}")
        
        # Generate inventory file for ansible
        inventory_file = f"/tmp/inventory_{deployment_id}"
        
        with open(inventory_file, 'w') as f:
            f.write("[command_targets]\n")
            for vm_name in vms:
                # Find VM IP from inventory
                vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
                if vm:
                    f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
        
        logger.debug(f"Created Ansible inventory: {inventory_file}")
        
        # Ensure control path directory exists
        os.makedirs('/tmp/ansible-ssh', exist_ok=True)
        # os.chmod('/tmp/ansible-ssh', 0o777)
        try:
            os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path
        except PermissionError:
            logger.info("Could not set permissions on /tmp/ansible-ssh - continuing with existing permissions")
        
        # Run ansible playbook
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
        
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")
        logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)
        
        for line in process.stdout:
            line_stripped = line.strip()
            log_message(deployment_id, line_stripped)
            # Also log to main application log
            logger.debug(f"[{deployment_id}] {line_stripped}")
        
        process.wait()
        
        if process.returncode == 0:
            log_message(deployment_id, f"SUCCESS: Shell command executed successfully (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "success"
            logger.info(f"Shell command {deployment_id} completed successfully (initiated by {logged_in_user})")
        else:
            log_message(deployment_id, f"ERROR: Shell command execution failed (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"Shell command {deployment_id} failed with return code {process.returncode} (initiated by {logged_in_user})")
        
        # Clean up temporary files
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # Save deployment history after completion
        save_deployment_history()
        
    except Exception as e:
        log_message(deployment_id, f"ERROR: Exception during shell command execution: {str(e)}")
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in shell command {deployment_id}: {str(e)}")
        save_deployment_history()

# API to get deployment history

@app.route('/api/deployments/history')
def get_deployment_history():
    try:
        logger.info("=== START: Getting deployment history ===")
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request args: {request.args}")
        
        # Log deployments variable state
        logger.debug(f"Deployments variable exists: {deployments is not None}")
        logger.debug(f"Deployments type: {type(deployments)}")
        logger.debug(f"Deployments length: {len(deployments) if deployments else 0}")
        logger.debug(f"Deployments keys: {list(deployments.keys()) if deployments else []}")
        
        # Check if deployments is empty, try to reload from file
        if not deployments:
            logger.info("Deployments dictionary is empty, attempting to reload from file")
            try:
                logger.debug(f"Checking if history file exists: {DEPLOYMENT_HISTORY_FILE}")
                logger.debug(f"File exists: {os.path.exists(DEPLOYMENT_HISTORY_FILE)}")
                
                if os.path.exists(DEPLOYMENT_HISTORY_FILE):
                    with open(DEPLOYMENT_HISTORY_FILE, 'r') as f:
                        loaded_deployments = json.load(f)
                        logger.debug(f"Loaded deployments type: {type(loaded_deployments)}")
                        logger.debug(f"Loaded deployments length: {len(loaded_deployments) if loaded_deployments else 0}")
                        
                        if loaded_deployments:
                            # Update global deployments dictionary
                            deployments.clear()
                            deployments.update(loaded_deployments)
                            logger.info(f"Successfully reloaded {len(deployments)} deployments from history file")
                        else:
                            logger.warning("Loaded deployments is empty or None")
                else:
                    logger.warning(f"Deployment history file does not exist: {DEPLOYMENT_HISTORY_FILE}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error when loading deployment history: {str(e)}")
                logger.error(f"Error line: {e.lineno}, column: {e.colno}")
            except Exception as e:
                logger.error(f"Failed to reload deployment history: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Log current deployments state before processing
        logger.debug(f"Final deployments count before processing: {len(deployments)}")
        
        # Get deployment values and normalize timestamps
        logger.debug("Starting deployment processing...")
        deployment_values = list(deployments.values())
        logger.debug(f"Deployment values count: {len(deployment_values)}")
        
        # Normalize timestamps to consistent format (float/unix timestamp)
        for i, d in enumerate(deployment_values):
            original_timestamp = d.get("timestamp", 0)
            logger.debug(f"Processing deployment {i}: original timestamp={original_timestamp} (type: {type(original_timestamp)})")
            
            try:
                # Convert timestamp to float (unix timestamp) for consistent sorting
                if isinstance(original_timestamp, str):
                    # Try to parse string timestamp
                    try:
                        # Try ISO format first
                        from datetime import datetime
                        dt = datetime.fromisoformat(original_timestamp.replace('Z', '+00:00'))
                        normalized_timestamp = dt.timestamp()
                        logger.debug(f"Converted ISO string timestamp to float: {normalized_timestamp}")
                    except ValueError:
                        try:
                            # Try other common formats
                            dt = datetime.strptime(original_timestamp, '%Y-%m-%dT%H:%M:%S')
                            normalized_timestamp = dt.timestamp()
                            logger.debug(f"Converted string timestamp to float: {normalized_timestamp}")
                        except ValueError:
                            # If parsing fails, try to convert directly to float
                            try:
                                normalized_timestamp = float(original_timestamp)
                                logger.debug(f"Converted string to float directly: {normalized_timestamp}")
                            except ValueError:
                                logger.warning(f"Could not parse timestamp '{original_timestamp}', using current time")
                                normalized_timestamp = time.time()
                elif isinstance(original_timestamp, (int, float)):
                    normalized_timestamp = float(original_timestamp)
                    logger.debug(f"Timestamp already numeric: {normalized_timestamp}")
                else:
                    logger.warning(f"Unknown timestamp type: {type(original_timestamp)}, using current time")
                    normalized_timestamp = time.time()
                
                # Store normalized timestamp for sorting

                d["_sort_timestamp"] = normalized_timestamp
                
            except Exception as e:
                logger.error(f"Error processing timestamp for deployment {i}: {str(e)}")
                d["_sort_timestamp"] = time.time()  # Default fallback
        
        # Sort deployments by normalized timestamp, newest first
        logger.debug("Starting deployment sorting...")
        for dep_id, dep in deployments.items():
            dep['id'] = dep_id

        sorted_deployments = sorted(
            deployment_values,
            key=lambda x: x.get("_sort_timestamp", 0),
            reverse=True
        )
        logger.debug(f"Sorted deployments count: {len(sorted_deployments)}")
        
        # Convert timestamps to ISO format for API response and clean up sort field
        logger.debug("Converting timestamps for API response...")
        for i, d in enumerate(sorted_deployments):
            sort_timestamp = d.get("_sort_timestamp", 0)
            
            try:
                # Convert to ISO format for API response
                # d["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(sort_timestamp))
                # d["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(sort_timestamp))
                d["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(sort_timestamp))
                logger.debug(f"Final timestamp for deployment {i}: {d['timestamp']}")
            except Exception as e:
                logger.error(f"Error converting timestamp for deployment {i}: {str(e)}")
                d["timestamp"] = "1970-01-01T00:00:00"  # Default fallback
            
            # Remove the temporary sort field
            if "_sort_timestamp" in d:
                del d["_sort_timestamp"]
            
            # Ensure logs field is present
            if "logs" not in d:
                d["logs"] = []
                logger.debug(f"Added empty logs array to deployment {i}")
            else:
                logger.debug(f"Deployment {i} already has {len(d.get('logs', []))} log entries")
        
        logger.info(f"Successfully processed {len(sorted_deployments)} deployments")
        logger.debug("=== END: Getting deployment history ===")
        
        id_to_deployment = {
            d.get('id', f"unknown-{i}"): d
            for i, d in enumerate(sorted_deployments)
        }

        return jsonify(id_to_deployment)
        # return jsonify(sorted_deployments)
        
    except Exception as e:
        import traceback
        logger.error("=== CRITICAL ERROR in get_deployment_history ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        logger.error("=== END CRITICAL ERROR ===")
        
        # Return JSON error response
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
            "type": type(e).__name__
        }), 500



# API to get logs for a specific deployment

@app.route('/api/deployments/files/recent', methods=['GET'])
def get_recent_file_deployments():
    """Get recent successful file deployments for rollback purposes"""
    try:
        logger.info("Fetching recent file deployments")
        
        # Filter and sort deployments
        file_deployments = []
        
        for deployment_id, deployment in deployments.items():
            # Only include successful file deployments
            if (deployment.get("type") == "file" and 
                deployment.get("status") == "success"):
                
                # Ensure timestamp is properly formatted
                timestamp = deployment.get("timestamp")
                if isinstance(timestamp, (int, float)):
                    # Convert to ISO format for consistent frontend handling
                    deployment_copy = deployment.copy()
                    deployment_copy["timestamp"] = datetime.fromtimestamp(timestamp).isoformat()
                elif isinstance(timestamp, str):
                    # Keep string timestamps as-is (should already be ISO format)
                    deployment_copy = deployment.copy()
                else:
                    # Fallback for missing/invalid timestamps
                    deployment_copy = deployment.copy()
                    deployment_copy["timestamp"] = datetime.now(timezone.utc).isoformat()
                
                file_deployments.append(deployment_copy)
        
        # Sort by timestamp (most recent first)
        # Convert timestamps to floats for sorting
        for deployment in file_deployments:
            timestamp_str = deployment["timestamp"]
            try:
                if 'T' in timestamp_str:
                    # ISO format
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    deployment["_sort_timestamp"] = dt.timestamp()
                else:
                    # Assume it's already a timestamp string
                    deployment["_sort_timestamp"] = float(timestamp_str)
            except (ValueError, TypeError):
                # Fallback to current time for invalid timestamps
                deployment["_sort_timestamp"] = time.time()
        
        # Sort by the normalized timestamp
        file_deployments.sort(key=lambda x: x["_sort_timestamp"], reverse=True)
        
        # Remove the temporary sorting field and limit to 10 most recent
        recent_deployments = []
        for deployment in file_deployments[:10]:
            deployment.pop("_sort_timestamp", None)
            recent_deployments.append(deployment)
        
        logger.info(f"Found {len(recent_deployments)} recent file deployments")
        return jsonify(recent_deployments)
        
    except Exception as e:
        logger.error(f"Error fetching recent file deployments: {str(e)}")
        return jsonify({"error": "Failed to fetch recent deployments"}), 500

# API to get logs for a specific deployment


@app.route('/api/deploy/<deployment_id>/logs')
def get_deployment_logs(deployment_id):
    logger.info(f"Getting logs for deployment: {deployment_id}")
    
    def find_deployment_with_retry(deployment_id, max_retries=3):
        """Find deployment with retry logic for race conditions"""
        
        for attempt in range(max_retries):
            logger.debug(f"Attempt {attempt + 1} to find deployment {deployment_id}")
            
            # First check in-memory deployments
            if deployment_id in deployments:
                logger.info(f"Found deployment {deployment_id} in memory on attempt {attempt + 1}")
                return deployments[deployment_id]
            
            # If not found in memory, try to load from history file
            logger.debug(f"Deployment {deployment_id} not in memory, checking history file (attempt {attempt + 1})")
            
            try:
                if os.path.exists(DEPLOYMENT_HISTORY_FILE):
                    # Add increasing delay for each retry to handle race conditions
                    if attempt > 0:
                        delay = 0.5 * attempt
                        logger.debug(f"Waiting {delay}s before reading file (attempt {attempt + 1})")
                        time.sleep(delay)
                    
                    with open(DEPLOYMENT_HISTORY_FILE, 'r') as f:
                        saved_deployments = json.load(f)
                        
                        if deployment_id in saved_deployments:
                            logger.info(f"Found deployment {deployment_id} in history file on attempt {attempt + 1}")
                            deployment = saved_deployments[deployment_id]
                            
                            # Add it back to memory for future requests
                            deployments[deployment_id] = deployment
                            logger.debug(f"Added deployment {deployment_id} back to memory")
                            
                            return deployment
                        else:
                            logger.debug(f"Deployment {deployment_id} not found in history file (attempt {attempt + 1})")
                            
                else:
                    logger.warning(f"History file {DEPLOYMENT_HISTORY_FILE} does not exist (attempt {attempt + 1})")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    return None
                # Continue to next attempt
                
            except Exception as e:
                logger.error(f"Error reading deployment history on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    return None
                # Continue to next attempt
            
            # If this wasn't the last attempt, wait a bit before retrying
            if attempt < max_retries - 1:
                time.sleep(0.2 * (attempt + 1))
        
        logger.error(f"Could not find deployment {deployment_id} after {max_retries} attempts")
        return None
    
    # Check if client expects server-sent events
    accept_header = request.headers.get('Accept', '')
    if 'text/event-stream' in accept_header:
        # Return SSE stream for real-time logs
        def generate():
            deployment = find_deployment_with_retry(deployment_id)
            if deployment:
                # First send all existing logs
                for log in deployment.get("logs", []):
                    yield f"data: {json.dumps({'message': log})}\n\n"

                # Send current status
                current_status = deployment.get('status', 'running')
                yield f"data: {json.dumps({'status': current_status})}\n\n"

                # Return if deployment is already completed
                if current_status in ["success", "failed"]:
                    logger.info(f"Deployment {deployment_id} is already completed with status: {current_status}")
                    return
                
                # Otherwise, keep the connection open for new logs (only if still in memory)
                last_log_count = len(deployment.get("logs", []))
                timeout_count = 0
                max_timeout = 300  # 5 minutes
                
                while deployment_id in deployments and timeout_count < max_timeout:
                    current_deployment = deployments[deployment_id]
                    current_logs = current_deployment.get("logs", [])
                    current_count = len(current_logs)
                    
                    # Send new logs
                    if current_count > last_log_count:
                        for i in range(last_log_count, current_count):
                            yield f"data: {json.dumps({'message': current_logs[i]})}\n\n"
                        last_log_count = current_count
                    
                    # Check if deployment status has changed
                    status = current_deployment.get("status", "running")
                    if status in ["success", "failed"]:
                        yield f"data: {json.dumps({'status': status})}\n\n"
                        break
                    
                    time.sleep(1)
                    timeout_count += 1
                
                if timeout_count >= max_timeout:
                    logger.warning(f"SSE stream timeout for deployment {deployment_id}")
                    yield f"data: {json.dumps({'error': 'Stream timeout'})}\n\n"
                    
            else:
                yield f"data: {json.dumps({'error': 'Deployment not found'})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    else:
        # Return regular JSON response for non-streaming requests
        deployment = find_deployment_with_retry(deployment_id)
        if deployment:
            return jsonify({
                "deploymentId": deployment_id,
                "logs": deployment.get("logs", []),
                "status": deployment.get("status", "unknown"),
                "timestamp": deployment.get("timestamp", 0),
                "type": deployment.get("type", "unknown")
            })
        else:
            logger.warning(f"Deployment {deployment_id} not found after all retry attempts")
            return jsonify({"error": "Deployment not found"}), 404


# API to get logs for a specific command
@app.route('/api/command/<command_id>/logs')
def get_command_logs(command_id):
    logger.info(f"Getting logs for command: {command_id}")
    
    # Check if client expects server-sent events
    accept_header = request.headers.get('Accept', '')
    if 'text/event-stream' in accept_header:
        # Return SSE stream for real-time logs
        def generate():
            if command_id in deployments:
                command = deployments[command_id]
                # First send all existing logs
                for log in command.get("logs", []):
                    yield f"data: {json.dumps({'message': log})}\n\n"

                # Send current status
                yield f"data: {json.dumps({'status': command.get('status', 'running')})}\n\n"

                # Return if command is already completed
                if command.get("status") in ["success", "failed"]:
                    return
                
                # Otherwise, keep the connection open for new logs
                last_log_count = len(command.get("logs", []))
                while command_id in deployments:
                    current_logs = deployments[command_id].get("logs", [])
                    current_count = len(current_logs)
                    
                    # Send new logs
                    if current_count > last_log_count:
                        for i in range(last_log_count, current_count):
                            yield f"data: {json.dumps({'message': current_logs[i]})}\n\n"
                        last_log_count = current_count
                    
                    # Check if command status has changed
                    status = deployments[command_id].get("status")
                    if status in ["success", "failed"]:
                        yield f"data: {json.dumps({'status': status})}\n\n"
                        break
                    
                    time.sleep(1)
            else:
                yield f"data: {json.dumps({'error': 'Command not found'})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    else:
        # Return regular JSON response for non-streaming requests
        if command_id in deployments:
            return jsonify({
                "logs": deployments[command_id].get("logs", []),
                "status": deployments[command_id].get("status", "unknown")
            })
        else:
            return jsonify({"error": "Command not found"}), 404

# Add a rollback endpoint
@app.route('/api/deploy/<deployment_id>/rollback', methods=['POST'])
def rollback_deployment(deployment_id):
    logger.info(f"Rolling back deployment with ID: {deployment_id}")

    # Get current authenticated user
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Authentication required"}), 401 
    
    if deployment_id not in deployments:
        logger.error(f"Deployment not found with ID: {deployment_id}")
        return jsonify({"error": "Deployment not found"}), 404
    
    deployment = deployments[deployment_id]
    
    if deployment["type"] != "file":
        logger.error(f"Cannot rollback non-file deployment type: {deployment['type']}")
        return jsonify({"error": "Only file deployments can be rolled back"}), 400
    
    # Generate a new deployment ID for the rollback operation
    rollback_id = str(uuid.uuid4())
    
    # Create a rollback deployment record
    deployments[rollback_id] = {
        "id": rollback_id,
        "type": "rollback",
        "original_deployment": deployment_id,
        "ft": deployment.get("ft"),
        "file": deployment.get("file"),
        "target_path": deployment.get("target_path"),
        "logged_in_user": current_user['username'],  # User who initiated the deployment
        "user_role": current_user['role'],  # Role of the user who initiated
        "vms": deployment.get("vms"),
        "user": deployment.get("user"),
        "sudo": deployment.get("sudo", False),
        "status": "running",
        "timestamp": time.time(),
        "logs": []
    }
    
    # Save deployment history
    save_deployment_history()
    
    # Start rollback in a separate thread
    threading.Thread(target=process_rollback, args=(rollback_id,)).start()
    
    logger.info(f"Rollback initiated with ID: {rollback_id}")
    return jsonify({"deploymentId": rollback_id})

    
def process_rollback(rollback_id):
    rollback = deployments[rollback_id]
    try:
        original_id = rollback["original_deployment"]
        vms = rollback["vms"]
        logged_in_user = rollback["logged_in_user"]  # User who initiated
        target_path = os.path.join(rollback["target_path"], rollback["file"])
        user = rollback["user"]
        sudo = rollback["sudo"]
        
        log_message(rollback_id, f"Starting rollback for deployment {original_id}")
        
        # Get current timestamp for backup naming
        timestamp = int(time.time())
        
        # Track overall rollback success
        overall_success = True
        failed_vms = []
        
        # Process rollback for each VM
        for vm_name in vms:
            vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
            if not vm:
                log_message(rollback_id, f"ERROR: VM {vm_name} not found in inventory")
                failed_vms.append(vm_name)
                overall_success = False
                continue
            
            # Generate rollback playbook
            playbook_file = f"/tmp/rollback_{rollback_id}_{vm_name}.yml"
            with open(playbook_file, 'w') as f:
                f.write(f"""---
- name: Rollback file deployment (backup and remove)
  hosts: {vm_name}
  gather_facts: false
  become: {"true" if sudo else "false"}
  become_user: {user}
  tasks:
    - name: Test connection
      ping:
    
    - name: Check if target file exists
      ansible.builtin.stat:
        path: "{target_path}"
      register: target_file_stat
    
    - name: Create backup of current file
      ansible.builtin.copy:
        src: "{target_path}"
        dest: "{target_path}_{timestamp}"
        remote_src: yes
        backup: no
      when: target_file_stat.stat.exists
      register: backup_result
    
    - name: Log backup creation
      ansible.builtin.debug:
        msg: "Created backup: {target_path}_{timestamp}"
      when: target_file_stat.stat.exists and backup_result.changed
    
    - name: Remove original file (rollback)
      ansible.builtin.file:
        path: "{target_path}"
        state: absent
      when: target_file_stat.stat.exists
      register: remove_result
    
    - name: Log file removal
      ansible.builtin.debug:
        msg: "Removed original file: {target_path}"
      when: target_file_stat.stat.exists and remove_result.changed
    
    - name: File not found
      ansible.builtin.debug:
        msg: "Target file {target_path} does not exist - nothing to rollback"
      when: not target_file_stat.stat.exists
""")
            
            # Generate inventory file
            inventory_file = f"/tmp/rollback_inventory_{rollback_id}_{vm_name}"
            with open(inventory_file, 'w') as f:
                f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'")
            
            # Run ansible playbook
            cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
            log_message(rollback_id, f"Running rollback on {vm_name}: backup and remove {target_path}")
            
            env_vars = os.environ.copy()
            env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
            env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
            env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
            env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)
            
            for line in process.stdout:
                log_message(rollback_id, line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                log_message(rollback_id, f"Rollback completed successfully on {vm_name}")
                log_message(rollback_id, f"File backed up as: {target_path}_{timestamp}")
            else:
                log_message(rollback_id, f"FAILED: Rollback failed on {vm_name} (exit code: {process.returncode})")
                failed_vms.append(vm_name)
                overall_success = False
            
            # Cleanup temporary files
            try:
                os.remove(playbook_file)
                os.remove(inventory_file)
            except Exception as cleanup_error:
                log_message(rollback_id, f"Warning: Could not cleanup temp files: {str(cleanup_error)}")
        
        # Update rollback status based on overall success
        if overall_success:
            deployments[rollback_id]["status"] = "success"
            deployments[rollback_id]["backup_timestamp"] = timestamp
            log_message(rollback_id, f"Rollback operation completed successfully on all VMs(initiated by {logged_in_user}) . Files backed up with timestamp: {timestamp}")
        else:
            deployments[rollback_id]["status"] = "failed"
            if failed_vms:
                log_message(rollback_id, f"Rollback FAILED on VMs: {', '.join(failed_vms)} (initiated by {logged_in_user})")
            log_message(rollback_id, "Rollback operation completed with failures")
        
        save_deployment_history()
        
    except Exception as e:
        log_message(rollback_id, f"ERROR: Exception during rollback: {str(e)} (initiated by {logged_in_user})")
        deployments[rollback_id]["status"] = "failed"
        logger.exception(f"Exception in rollback {rollback_id}: {str(e)}")
        save_deployment_history()


# API to clear deployment history
@app.route('/api/deployments/clear', methods=['POST'])
def clear_deployment_history():
    days = request.json.get('days', 30)
    logger.info(f"Clearing deployment logs older than {days} days")
    
    if days < 0:
        return jsonify({"error": "Days must be a positive number"}), 400
    
    # Calculate cutoff timestamp
    cutoff_time = time.time() - (days * 86400)  # 86400 seconds in a day
    
    # Count deployments before deletion
    initial_count = len(deployments)
    
    # Filter deployments to keep only those newer than the cutoff
    if days == 0:  # If days is 0, clear all logs
        deployments.clear()
    else:
        to_delete = []
        for deployment_id, deployment in deployments.items():
            try:
                # Get timestamp and convert to float if it's a string
                timestamp = deployment.get('timestamp', 0)
                if isinstance(timestamp, str):
                    # Try to convert string timestamp to float
                    try:
                        timestamp = float(timestamp)
                    except ValueError:
                        # If conversion fails, treat as very old (0)
                        timestamp = 0
                elif timestamp is None:
                    timestamp = 0
                
                # Compare with cutoff time
                if timestamp < cutoff_time:
                    to_delete.append(deployment_id)
                    
            except Exception as e:
                logger.warning(f"Error processing timestamp for deployment {deployment_id}: {e}")
                # If there's any error, consider it for deletion (treat as old)
                to_delete.append(deployment_id)
        
        # Delete the identified deployments
        for deployment_id in to_delete:
            try:
                del deployments[deployment_id]
            except KeyError:
                logger.warning(f"Deployment {deployment_id} was already deleted")
    
    # Count how many were deleted
    deleted_count = initial_count - len(deployments)
    
    # Save updated deployment history
    try:
        save_deployment_history()
    except Exception as e:
        logger.error(f"Error saving deployment history: {e}")
        return jsonify({"error": "Failed to save deployment history"}), 500
    
    return jsonify({
        "message": f"Successfully cleared {deleted_count} deployment logs",
        "deleted_count": deleted_count,
        "remaining_count": len(deployments)
    })



def get_current_timestamp():
    """Return current timestamp as float"""
    return time.time()

@app.route('/api/systemd/<operation>', methods=['POST'])
def systemd_operation(operation):
    # Get current authenticated user
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Authentication required"}), 401

    data = request.json
    operation = data.get('operation', operation).strip().lower()  # Use URL param or body param
    service = data.get('service')
    vms = data.get('vms')
    
    if not all([service, vms, operation]):
        logger.error("Missing required parameters for systemd operation")
        return jsonify({"error": "Missing required parameters"}), 400
    
    if operation not in ['start', 'stop', 'restart', 'status']:
        logger.error(f"Invalid systemd operation: {operation}")
        return jsonify({"error": "Invalid operation. Must be one of: start, stop, restart, status"}), 400
    
    # Generate a unique deployment ID
    deployment_id = str(uuid.uuid4())
    
    # Store deployment information
    deployments[deployment_id] = {
        "id": deployment_id,
        "type": "systemd",
        "service": service,
        "operation": operation,
        "logged_in_user": current_user['username'],  # User who initiated the deployment
        "user_role": current_user['role'],  # Role of the user who initiated
        "vms": vms,
        "status": "running",
        "timestamp": get_current_timestamp(),
        "logs": []
    }
    
    # Save deployment history
    save_deployment_history()
    
    # Start systemd operation in a separate thread
    threading.Thread(target=process_systemd_operation, args=(deployment_id, operation, service, vms)).start()
    
    logger.info(f"Systemd {operation} initiated with ID: {deployment_id} initiated by {current_user['username']}")
    return jsonify({"deploymentId": deployment_id, "initiatedBy": current_user['username']})


def process_systemd_operation(deployment_id, operation, service, vms):
    deployment = deployments[deployment_id]
    try:
        logged_in_user = deployment["logged_in_user"]  # User who initiated
        user = deployment.get("user", "infadm")
        log_message(deployment_id, f"Starting systemd {operation} for service '{service}' on {len(vms)} VMs (initiated by {logged_in_user})")
        
        # Generate an ansible playbook for systemd operation
        playbook_file = f"/tmp/systemd_{deployment_id}.yml"
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Systemd {operation} operation for {service} (initiated by {logged_in_user})
  hosts: systemd_targets
  gather_facts: true
#   become: true
  vars:
    service_name: "{service}"
    operation_type: "{operation}"
  tasks:
    - name: Test connection
      ansible.builtin.ping:
      
    - name: Check if service unit file exists
      ansible.builtin.stat:
        path: "/etc/systemd/system/{{{{ service_name }}}}"
      register: service_file_etc
      
    - name: Check if service unit file exists in lib
      ansible.builtin.stat:
        path: "/usr/lib/systemd/system/{{{{ service_name }}}}"
      register: service_file_lib
      
    - name: Check if service unit file exists in local
      ansible.builtin.stat:
        path: "/usr/local/lib/systemd/system/{{{{ service_name }}}}"
      register: service_file_local
      
    - name: Set service exists fact
      ansible.builtin.set_fact:
        service_exists: "{{{{ service_file_etc.stat.exists or service_file_lib.stat.exists or service_file_local.stat.exists }}}}"
        
    - name: Report if service doesn't exist
      ansible.builtin.debug:
        msg: "ERROR: Service '{{{{ service_name }}}}' unit file not found on {{{{ inventory_hostname }}}}"
      when: not service_exists
      
    - name: Get detailed service status
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: service_status
      when: service_exists
      failed_when: false
      
    - name: Get service status with systemctl
      ansible.builtin.shell: |
        systemctl status {{{{ service_name }}}} --no-pager -l || true
        echo "---SEPARATOR---"
        systemctl show {{{{ service_name }}}} --property=ActiveState,SubState,LoadState,UnitFileState,ExecMainStartTimestamp,ExecMainPID,MainPID || true
      register: service_details
      when: service_exists
      
    - name: Parse service uptime
      ansible.builtin.shell: |
        if systemctl is-active {{{{ service_name }}}} >/dev/null 2>&1; then
          start_time=$(systemctl show {{{{ service_name }}}} --property=ExecMainStartTimestamp --value)
          if [ -n "$start_time" ] && [ "$start_time" != "n/a" ]; then
            echo "Service started at: $start_time"
            # Calculate uptime
            start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo "0")
            current_epoch=$(date +%s)
            if [ "$start_epoch" -gt 0 ]; then
              uptime_seconds=$((current_epoch - start_epoch))
              uptime_days=$((uptime_seconds / 86400))
              uptime_hours=$(((uptime_seconds % 86400) / 3600))
              uptime_minutes=$(((uptime_seconds % 3600) / 60))
              echo "Uptime: ${{uptime_days}}d ${{uptime_hours}}h ${{uptime_minutes}}m"
            else
              echo "Uptime: Unable to calculate"
            fi
          else
            echo "Service start time: Not available"
            echo "Uptime: Not available"
          fi
        else
          echo "Service is not active"
        fi
      register: service_uptime
      when: service_exists
      
    - name: Display comprehensive service status
      ansible.builtin.debug:
        msg: |
          ===========================================
          SERVICE STATUS REPORT for {{{{ inventory_hostname }}}}
          ===========================================
          Service Name: {{{{ service_name }}}}
          Active State: {{{{ service_status.status.ActiveState | default('unknown') }}}}
          Sub State: {{{{ service_status.status.SubState | default('unknown') }}}}
          Load State: {{{{ service_status.status.LoadState | default('unknown') }}}}
          Unit File State: {{{{ service_status.status.UnitFileState | default('unknown') }}}}
          Main PID: {{{{ service_status.status.MainPID | default('N/A') }}}}
          
          {{{{ service_uptime.stdout | default('Uptime info not available') }}}}
          
          Status: {{{{ 'ACTIVE' if service_status.status.ActiveState == 'active' else 'INACTIVE/DEAD' }}}}
          Enabled: {{{{ 'YES' if service_status.status.UnitFileState in ['enabled', 'enabled-runtime'] else 'NO' }}}}
          ===========================================
      when: service_exists and operation_type == 'status'
      
    # - name: Perform systemd START operation
    #   ansible.builtin.systemd:
    #     name: "{{{{ service_name }}}}"
    #     state: started
    #     enabled: yes
    #   become: yes  
    #   register: start_result
    #   when: service_exists and operation_type == 'start'

    - name: Perform systemd START operation
      ansible.builtin.shell: |
        sudo systemctl start {{{{ service_name }}}}
      register: start_result
      when: service_exists and operation_type == 'start'
      
    # - name: Perform systemd STOP operation
    #   ansible.builtin.systemd:
    #     name: "{{{{ service_name }}}}"
    #     state: stopped
    #   become: yes  
    #   register: stop_result
    #   when: service_exists and operation_type == 'stop'

    - name: Perform systemd STOP operation
      ansible.builtin.shell: |
        sudo systemctl stop {{{{ service_name }}}}
      register: stop_result
      when: service_exists and operation_type == 'stop'
      
    # - name: Perform systemd RESTART operation
    #   ansible.builtin.systemd:
    #     name: "{{{{ service_name }}}}"
    #     state: restarted
    #     enabled: yes
    #   become: yes
    #   register: restart_result
    #   when: service_exists and operation_type == 'restart'

    - name: Perform systemd RESTART operation
      ansible.builtin.shell: |
        sudo systemctl restart {{{{ service_name }}}}
      register: restart_result
      when: service_exists and operation_type == 'restart'
      
    - name: Verify operation result
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: post_operation_status
      when: service_exists and operation_type in ['start', 'stop', 'restart']
      failed_when: false
      
    - name: Report operation success
      ansible.builtin.debug:
        msg: |
          ===========================================
          OPERATION RESULT for {{{{ inventory_hostname }}}}
          ===========================================
          Service: {{{{ service_name }}}}
          Operation: {{{{ operation_type | upper }}}}
          Result: SUCCESS
          New Status: {{{{ post_operation_status.status.ActiveState | default('unknown') }}}} ({{{{ post_operation_status.status.SubState | default('unknown') }}}})
          Enabled: {{{{ 'YES' if post_operation_status.status.UnitFileState in ['enabled', 'enabled-runtime'] else 'NO' }}}}
          ===========================================
      when: service_exists and operation_type in ['start', 'stop', 'restart']
      
    - name: Get final service status for logging
      ansible.builtin.shell: systemctl is-active {{{{ service_name }}}} || echo "inactive"
      register: final_status
      when: service_exists
      
    - name: Log final status
      ansible.builtin.debug:
        msg: "Final service status on {{{{ inventory_hostname }}}}: {{{{ final_status.stdout | default('unknown') }}}}"
      when: service_exists
""")

        # Generate inventory file for ansible
        inventory_file = f"/tmp/inventory_{deployment_id}"
        
        with open(inventory_file, 'w') as f:
            f.write("[systemd_targets]\n")
            for vm_name in vms:
                # Find VM IP from inventory
                vm = next((v for v in inventory["vms"] if v["name"] == vm_name), None)
                if vm:
                    f.write(f"{vm_name} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPath=/tmp/ansible-ssh/%h-%p-%r -o ControlPersist=60s'\n")
        
        # Run ansible playbook
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
        
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")
        logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
        # Use subprocess.run with capture_output=True instead of Popen
        result = subprocess.run(cmd, capture_output=True, text=True, env=env_vars, timeout=300)
        
        # Log the output line by line
        if result.stdout:
            log_message(deployment_id, "=== ANSIBLE OUTPUT ===")
            for line in result.stdout.splitlines():
                if line.strip():  # Only log non-empty lines
                    log_message(deployment_id, line.strip())
        
        if result.stderr:
            log_message(deployment_id, "=== ANSIBLE STDERR ===")
            for line in result.stderr.splitlines():
                if line.strip():  # Only log non-empty lines
                    log_message(deployment_id, line.strip())
        
        # Check result and update status
        if result.returncode == 0:
            log_message(deployment_id, f"SUCCESS: Systemd {operation} operation completed successfully (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "completed"
            logger.info(f"Systemd operation {deployment_id} completed successfully (initiated by {logged_in_user})")
        else:
            log_message(deployment_id, f"ERROR: Systemd {operation} operation failed with return code {result.returncode} (initiated by {logged_in_user})")
            deployments[deployment_id]["status"] = "failed"
            logger.error(f"Systemd operation {deployment_id} failed with return code {result.returncode} (initiated by {logged_in_user})")
        
        # Clean up temporary files
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # Save deployment history after completion
        save_deployment_history()
        
    except subprocess.TimeoutExpired:
        log_message(deployment_id, f"ERROR: Systemd {operation} operation timed out after 5 minutes")
        deployments[deployment_id]["status"] = "failed"
        logger.error(f"Systemd operation {deployment_id} timed out")
        save_deployment_history()
        
    except Exception as e:
        log_message(deployment_id, f"ERROR: Exception during systemd operation: {str(e)}")
        deployments[deployment_id]["status"] = "failed"
        logger.exception(f"Exception in systemd operation {deployment_id}: {str(e)}")
        save_deployment_history()

if __name__ == '__main__':
    from waitress import serve
    logger.info("Starting Fix Deployment Orchestrator")
    
    # Ensure required directories exist
    os.makedirs('/tmp/ansible-ssh', exist_ok=True)
    # os.chmod('/tmp/ansible-ssh', 0o777)
    try:
        os.chmod('/tmp/ansible-ssh', 0o777)  # Set proper permissions for ansible control path
    except PermissionError:
        logger.info("Could not set permissions on /tmp/ansible-ssh - continuing with existing permissions")
    logger.info("Ensured ansible control path directory exists with permissions 777")
    
    # Print SSH key information for debugging
    logger.info("Checking SSH key setup...")
    check_ssh_setup()
    
    serve(app, host="0.0.0.0", port=5000)
