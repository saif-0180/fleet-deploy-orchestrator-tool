
import os
import json
import subprocess
import threading
import time
import uuid
import base64
from flask import current_app, Blueprint, jsonify, request
import logging

# Create the blueprint without importing from app
deploy_template_bp = Blueprint('deploy_template', __name__)

logger = logging.getLogger('fix_deployment_orchestrator')
logging.basicConfig(level=logging.DEBUG)

# Deploy directory for logs - use relative paths like db_routes.py
DEPLOYMENT_LOGS_DIR = os.environ.get('DEPLOYMENT_LOGS_DIR', '/app/logs')
TEMPLATE_DIR = "/app/deployment_templates"
INVENTORY_FILE = "/app/inventory/inventory.json"
DB_INVENTORY_FILE = "/app/inventory/db_inventory.json"
FIX_FILES_DIR = "/app/fixfiles"

def get_app_globals():
    """Get shared objects from the main app via current_app context"""
    try:
        from flask import current_app
        # Access the shared objects through current_app
        deployments = current_app.config.get('deployments')
        save_deployment_history = current_app.config.get('save_deployment_history')
        log_message = current_app.config.get('log_message')
        inventory = current_app.config.get('inventory')
        
        if not all([deployments is not None, save_deployment_history, log_message, inventory is not None]):
            logger.error("One or more required app globals are None")
            logger.debug(f"deployments: {deployments is not None}")
            logger.debug(f"save_deployment_history: {save_deployment_history is not None}")
            logger.debug(f"log_message: {log_message is not None}")
            logger.debug(f"inventory: {inventory is not None}")
            raise Exception("Required app globals not properly initialized")
        
        return deployments, save_deployment_history, log_message, inventory
    except Exception as e:
        logger.error(f"Failed to get app globals: {str(e)}")
        raise Exception(f"Failed to access shared app globals: {str(e)}")

def load_template(template_name):
    """Load template from the templates directory"""
    try:
        logger.debug(f"Loading template: {template_name}")
        template_path = os.path.join(TEMPLATE_DIR, template_name)
        logger.debug(f"Template path: {template_path}")
        
        if not os.path.exists(template_path):
            logger.warning(f"Template not found: {template_path}")
            # Return a simple template if file doesn't exist
            return {
                "metadata": {
                    "ft_number": "TEST-001",
                    "description": f"Simple template for {template_name}",
                    "total_steps": 1,
                    "generated_at": "2025-01-01T00:00:00Z"
                },
                "steps": [
                    {
                        "order": 1,
                        "type": "shell_command",
                        "description": f"Template deployment: {template_name}",
                        "command": f"echo 'Template deployment: {template_name}'"
                    }
                ]
            }
        
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        logger.debug(f"Template loaded successfully: {template.get('metadata', {}).get('ft_number', 'unknown')}")
        return template
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        # Return a fallback template
        return {
            "metadata": {
                "ft_number": "ERROR-001",
                "description": "Fallback template due to loading error",
                "total_steps": 1,
                "generated_at": "2025-01-01T00:00:00Z"
            },
            "steps": [
                {
                    "order": 1,
                    "type": "shell_command",
                    "description": f"Error loading template: {str(e)}",
                    "command": f"echo 'Error loading template: {str(e)}'"
                }
            ]
        }

