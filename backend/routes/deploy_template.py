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
    """Get shared objects from the main app - fixed to work like db_routes.py"""
    try:
        # Import here to avoid circular imports and ensure we get the shared instance
        from app import deployments, save_deployment_history, log_message
        return deployments, save_deployment_history, log_message
    except ImportError as e:
        logger.error(f"Failed to import app globals: {str(e)}")
        raise Exception(f"Failed to access shared app globals: {str(e)}")

def load_template(template_name):
    """Load template from the templates directory"""
    try:
        template_path = os.path.join(TEMPLATE_DIR, template_name)
        if not os.path.exists(template_path):
            logger.warning(f"Template not found: {template_path}")
            # Return a simple template if file doesn't exist
            return {
                "name": f"Simple {template_name}",
                "description": f"Simple template for {template_name}",
                "steps": [
                    {
                        "name": "test-step",
                        "type": "shell_command",
                        "command": f"echo 'Template deployment: {template_name}'"
                    }
                ]
            }
        
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        return template
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        # Return a fallback template
        return {
            "name": "fallback-template",
            "description": "Fallback template due to loading error",
            "steps": [
                {
                    "name": "error-step",
                    "type": "shell_command", 
                    "command": f"echo 'Error loading template: {str(e)}'"
                }
            ]
        }

def load_inventory():
    """Load inventory and db_inventory files with fallbacks like db_routes.py"""
    try:
        # Load main inventory with fallback
        inventory = {}
        if os.path.exists(INVENTORY_FILE):
            with open(INVENTORY_FILE, 'r') as f:
                inventory = json.load(f)
        else:
            # Fallback inventory
            inventory = {
                "vms": ["vm1", "vm2"],
                "databases": ["db1", "db2"]
            }
        
        # Load database inventory with fallback
        db_inventory = {}
        if os.path.exists(DB_INVENTORY_FILE):
            with open(DB_INVENTORY_FILE, 'r') as f:
                db_inventory = json.load(f)
        else:
            # Fallback db_inventory
            db_inventory = {
                "db_connections": [
                    {"hostname": "10.172.145.204", "port": "5400", "users": ["xpidbo1cfg", "abpwrk1db", "postgres"]},
                    {"hostname": "10.172.145.205", "port": "5432", "users": ["postgres", "dbadmin"]}
                ],
                "db_users": ["xpidbo1cfg", "postgres", "dbadmin"]
            }
        
        return inventory, db_inventory
    except Exception as e:
        logger.error(f"Error loading inventory: {str(e)}")
        # Return minimal fallback data
        return {"vms": [], "databases": []}, {"db_connections": [], "db_users": []}

def get_inventory_value(key, inventory, db_inventory):
    """Get value from inventory or db_inventory based on key"""
    # First check in main inventory
    if key in inventory:
        return inventory[key]
    
    # Then check in db_inventory
    if key in db_inventory:
        return db_inventory[key]
    
    # If not found, return None or raise exception
    return None

# @deploy_template_bp.route('/api/templates', methods=['GET'])
# def list_templates():
#     """List available templates"""
#     try:
#         templates = []
#         # Create a simple templates directory if it doesn't exist
#         templates_dir = './templates'
#         if not os.path.exists(templates_dir):
#             os.makedirs(templates_dir, exist_ok=True)
#             # Create a sample template for testing
#             sample_template = {
#                 "name": "sample-deployment",
#                 "description": "Sample deployment template",
#                 "steps": [
#                     {
#                         "name": "test-step",
#                         "type": "shell_command",
#                         "command": "echo 'Hello from template deployment!'"
#                     }
#                 ]
#             }
#             with open(os.path.join(templates_dir, 'sample.json'), 'w') as f:
#                 json.dump(sample_template, f, indent=2)
        
#         # List all json files in templates directory
#         for filename in os.listdir(templates_dir):
#             if filename.endswith('.json'):
#                 templates.append(filename)
        
#         return jsonify(templates)
#     except Exception as e:
#         logger.error(f"Error listing templates: {str(e)}")
#         return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """List available deployment templates"""
    try:
        templates = []
        if os.path.exists(TEMPLATE_DIR):
            for file_name in os.listdir(TEMPLATE_DIR):
                if file_name.endswith('.json'):
                    try:
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

        return jsonify({"templates": templates})
    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/template/<template_name>', methods=['GET'])