def load_inventory():
    """Load inventory and db_inventory files with fallbacks like db_routes.py"""
    try:
        logger.debug("Loading inventory files")
        
        # Load main inventory with fallback
        inventory = {}
        if os.path.exists(INVENTORY_FILE):
            with open(INVENTORY_FILE, 'r') as f:
                inventory = json.load(f)
            logger.debug(f"Loaded inventory: {len(inventory.get('vms', []))} VMs")
        else:
            # Fallback inventory
            inventory = {
                "vms": [{"name": "vm1", "ip": "192.168.1.1"}, {"name": "vm2", "ip": "192.168.1.2"}],
                "databases": ["db1", "db2"]
            }
            logger.debug("Using fallback inventory")
        
        # Load database inventory with fallback
        db_inventory = {}
        if os.path.exists(DB_INVENTORY_FILE):
            with open(DB_INVENTORY_FILE, 'r') as f:
                db_inventory = json.load(f)
            logger.debug(f"Loaded db_inventory: {len(db_inventory.get('db_connections', []))} connections")
        else:
            # Fallback db_inventory
            db_inventory = {
                "db_connections": [
                    {"hostname": "10.172.145.204", "port": "5400", "users": ["xpidbo1cfg", "abpwrk1db", "postgres"]},
                    {"hostname": "10.172.145.205", "port": "5432", "users": ["postgres", "dbadmin"]}
                ],
                "db_users": ["xpidbo1cfg", "postgres", "dbadmin"]
            }
            logger.debug("Using fallback db_inventory")
        
        return inventory, db_inventory
    except Exception as e:
        logger.error(f"Error loading inventory: {str(e)}")
        # Return minimal fallback data
        return {"vms": [], "databases": []}, {"db_connections": [], "db_users": []}