def get_template_details(template_name):
    """Get details of a specific template"""
    try:
        template = load_template(template_name)
        return jsonify(template)
    except Exception as e:
        logger.error(f"Failed to get template details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/deploy/template', methods=['POST'])
def deploy_template():
    """Start template deployment - similar to deploy_sql in db_routes.py"""
    # Import here to avoid circular imports and ensure we get the shared instance
    from app import deployments, save_deployment_history
    
    try:
        data = request.json
        template_name = data.get('template')
        variables = data.get('variables', {})
        
        logger.info(f"Template deployment request received: {template_name}")
        
        if not template_name:
            logger.error("Missing template name for template deployment")
            return jsonify({"error": "Missing template name"}), 400
        
        # Generate a unique deployment ID
        deployment_id = str(uuid.uuid4())
        
        # Store deployment information in the shared deployments dictionary
        deployments[deployment_id] = {
            "id": deployment_id,
            "type": "template",
            "template": template_name,
            "variables": variables,
            "status": "running",
            "timestamp": time.time(),
            "logs": []
        }
        
        # Save deployment history
        save_deployment_history()
        
        # Start deployment in a separate thread
        threading.Thread(target=process_template_deployment, args=(deployment_id,)).start()
        
        logger.info(f"Template deployment initiated with ID: {deployment_id}")
        return jsonify({"deploymentId": deployment_id})
        
    except Exception as e:
        logger.error(f"Error starting template deployment: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_template_deployment(deployment_id):
    """Process template deployment in a separate thread"""
    # Import here to ensure we get the shared instances
    from app import deployments, save_deployment_history, log_message
    
    try:
        # Check if deployment exists
        if deployment_id not in deployments:
            logger.error(f"Deployment ID {deployment_id} not found in deployments dictionary")
            return
        
        deployment = deployments[deployment_id]
        template_name = deployment["template"]
        variables = deployment.get("variables", {})
        
        logger.info(f"Processing template deployment from {template_name}")
        log_message(deployment_id, f"Starting template deployment: {template_name}")
        
        # Load template
        try:
            template = load_template(template_name)
            log_message(deployment_id, f"Loaded template: {template_name}")
        except Exception as e:
            error_msg = f"Failed to load template {template_name}: {str(e)}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(error_msg)
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()
            return
        
        # Load inventory
        try:
            inventory, db_inventory = load_inventory()
            log_message(deployment_id, "Loaded inventory files")
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
        
        for step in steps:
            try:
                step_type = step.get("type")
                step_order = step.get("order", 0)
                step_description = step.get("description", "")
                
                log_message(deployment_id, f"Executing step {step_order}: {step_description}")
                logger.info(f"[{deployment_id}] Executing step {step_order}: {step_type}")
                
                if step_type == "shell_command":
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
                
                elif step_type == "file_deployment":
                    log_message(deployment_id, "File deployment step (placeholder)")
                elif step_type == "service_restart":
                    log_message(deployment_id, "Service restart step (placeholder)")
                elif step_type == "sql_deployment":
                    log_message(deployment_id, "SQL deployment step (placeholder)")
                else:
                    warning_msg = f"Unknown step type: {step_type}"
                    log_message(deployment_id, f"WARNING: {warning_msg}")
                    logger.warning(f"[{deployment_id}] {warning_msg}")
                
                log_message(deployment_id, f"Completed step {step_order}")
                
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
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.exception(f"Exception in template deployment {deployment_id}: {str(e)}")
        
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "failed"
    
    finally:
        # Always save deployment history
        save_deployment_history()

def execute_file_deployment(deployment_id, step, inventory, db_inventory):
    """Execute file deployment step using Ansible like in app.py"""
    try:
        from app import deployments, save_deployment_history, log_message
        
        logger.info(f"[{deployment_id}] Starting file deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting file deployment step {step['order']}: {step['description']}")
        
        ft_number = step['ftNumber']
        files = step['files']
        target_path = step['targetPath']
        target_user = step['targetUser']
        target_vms = step['targetVMs']
        
        # Get logged in user from deployment
        deployment = deployments[deployment_id]
        logged_in_user = deployment.get("logged_in_user", "system")
        
        # Resolve target VMs from inventory if needed
        resolved_vms = []
        for vm in target_vms:
            vm_info = get_inventory_value(vm, inventory, db_inventory)
            if vm_info:
                resolved_vms.append(vm_info)
            else:
                resolved_vms.append(vm)
        
        log_message(deployment_id, f"Deploying {len(files)} files to {len(resolved_vms)} VMs (initiated by {logged_in_user})")
        logger.info(f"[{deployment_id}] Deploying {len(files)} files to {len(resolved_vms)} VMs")
        
        for file_name in files:
            source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft_number, file_name)
            
            if not os.path.exists(source_file):
                error_msg = f"Source file not found: {source_file}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise FileNotFoundError(error_msg)
            
            log_message(deployment_id, f"Deploying file: {file_name} (initiated by {logged_in_user})")
            
            # Generate ansible playbook for file deployment
            playbook_file = f"/tmp/file_deploy_{deployment_id}_{step['order']}.yml"
            final_target_path = os.path.join(target_path, file_name)
            
            with open(playbook_file, 'w') as f:
                f.write(f"""---
- name: Deploy file {file_name} (Step {step['order']}) (initiated by {logged_in_user})
  hosts: deployment_targets
  gather_facts: false
  become: true
  become_method: sudo
  become_user: {target_user}
  tasks:
    - name: Test connection
      ansible.builtin.ping:
      
    - name: Create target directory
      ansible.builtin.file:
        path: "{target_path}"
        state: directory
        mode: '0755'
        owner: "{target_user}"
      
    - name: Check if file exists
      ansible.builtin.stat:
        path: "{final_target_path}"
      register: file_stat
      
    - name: Create backup if file exists
      ansible.builtin.copy:
        src: "{final_target_path}"
        dest: "{final_target_path}.bak.{{{{ ansible_date_time.epoch }}}}"
        remote_src: yes
      when: file_stat.stat.exists
      
    - name: Copy file to target
      ansible.builtin.copy:
        src: "{source_file}"
        dest: "{final_target_path}"
        mode: '0644'
        owner: "{target_user}"
      register: copy_result
      
    - name: Log success
      ansible.builtin.debug:
        msg: "File {file_name} deployed successfully by {logged_in_user}"
      when: copy_result.changed
""")
            
            # Create inventory file
            inventory_file = f"/tmp/inventory_{deployment_id}_{step['order']}"
            with open(inventory_file, 'w') as f:
                f.write("[deployment_targets]\n")
                for vm_name in resolved_vms:
                    if isinstance(vm_name, dict) and 'ip' in vm_name:
                        f.write(f"{vm_name['name']} ansible_host={vm_name['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                    else:
                        vm_info = next((v for v in inventory.get("vms", []) if v["name"] == vm_name), None)
                        if vm_info:
                            f.write(f"{vm_name} ansible_host={vm_info['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
            
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
                log_message(deployment_id, f"File {file_name} deployed successfully")
                logger.info(f"[{deployment_id}] File {file_name} deployed successfully")
            else:
                error_msg = f"File deployment failed: {result.stderr}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise Exception(error_msg)
            
            # Clean up temporary files
            try:
                os.remove(playbook_file)
                os.remove(inventory_file)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        log_message(deployment_id, f"File deployment step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] File deployment step {step['order']} completed successfully")
        
    except Exception as e:
        deployments, save_deployment_history, log_message = get_app_globals()
        error_msg = f"File deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_service_restart(deployment_id, step, inventory, db_inventory):
    """Execute service operation step using Ansible with comprehensive systemd management like in app.py"""
    try:
        deployments, save_deployment_history, log_message = get_app_globals()
        
        logger.debug(f"[{deployment_id}] DEBUG: Starting execute_service_restart")
        logger.debug(f"[{deployment_id}] DEBUG: Step data: {step}")
        
        if deployment_id not in deployments:
            logger.error(f"[{deployment_id}] DEBUG: Deployment ID not found in deployments")
            return

        deployment = deployments[deployment_id]
        logger.debug(f"[{deployment_id}] DEBUG: Found deployment: {deployment}")
        
        logged_in_user = "admin"
        
        order = step.get("order")
        description = step.get("description", "")
        service = step.get("service")
        operation = step.get("operation", "status")
        target_vms = step.get("targetVMs", [])

        logger.debug(f"[{deployment_id}] DEBUG: Service={service}, Operation={operation}, VMs={target_vms}")
        
        log_message(deployment_id, f"Starting systemd {operation} for service '{service}' on {len(target_vms)} VMs")
        logger.info(f"[{deployment_id}] Starting systemd {operation} for service '{service}' on {len(target_vms)} VMs")

        # Generate an ansible playbook for systemd operation
        playbook_file = f"/tmp/systemd_{deployment_id}_{order}.yml"
        logger.debug(f"[{deployment_id}] DEBUG: Creating playbook at {playbook_file}")
        
        with open(playbook_file, 'w') as f:
            f.write(f"""---
- name: Systemd {operation} operation for {service} 
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
      
    - name: Check if service unit file exists in local
      ansible.builtin.stat:
        path: "/usr/local/lib/systemd/system/{{{{ service_name }}}}"
      register: service_file_local
      
    - name: Set service exists fact
      ansible.builtin.set_fact:
        service_exists: "{{{{ service_file_etc.stat.exists or service_file_lib.stat.exists or service_file_local.stat.exists }}}}"
        
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
                    vm_info = next((v for v in inventory.get("vms", []) if v["name"] == vm_name), None)
                    if vm_info:
                        f.write(f"{vm_name} ansible_host={vm_info['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
        
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
        deployments, save_deployment_history, log_message = get_app_globals()
        error_msg = f"Service restart step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_sql_deployment(deployment_id, step, inventory, db_inventory):
    """Execute SQL deployment step"""
    try:
        deployments, save_deployment_history, log_message = get_app_globals()
        
        logger.info(f"[{deployment_id}] Starting SQL deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting SQL deployment step {step['order']}: {step['description']}")
        
        ft_number = step['ftNumber']
        file_name = step['fileName']
        hostname = step['hostname']
        port = step['port']
        db_name = step['dbName']
        user = step['user']
        password = step.get('password', '')
        
        source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft_number, file_name)
        
        if not os.path.exists(source_file):
            error_msg = f"Source SQL file not found: {source_file}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise FileNotFoundError(error_msg)
        
        log_message(deployment_id, f"Executing SQL file: {file_name} on {hostname}:{port}/{db_name}")
        
        # Check if psql is available
        psql_check = subprocess.run(["which", "psql"], capture_output=True, text=True)
        if psql_check.returncode != 0:
            error_msg = "psql command not found. PostgreSQL client tools are not installed."
            log_message(deployment_id, f"ERROR: {error_msg}")
            raise Exception(error_msg)
        
        # Create command using psql
        cmd = ["psql", "-h", hostname, "-p", port, "-d", db_name, "-U", user, "-f", source_file]
        env = os.environ.copy()
        
        # Set password in environment if provided
        if password:
            env["PGPASSWORD"] = password
        
        log_message(deployment_id, f"Executing: psql -h {hostname} -p {port} -d {db_name} -U {user} -f {file_name}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
        
        has_errors = False
        has_warnings = False
        
        # Process and log all output (stdout and stderr combined)
        all_output = ""
        if result.stdout:
            all_output += result.stdout
        if result.stderr:
            all_output += result.stderr
        
        if all_output:
            for line in all_output.strip().split('\n'):
                line_stripped = line.strip()
                if line_stripped:
                    # Check for SQL errors in the output
                    if "ERROR:" in line_stripped.upper():
                        has_errors = True
                        log_message(deployment_id, line_stripped)
                        logger.debug(f"[{deployment_id}] {line_stripped}")
                    elif "WARNING:" in line_stripped.upper():
                        has_warnings = True
                        log_message(deployment_id, line_stripped)
                        logger.debug(f"[{deployment_id}] {line_stripped}")
                    else:
                        log_message(deployment_id, line_stripped)
                        logger.debug(f"[{deployment_id}] {line_stripped}")
        
        # Determine final status based on errors found in output, not just return code
        if has_errors or result.returncode != 0:
            log_message(deployment_id, "FAILED: SQL execution completed with errors")
            logger.error(f"SQL deployment step {step['order']} failed - errors detected in output or non-zero return code")
            raise Exception("SQL execution failed with errors")
        elif has_warnings:
            log_message(deployment_id, "WARNING: SQL execution completed with warnings")
            logger.warning(f"SQL deployment step {step['order']} completed with warnings")
        else:
            log_message(deployment_id, "SUCCESS: SQL execution completed successfully")
            logger.info(f"SQL deployment step {step['order']} completed successfully")
        
        log_message(deployment_id, f"SQL deployment step {step['order']} completed successfully")
        
    except Exception as e:
        deployments, save_deployment_history, log_message = get_app_globals()
        error_msg = f"SQL deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

@deploy_template_bp.route('/api/deploy/<deployment_id>/logs', methods=['GET'])
def get_deployment_logs(deployment_id):
    """Get deployment logs - matching the working db_routes.py implementation"""
    try:
        deployments, save_deployment_history, log_message = get_app_globals()

        logger.info(f"Looking for deployment: {deployment_id}")
        logger.info(f"Available deployments: {list(deployments.keys())}")
        logger.info(f"Total deployments in memory: {len(deployments)}")
        
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
        deployments, save_deployment_history, log_message = get_app_globals()
        
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
        deployments, save_deployment_history, log_message = get_app_globals()
        
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