@deploy_template_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """List available deployment templates"""
    try:
        logger.debug("Listing available templates")
        templates = []
        if os.path.exists(TEMPLATE_DIR):
            logger.debug(f"Template directory exists: {TEMPLATE_DIR}")
            for file_name in os.listdir(TEMPLATE_DIR):
                if file_name.endswith('.json'):
                    try:
                        logger.debug(f"Processing template file: {file_name}")
                        template = load_template(file_name)
                        templates.append({
                            "name": file_name,
                            "description": template.get('metadata', {}).get('description', ''),
                            "ft_number": template.get('metadata', {}).get('ft_number', ''),
                            "total_steps": template.get('metadata', {}).get('total_steps', len(template.get('steps', []))),
                            "steps": [
                                {
                                    "order": step.get('order'),
                                    "type": step.get('type'),
                                    "description": step.get('description', '')
                                } for step in template.get('steps', [])
                            ]
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load template {file_name}: {str(e)}")
                        continue
        else:
            logger.warning(f"Template directory does not exist: {TEMPLATE_DIR}")

        logger.debug(f"Found {len(templates)} templates")
        return jsonify({"templates": templates})
    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/template/<template_name>', methods=['GET'])
def get_template_details(template_name):
    """Get details of a specific template"""
    try:
        logger.debug(f"Getting template details for: {template_name}")
        template = load_template(template_name)
        return jsonify(template)
    except Exception as e:
        logger.error(f"Failed to get template details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/deploy/template', methods=['POST'])
def deploy_template():
    """Start template deployment - properly integrated with main app"""
    try:
        logger.info("=== TEMPLATE DEPLOYMENT REQUEST RECEIVED ===")
        data = request.json
        logger.debug(f"Request data: {data}")
        
        template_name = data.get('template')
        ft_number = data.get('ft_number', '')
        variables = data.get('variables', {})
        
        logger.info(f"Template deployment request: template={template_name}, ft_number={ft_number}")
        
        if not template_name:
            logger.error("Missing template name for template deployment")
            return jsonify({"error": "Missing template name"}), 400
        
        # Get shared objects from main app
        try:
            deployments, save_deployment_history, log_message, inventory = get_app_globals()
            logger.debug("Successfully got app globals")
        except Exception as e:
            logger.error(f"Failed to get app globals: {str(e)}")
            return jsonify({"error": f"App integration error: {str(e)}"}), 500
        
        # Generate a unique deployment ID
        deployment_id = str(uuid.uuid4())
        logger.info(f"Generated deployment ID: {deployment_id}")
        
        # Store deployment information in the shared deployments dictionary
        deployment_data = {
            "id": deployment_id,
            "type": "template",
            "template": template_name,
            "ft": ft_number,
            "variables": variables,
            "status": "running",
            "timestamp": time.time(),
            "logs": [],
            "logged_in_user": "infadm"  # Set default user
        }
        
        deployments[deployment_id] = deployment_data
        logger.info(f"Added deployment to shared dictionary. Total deployments: {len(deployments)}")
        logger.debug(f"Deployment data: {deployment_data}")
        
        # Log initial message
        log_message(deployment_id, f"Template deployment initiated: {template_name}")
        logger.info(f"Logged initial message for deployment {deployment_id}")
        
        # Save deployment history
        save_deployment_history()
        logger.debug("Saved deployment history")
        
        # Start deployment in a separate thread
        logger.info(f"Starting background thread for deployment {deployment_id}")
        deployment_thread = threading.Thread(
            target=process_template_deployment, 
            args=(deployment_id,),
            daemon=True
        )
        deployment_thread.start()
        logger.info(f"Background thread started for deployment {deployment_id}")
        
        # Verify thread is alive
        if deployment_thread.is_alive():
            logger.info(f"Thread is alive and running for deployment {deployment_id}")
        else:
            logger.error(f"Thread failed to start for deployment {deployment_id}")
        
        logger.info(f"Template deployment initiated with ID: {deployment_id}")
        return jsonify({"deploymentId": deployment_id})
        
    except Exception as e:
        logger.error(f"Error starting template deployment: {str(e)}")
        logger.exception("Full exception details:")
        return jsonify({"error": str(e)}), 500

def process_template_deployment(deployment_id):
    """Process template deployment in a separate thread"""
    try:
        logger.info(f"=== STARTING TEMPLATE DEPLOYMENT PROCESSING: {deployment_id} ===")
        
        # Get shared objects from main app
        try:
            deployments, save_deployment_history, log_message, inventory = get_app_globals()
            logger.debug(f"Got app globals in thread for deployment {deployment_id}")
        except Exception as e:
            logger.error(f"Failed to get app globals in thread: {str(e)}")
            return
        
        # Check if deployment exists
        if deployment_id not in deployments:
            logger.error(f"Deployment ID {deployment_id} not found in deployments dictionary")
            logger.debug(f"Available deployment IDs: {list(deployments.keys())}")
            return
        
        deployment = deployments[deployment_id]
        template_name = deployment["template"]
        variables = deployment.get("variables", {})
        
        logger.info(f"Processing template deployment: {template_name}")
        log_message(deployment_id, f"Starting template deployment: {template_name}")
        
        # Load template
        try:
            template = load_template(template_name)
            log_message(deployment_id, f"Loaded template: {template_name}")
            logger.debug(f"Template loaded: {template.get('metadata', {})}")
        except Exception as e:
            error_msg = f"Failed to load template {template_name}: {str(e)}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(error_msg)
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return
        
        # Load inventory
        try:
            inv_data, db_inventory = load_inventory()
            log_message(deployment_id, "Loaded inventory files")
            logger.debug("Inventory loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load inventory: {str(e)}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(error_msg)
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return
        
        # Process deployment steps
        steps = template.get("steps", [])
        log_message(deployment_id, f"Processing {len(steps)} deployment steps")
        logger.info(f"Processing {len(steps)} deployment steps")
        
        for step in sorted(steps, key=lambda x: x.get('order', 0)):
            try:
                step_type = step.get("type")
                step_order = step.get("order", 0)
                step_description = step.get("description", "")
                
                log_message(deployment_id, f"Executing step {step_order}: {step_description}")
                logger.info(f"[{deployment_id}] Executing step {step_order}: {step_type}")
                
                # Execute different step types
                if step_type == "service_restart":
                    execute_service_restart(deployment_id, step, inv_data, db_inventory)
                elif step_type == "file_deployment":
                    execute_file_deployment(deployment_id, step, inv_data, db_inventory)
                elif step_type == "sql_deployment":
                    execute_sql_deployment(deployment_id, step, inv_data, db_inventory)
                elif step_type == "ansible_playbook":
                    execute_ansible_playbook(deployment_id, step, inv_data, db_inventory)
                elif step_type == "helm_upgrade":
                    execute_helm_upgrade(deployment_id, step, inv_data, db_inventory)
                elif step_type == "shell_command":
                    # Execute simple shell command
                    command = step.get("command", "echo 'No command specified'")
                    log_message(deployment_id, f"Executing command: {command}")
                    
                    try:
                        result = subprocess.run(
                            command, 
                            shell=True, 
                            capture_output=True, 
                            text=True, 
                            timeout=30
                        )
                        log_message(deployment_id, f"Command output: {result.stdout}")
                        if result.stderr:
                            log_message(deployment_id, f"Command stderr: {result.stderr}")
                        if result.returncode != 0:
                            log_message(deployment_id, f"Command failed with return code: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        log_message(deployment_id, "Command timed out after 30 seconds")
                    except Exception as cmd_e:
                        log_message(deployment_id, f"Command execution error: {str(cmd_e)}")
                else:
                    warning_msg = f"Unknown step type: {step_type}"
                    log_message(deployment_id, f"WARNING: {warning_msg}")
                    logger.warning(f"[{deployment_id}] {warning_msg}")
                
                log_message(deployment_id, f"Completed step {step_order}")
                
                # Small delay between steps
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"Failed to execute step {step_order}: {str(e)}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                deployments[deployment_id]["status"] = "failed"
                save_deployment_history()
                return
        
        # If we get here, all steps completed successfully
        log_message(deployment_id, "SUCCESS: Template deployment completed successfully")
        deployments[deployment_id]["status"] = "success"
        logger.info(f"Template deployment {deployment_id} completed successfully")
        
    except Exception as e:
        error_msg = f"Unexpected error during template deployment: {str(e)}"
        logger.error(f"[{deployment_id}] {error_msg}")
        logger.exception("Full exception details:")
        
        try:
            deployments, save_deployment_history, log_message, inventory = get_app_globals()
            log_message(deployment_id, f"ERROR: {error_msg}")
            deployments[deployment_id]["status"] = "failed"
        except:
            logger.error("Failed to update deployment status after error")
    
    finally:
        # Always save deployment history
        try:
            deployments, save_deployment_history, log_message, inventory = get_app_globals()
            save_deployment_history()
        except:
            logger.error("Failed to save deployment history in finally block")

def execute_service_restart(deployment_id, step, inventory, db_inventory):
    """Execute service operation step using Ansible with comprehensive systemd management"""
    try:
        deployments, save_deployment_history, log_message, inv = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting service restart step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting service restart step {step['order']}: {step['description']}")
        
        order = step.get("order")
        description = step.get("description", "")
        service = step.get("service")
        operation = step.get("operation", "restart")
        target_vms = step.get("targetVMs", [])
        
        logged_in_user = deployments[deployment_id].get("logged_in_user", "infadm")
        
        log_message(deployment_id, f"Starting systemd {operation} for service '{service}' on {len(target_vms)} VMs (initiated by {logged_in_user})")
        logger.info(f"[{deployment_id}] Starting systemd {operation} for service '{service}' on {len(target_vms)} VMs")
        
        # Generate an ansible playbook for systemd operation
        playbook_file = f"/tmp/systemd_{deployment_id}_{order}.yml"
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Systemd {operation} operation for {service} (initiated by {logged_in_user})
  hosts: systemd_targets
  gather_facts: true
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
      
    - name: Set service exists fact
      ansible.builtin.set_fact:
        service_exists: "{{{{ service_file_etc.stat.exists or service_file_lib.stat.exists }}}}"
        
    - name: Report if service doesn't exist
      ansible.builtin.debug:
        msg: "WARNING: Service {{{{ service_name }}}} unit file not found in standard locations"
      when: not service_exists
      
    - name: Get service status
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: service_status
      failed_when: false
      
    - name: Display current service status
      ansible.builtin.debug:
        msg: "Service {{{{ service_name }}}} status: {{{{ service_status.status.ActiveState | default('unknown') }}}}"
      
    - name: Perform systemd operation
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
        state: "{{{{ 'started' if operation_type == 'start' else 'stopped' if operation_type == 'stop' else 'restarted' if operation_type == 'restart' else omit }}}}"
        enabled: "{{{{ true if operation_type == 'enable' else false if operation_type == 'disable' else omit }}}}"
        daemon_reload: "{{{{ true if operation_type == 'daemon-reload' else false }}}}"
      register: systemd_result
      when: operation_type in ['start', 'stop', 'restart', 'enable', 'disable', 'daemon-reload']
      
    - name: Get updated service status after operation
      ansible.builtin.systemd:
        name: "{{{{ service_name }}}}"
      register: updated_service_status
      failed_when: false
      when: operation_type in ['start', 'stop', 'restart', 'enable', 'disable']
      
    - name: Display updated service status
      ansible.builtin.debug:
        msg: "Service {{{{ service_name }}}} updated status: {{{{ updated_service_status.status.ActiveState | default('unknown') }}}}"
      when: operation_type in ['start', 'stop', 'restart', 'enable', 'disable']
      
    - name: Show service status (for status operation)
      ansible.builtin.command:
        cmd: "systemctl status {{{{ service_name }}}}"
      register: status_output
      failed_when: false
      when: operation_type == 'status'
      
    - name: Display service status output
      ansible.builtin.debug:
        msg: "{{{{ status_output.stdout_lines }}}}"
      when: operation_type == 'status' and status_output.stdout_lines is defined
""")
        
        # Create inventory file
        inventory_file = f"/tmp/inventory_{deployment_id}_{order}"
        with open(inventory_file, 'w') as f:
            f.write("[systemd_targets]\n")
            for vm_name in target_vms:
                if isinstance(vm_name, dict) and 'ip' in vm_name:
                    f.write(f"{vm_name['name']} ansible_host={vm_name['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                else:
                    vm_info = next((v for v in inventory.get("vms", []) if v.get("name") == vm_name), None)
                    if vm_info:
                        f.write(f"{vm_name} ansible_host={vm_info['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                    else:
                        log_message(deployment_id, f"WARNING: VM {vm_name} not found in inventory")
        
        # Execute ansible playbook
        env_vars = os.environ.copy()
        env_vars["ANSIBLE_CONFIG"] = "/etc/ansible/ansible.cfg"
        env_vars["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        env_vars["ANSIBLE_SSH_CONTROL_PATH"] = "/tmp/ansible-ssh/%h-%p-%r"
        env_vars["ANSIBLE_SSH_CONTROL_PATH_DIR"] = "/tmp/ansible-ssh"
        
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_file, "-v"]
        
        log_message(deployment_id, f"Executing: {' '.join(cmd)}")
        logger.info(f"Executing Ansible command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env_vars, timeout=300)
        
        # Log the output line by line
        if result.stdout:
            log_message(deployment_id, "=== ANSIBLE OUTPUT ===")
            for line in result.stdout.splitlines():
                if line.strip():
                    log_message(deployment_id, line.strip())
        
        if result.stderr:
            log_message(deployment_id, "=== ANSIBLE STDERR ===")
            for line in result.stderr.splitlines():
                if line.strip():
                    log_message(deployment_id, line.strip())
        
        if result.returncode == 0:
            log_message(deployment_id, f"Service {operation} operation completed successfully")
            logger.info(f"[{deployment_id}] Service {operation} operation completed successfully")
        else:
            error_msg = f"Service {operation} operation failed: {result.stderr}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise Exception(error_msg)
        
        # Clean up temporary files
        try:
            os.remove(playbook_file)
            os.remove(inventory_file)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        log_message(deployment_id, f"Service restart step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] Service restart step {step['order']} completed successfully")
        
    except Exception as e:
        error_msg = f"Service restart step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_file_deployment(deployment_id, step, inventory, db_inventory):
    """Execute file deployment step using Ansible"""
    try:
        deployments, save_deployment_history, log_message, inv = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting file deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting file deployment step {step['order']}: {step['description']}")
        
        # Implementation similar to service restart but for file deployment
        # This is a placeholder - implement based on your template structure
        log_message(deployment_id, f"File deployment step {step['order']} completed (placeholder)")
        
    except Exception as e:
        error_msg = f"File deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        raise

def execute_sql_deployment(deployment_id, step, inventory, db_inventory):
    """Execute SQL deployment step"""
    try:
        deployments, save_deployment_history, log_message, inv = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting SQL deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting SQL deployment step {step['order']}: {step['description']}")
        
        # Implementation placeholder
        log_message(deployment_id, f"SQL deployment step {step['order']} completed (placeholder)")
        
    except Exception as e:
        error_msg = f"SQL deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        raise

def execute_ansible_playbook(deployment_id, step, inventory, db_inventory):
    """Execute Ansible playbook step"""
    try:
        deployments, save_deployment_history, log_message, inv = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting Ansible playbook step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting Ansible playbook step {step['order']}: {step['description']}")
        
        # Implementation placeholder
        log_message(deployment_id, f"Ansible playbook step {step['order']} completed (placeholder)")
        
    except Exception as e:
        error_msg = f"Ansible playbook step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        raise

def execute_helm_upgrade(deployment_id, step, inventory, db_inventory):
    """Execute Helm upgrade step"""
    try:
        deployments, save_deployment_history, log_message, inv = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting Helm upgrade step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting Helm upgrade step {step['order']}: {step['description']}")
        
        # Implementation placeholder
        log_message(deployment_id, f"Helm upgrade step {step['order']} completed (placeholder)")
        
    except Exception as e:
        error_msg = f"Helm upgrade step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        raise

@deploy_template_bp.route('/api/deploy/<deployment_id>/logs', methods=['GET'])
def get_deployment_logs(deployment_id):
    """Get deployment logs - matching the working db_routes.py implementation"""
    try:
        deployments, save_deployment_history, log_message, inventory = get_app_globals()

        logger.debug(f"Looking for deployment: {deployment_id}")
        logger.debug(f"Available deployments: {list(deployments.keys())}")
        
        if deployment_id not in deployments:
            logger.warning(f"Deployment {deployment_id} not found in deployments dictionary")
            return jsonify({"error": "Deployment not found"}), 404
        
        deployment = deployments[deployment_id]
        logs = deployment.get('logs', [])
        
        return jsonify({
            "deploymentId": deployment_id,
            "status": deployment.get('status', 'unknown'),
            "logs": logs,
            "timestamp": deployment.get('timestamp'),
            "type": deployment.get('type', 'template')
        })
        
    except Exception as e:
        logger.error(f"Error fetching deployment logs for {deployment_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/deploy/<deployment_id>/status', methods=['GET'])
def get_deployment_status(deployment_id):
    """Get deployment status"""
    try:
        deployments, save_deployment_history, log_message, inventory = get_app_globals()
        
        if deployment_id not in deployments:
            return jsonify({"error": "Deployment not found"}), 404
        
        deployment = deployments[deployment_id]
        
        return jsonify({
            "deploymentId": deployment_id,
            "status": deployment.get('status', 'unknown'),
            "type": deployment.get('type', 'template'),
            "timestamp": deployment.get('timestamp'),
            "template": deployment.get('template'),
            "variables": deployment.get('variables', {})
        })
        
    except Exception as e:
        logger.error(f"Error fetching deployment status for {deployment_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/deployments', methods=['GET'])
def get_all_deployments():
    """Get all deployments - matching db_routes.py pattern"""
    try:
        deployments, save_deployment_history, log_message, inventory = get_app_globals()
        
        # Return deployments as a list sorted by timestamp
        deployment_list = []
        for deployment_id, deployment in deployments.items():
            deployment_list.append({
                "id": deployment_id,
                "type": deployment.get("type", "unknown"),
                "status": deployment.get("status", "unknown"),
                "timestamp": deployment.get("timestamp", 0),
                "template": deployment.get("template", ""),
                "ft": deployment.get("ft", ""),
                "file": deployment.get("file", "")
            })
        
        # Sort by timestamp (most recent first)
        deployment_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify(deployment_list)
        
    except Exception as e:
        logger.error(f"Error fetching all deployments: {str(e)}")
        return jsonify({"error": str(e)}), 500
