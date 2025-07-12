
import os
import json
import subprocess
import threading
import time
import uuid
import base64
from flask import current_app, Blueprint, jsonify, request
import logging

deploy_template_bp = Blueprint('deploy_template', __name__)

TEMPLATE_DIR = "/app/deployment_templates"
INVENTORY_FILE = "/app/inventory/inventory.json"
DB_INVENTORY_FILE = "/app/inventory/db_inventory.json"
FIX_FILES_DIR = "/app/fixfiles"

def load_template(template_name):
    """Load template from the deployment_templates directory"""
    try:
        template_path = os.path.join(TEMPLATE_DIR, template_name)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        return template
    except Exception as e:
        raise Exception(f"Failed to load template: {str(e)}")

def load_inventory():
    """Load inventory and db_inventory files"""
    try:
        # Load main inventory
        with open(INVENTORY_FILE, 'r') as f:
            inventory = json.load(f)
        
        # Load database inventory
        db_inventory = {}
        if os.path.exists(DB_INVENTORY_FILE):
            with open(DB_INVENTORY_FILE, 'r') as f:
                db_inventory = json.load(f)
        
        return inventory, db_inventory
    except Exception as e:
        raise Exception(f"Failed to load inventory: {str(e)}")

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

def execute_file_deployment(deployment_id, step, inventory, db_inventory):
    """Execute file deployment step"""
    from app import log_message, deployments, save_deployment_history, logger
    
    try:
        logger.info(f"[{deployment_id}] Starting file deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting file deployment step {step['order']}: {step['description']}")
        
        ft_number = step['ftNumber']
        files = step['files']
        target_path = step['targetPath']
        target_user = step['targetUser']
        target_vms = step['targetVMs']
        
        # Resolve target VMs from inventory if needed
        resolved_vms = []
        for vm in target_vms:
            vm_info = get_inventory_value(vm, inventory, db_inventory)
            if vm_info:
                resolved_vms.append(vm_info)
            else:
                resolved_vms.append(vm)
        
        log_message(deployment_id, f"Deploying {len(files)} files to {len(resolved_vms)} VMs")
        logger.info(f"[{deployment_id}] Deploying {len(files)} files to {len(resolved_vms)} VMs")
        
        for file_name in files:
            source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft_number, file_name)
            
            if not os.path.exists(source_file):
                error_msg = f"Source file not found: {source_file}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise FileNotFoundError(error_msg)
            
            log_message(deployment_id, f"Deploying file: {file_name}")
            
            # Generate ansible playbook for file deployment
            playbook_file = f"/tmp/file_deploy_{deployment_id}_{step['order']}.yml"
            final_target_path = os.path.join(target_path, file_name)
            
            with open(playbook_file, 'w') as f:
                f.write(f"""---
- name: Deploy file {file_name} (Step {step['order']})
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
        msg: "File {file_name} deployed successfully"
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
            cmd = ["ansible-playbook", "-i", inventory_file, playbook_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                log_message(deployment_id, f"File {file_name} deployed successfully")
                logger.info(f"[{deployment_id}] File {file_name} deployed successfully")
            else:
                error_msg = f"File deployment failed: {result.stderr}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise Exception(error_msg)
        
        log_message(deployment_id, f"File deployment step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] File deployment step {step['order']} completed successfully")
        
    except Exception as e:
        error_msg = f"File deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_sql_deployment(deployment_id, step, inventory, db_inventory):
    """Execute SQL deployment step"""
    from app import log_message, deployments, save_deployment_history, logger
    
    try:
        logger.info(f"[{deployment_id}] Starting SQL deployment step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting SQL deployment step {step['order']}: {step['description']}")
        
        db_connection = step['dbConnection']
        db_user = step['dbUser']
        db_password = step['dbPassword']
        files = step['files']
        ft_number = step['ftNumber']
        
        # Resolve database connection details from inventory
        db_info = get_inventory_value(db_connection, inventory, db_inventory)
        if not db_info:
            error_msg = f"Database connection '{db_connection}' not found in inventory"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise Exception(error_msg)
        
        # Decode password if it's base64 encoded
        try:
            decoded_password = base64.b64decode(db_password).decode('utf-8')
        except:
            decoded_password = db_password
        
        log_message(deployment_id, f"Executing SQL files: {', '.join(files)}")
        logger.info(f"[{deployment_id}] Executing SQL files: {', '.join(files)}")
        
        for sql_file in files:
            source_file = os.path.join(FIX_FILES_DIR, 'AllFts', ft_number, sql_file)
            
            if not os.path.exists(source_file):
                error_msg = f"SQL file not found: {source_file}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise FileNotFoundError(error_msg)
            
            log_message(deployment_id, f"Executing SQL file: {sql_file}")
            
            # Execute SQL file (adjust based on your database type)
            if 'oracle' in db_info.get('type', '').lower():
                cmd = ["sqlplus", "-s", f"{db_user}/{decoded_password}@{db_info['host']}:{db_info['port']}/{db_info['service']}", f"@{source_file}"]
            elif 'mysql' in db_info.get('type', '').lower():
                cmd = ["mysql", "-h", db_info['host'], "-P", str(db_info['port']), "-u", db_user, f"-p{decoded_password}", "-e", f"source {source_file}"]
            elif 'postgres' in db_info.get('type', '').lower():
                cmd = ["psql", "-h", db_info['host'], "-p", str(db_info['port']), "-U", db_user, "-d", db_info['database'], "-f", source_file]
            else:
                error_msg = f"Unsupported database type: {db_info.get('type', 'unknown')}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise Exception(error_msg)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                log_message(deployment_id, f"SQL file {sql_file} executed successfully")
                logger.info(f"[{deployment_id}] SQL file {sql_file} executed successfully")
            else:
                error_msg = f"SQL execution failed: {result.stderr}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise Exception(error_msg)
        
        log_message(deployment_id, f"SQL deployment step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] SQL deployment step {step['order']} completed successfully")
        
    except Exception as e:
        error_msg = f"SQL deployment step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_service_restart(deployment_id, step, inventory, db_inventory):
    """Execute service operation step using raw systemctl shell commands with unified logging"""
    from app import log_message, deployments, save_deployment_history, logger

    try:
        if deployment_id not in deployments:
            logger.error(f"Deployment ID {deployment_id} not found")
            return

        order = step.get("order")
        description = step.get("description", "")
        service = step.get("service")
        operation = step.get("operation", "restart")
        target_vms = step.get("targetVMs", [])

        log_message(deployment_id, f"Starting service operation step {order}: {description}")
        logger.info(f"[{deployment_id}] Starting systemctl '{operation}' on '{service}' for {len(target_vms)} VM(s)")

        for vm in target_vms:
            # Resolve IP from inventory
            vm_info = next((v for v in inventory.get("vms", []) if v["name"] == vm), None)
            if not vm_info or "ip" not in vm_info:
                error_msg = f"Could not resolve IP for VM: {vm}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                deployments[deployment_id]["status"] = "failed"
                save_deployment_history()
                continue

            ip = vm_info["ip"]
            user = "infadm"

            ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{ip} 'sudo systemctl {operation} {service}'"
            log_message(deployment_id, f"[{vm}] Executing: systemctl {operation} {service}")
            logger.debug(f"[{deployment_id}] [{vm}] SSH command: {ssh_cmd}")

            try:
                result = subprocess.run(
                    ssh_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                stdout = result.stdout.strip()
                stderr = result.stderr.strip()

                if result.returncode == 0:
                    log_message(deployment_id, f"[{vm}] SUCCESS: {operation} on {service}")
                    if stdout:
                        log_message(deployment_id, f"[{vm}] STDOUT: {stdout}")
                    logger.info(f"[{deployment_id}] [{vm}] systemctl {operation} successful")
                else:
                    error_msg = f"[{vm}] ERROR: systemctl {operation} failed with code {result.returncode}"
                    log_message(deployment_id, error_msg)
                    if stderr:
                        log_message(deployment_id, f"[{vm}] STDERR: {stderr}")
                    logger.error(f"[{deployment_id}] [{vm}] systemctl {operation} failed: {stderr}")
                    deployments[deployment_id]["status"] = "failed"
                    save_deployment_history()
                    return

            except subprocess.TimeoutExpired:
                error_msg = f"[{vm}] ERROR: Timeout while running systemctl {operation} {service}"
                log_message(deployment_id, error_msg)
                logger.error(f"[{deployment_id}] [{vm}] systemctl command timed out")
                deployments[deployment_id]["status"] = "failed"
                save_deployment_history()
                return

            except Exception as e:
                error_msg = f"[{vm}] ERROR: Exception: {str(e)}"
                log_message(deployment_id, error_msg)
                logger.exception(f"[{deployment_id}] [{vm}] Unexpected error during systemctl operation")
                deployments[deployment_id]["status"] = "failed"
                save_deployment_history()
                return

        log_message(deployment_id, f"Step {order} completed: systemctl {operation} {service} on all VMs")
        logger.info(f"[{deployment_id}] Step {order} completed successfully")

    except Exception as e:
        error_msg = f"ERROR: Service operation failed: {str(e)}"
        log_message(deployment_id, error_msg)
        logger.exception(f"[{deployment_id}] Critical error in execute_service_restart()")
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "failed"
            save_deployment_history()

def execute_ansible_playbook(deployment_id, step, inventory, db_inventory):
    """Execute ansible playbook step"""
    from app import log_message, deployments, save_deployment_history, logger
    
    try:
        logger.info(f"[{deployment_id}] Starting ansible playbook step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting ansible playbook step {step['order']}: {step['description']}")
        
        playbook = step['playbook']
        
        # Find playbook file
        playbook_path = os.path.join("/app/ansible_playbooks", playbook)
        if not os.path.exists(playbook_path):
            # Try alternative locations
            alternative_paths = [
                os.path.join(FIX_FILES_DIR, "playbooks", playbook),
                os.path.join("/app/playbooks", playbook),
                f"/tmp/{playbook}"
            ]
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    playbook_path = alt_path
                    break
            else:
                error_msg = f"Playbook not found: {playbook}"
                log_message(deployment_id, f"ERROR: {error_msg}")
                logger.error(f"[{deployment_id}] {error_msg}")
                raise FileNotFoundError(error_msg)
        
        log_message(deployment_id, f"Executing playbook: {playbook}")
        logger.info(f"[{deployment_id}] Executing playbook: {playbook}")
        
        # Create inventory file with all VMs
        inventory_file = f"/tmp/inventory_{deployment_id}_{step['order']}"
        with open(inventory_file, 'w') as f:
            f.write("[all]\n")
            for vm in inventory.get("vms", []):
                f.write(f"{vm['name']} ansible_host={vm['ip']} ansible_user=infadm ansible_ssh_private_key_file=/home/users/infadm/.ssh/id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
        
        # Execute ansible playbook
        cmd = ["ansible-playbook", "-i", inventory_file, playbook_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log_message(deployment_id, f"Playbook {playbook} executed successfully")
            logger.info(f"[{deployment_id}] Playbook {playbook} executed successfully")
        else:
            error_msg = f"Playbook execution failed: {result.stderr}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise Exception(error_msg)
        
        log_message(deployment_id, f"Ansible playbook step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] Ansible playbook step {step['order']} completed successfully")
        
    except Exception as e:
        error_msg = f"Ansible playbook step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

def execute_helm_upgrade(deployment_id, step, inventory, db_inventory):
    """Execute helm upgrade step"""
    from app import log_message, deployments, save_deployment_history, logger
    
    try:
        logger.info(f"[{deployment_id}] Starting helm upgrade step {step['order']}: {step['description']}")
        log_message(deployment_id, f"Starting helm upgrade step {step['order']}: {step['description']}")
        
        helm_deployment_type = step['helmDeploymentType']
        
        # Get helm configuration from inventory
        helm_config = get_inventory_value(f"helm_{helm_deployment_type}", inventory, db_inventory)
        if not helm_config:
            error_msg = f"Helm configuration for '{helm_deployment_type}' not found in inventory"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise Exception(error_msg)
        
        log_message(deployment_id, f"Executing helm upgrade for: {helm_deployment_type}")
        logger.info(f"[{deployment_id}] Executing helm upgrade for: {helm_deployment_type}")
        
        # Construct helm upgrade command
        release_name = helm_config.get('release_name', helm_deployment_type)
        chart_name = helm_config.get('chart_name', helm_deployment_type)
        namespace = helm_config.get('namespace', 'default')
        values_file = helm_config.get('values_file', '')
        
        cmd = ["helm", "upgrade", release_name, chart_name, "--namespace", namespace]
        
        if values_file:
            values_path = os.path.join("/app/helm_values", values_file)
            if os.path.exists(values_path):
                cmd.extend(["-f", values_path])
        
        # Add any additional helm arguments
        if 'args' in helm_config:
            cmd.extend(helm_config['args'])
        
        log_message(deployment_id, f"Executing helm command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log_message(deployment_id, f"Helm upgrade for {helm_deployment_type} completed successfully")
            log_message(deployment_id, f"Helm output: {result.stdout}")
            logger.info(f"[{deployment_id}] Helm upgrade for {helm_deployment_type} completed successfully")
        else:
            error_msg = f"Helm upgrade failed: {result.stderr}"
            log_message(deployment_id, f"ERROR: {error_msg}")
            logger.error(f"[{deployment_id}] {error_msg}")
            raise Exception(error_msg)
        
        log_message(deployment_id, f"Helm upgrade step {step['order']} completed successfully")
        logger.info(f"[{deployment_id}] Helm upgrade step {step['order']} completed successfully")
        
    except Exception as e:
        error_msg = f"Helm upgrade step {step['order']} failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        deployments[deployment_id]['status'] = 'failed'
        save_deployment_history()
        raise

@deploy_template_bp.route('/api/deploy/template', methods=['POST'])
def deploy_template_route():
    from app import deployments, save_deployment_history, logger

    try:
        data = request.get_json()
        logger.debug(f"Received JSON payload: {data}")

        template_name = data.get('template')
        if not template_name:
            logger.warning("Missing 'template' key in request")
            return jsonify({"error": "Template name is required"}), 400

        # You can replace this with real user logic if available
        current_user = {"username": "mockuser", "role": "admin"}
        logger.info(f"Initiating deployment for template: {template_name} by user: {current_user['username']}")

        # Call the deployment function
        result, status_code = deploy_template(template_name, current_user)
        logger.info(f"Deployment started: {result.get('deploymentId')} (Status code: {status_code})")

        return jsonify(result), status_code

    except Exception as e:
        logger.exception("Error occurred while handling template deployment")
        return jsonify({"error": str(e)}), 500

@deploy_template_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """List available deployment templates"""
    from app import logger
    
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
    from app import logger
    
    try:
        template = load_template(template_name)
        return jsonify(template)
    except Exception as e:
        logger.error(f"Failed to get template details: {str(e)}")
        return jsonify({"error": str(e)}), 500

def execute_step(deployment_id, step, inventory, db_inventory):
    """Execute a single step based on its type"""
    step_type = step['type']
    
    if step_type == 'file_deployment':
        execute_file_deployment(deployment_id, step, inventory, db_inventory)
    elif step_type == 'sql_deployment':
        execute_sql_deployment(deployment_id, step, inventory, db_inventory)
    elif step_type == 'service_restart':
        execute_service_restart(deployment_id, step, inventory, db_inventory)
    elif step_type == 'ansible_playbook':
        execute_ansible_playbook(deployment_id, step, inventory, db_inventory)
    elif step_type == 'helm_upgrade':
        execute_helm_upgrade(deployment_id, step, inventory, db_inventory)
    else:
        from app import log_message, logger
        error_msg = f"Unknown step type: {step_type}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.error(f"[{deployment_id}] {error_msg}")
        raise Exception(error_msg)

def can_execute_step(step, completed_steps, dependencies):
    """Check if a step can be executed based on its dependencies"""
    step_number = step['order']
    
    # Find dependencies for this step
    step_deps = None
    for dep in dependencies:
        if dep['step'] == step_number:
            step_deps = dep
            break
    
    if not step_deps:
        return True  # No dependencies defined
    
    # Check if all dependencies are completed
    for dep_step in step_deps['depends_on']:
        if dep_step not in completed_steps:
            return False
    
    return True

def process_template_deployment(deployment_id):
    """Process template deployment with dependency management"""
    from app import deployments, save_deployment_history, log_message, logger
    
    if deployment_id not in deployments:
        logger.error(f"Deployment ID {deployment_id} not found in deployments")
        return
        
    deployment = deployments[deployment_id]
    
    try:
        template_name = deployment['template']
        
        # Load template
        template = load_template(template_name)
        log_message(deployment_id, f"Loaded template: {template_name}")
        logger.info(f"[{deployment_id}] Loaded template: {template_name}")
        
        # Load inventory
        inventory, db_inventory = load_inventory()
        log_message(deployment_id, f"Loaded inventory data")
        logger.info(f"[{deployment_id}] Loaded inventory data")
        
        # Get steps and dependencies
        steps = template['steps']
        dependencies = template.get('dependencies', [])
        
        log_message(deployment_id, f"Starting template deployment with {len(steps)} steps")
        logger.info(f"[{deployment_id}] Starting template deployment with {len(steps)} steps")
        
        # Sort steps by order
        steps.sort(key=lambda x: x['order'])
        
        completed_steps = set()
        failed_steps = set()
        
        # Execute steps based on dependencies
        while len(completed_steps) < len(steps) and not failed_steps:
            ready_steps = []
            
            for step in steps:
                step_number = step['order']
                if step_number not in completed_steps and step_number not in failed_steps:
                    if can_execute_step(step, completed_steps, dependencies):
                        ready_steps.append(step)
            
            if not ready_steps:
                if len(completed_steps) < len(steps):
                    error_msg = "No more steps can be executed due to dependencies"
                    log_message(deployment_id, f"ERROR: {error_msg}")
                    logger.error(f"[{deployment_id}] {error_msg}")
                    break
                else:
                    break
            
            # Execute ready steps
            for step in ready_steps:
                try:
                    log_message(deployment_id, f"Executing step {step['order']}: {step['description']}")
                    logger.info(f"[{deployment_id}] Executing step {step['order']}: {step['description']}")
                    execute_step(deployment_id, step, inventory, db_inventory)
                    completed_steps.add(step['order'])
                    log_message(deployment_id, f"Step {step['order']} completed successfully")
                    logger.info(f"[{deployment_id}] Step {step['order']} completed successfully")
                except Exception as e:
                    error_msg = f"Step {step['order']} failed: {str(e)}"
                    log_message(deployment_id, f"ERROR: {error_msg}")
                    logger.error(f"[{deployment_id}] {error_msg}")
                    failed_steps.add(step['order'])
                    break  # Stop execution on first failure
        
        # Update deployment status
        if failed_steps:
            deployments[deployment_id]['status'] = 'failed'
            log_message(deployment_id, f"Template deployment failed. Steps failed: {failed_steps}")
            logger.error(f"[{deployment_id}] Template deployment failed. Steps failed: {failed_steps}")
        else:
            deployments[deployment_id]['status'] = 'completed'
            log_message(deployment_id, f"Template deployment completed successfully. Steps completed: {completed_steps}")
            logger.info(f"[{deployment_id}] Template deployment completed successfully. Steps completed: {completed_steps}")
        
    except Exception as e:
        error_msg = f"Template deployment failed: {str(e)}"
        log_message(deployment_id, f"ERROR: {error_msg}")
        logger.exception(f"[{deployment_id}] Template deployment critical error")
        deployments[deployment_id]['status'] = 'failed'
    
    finally:
        # Save deployment history
        save_deployment_history()
        logger.info(f"[{deployment_id}] Deployment history saved")

def deploy_template(template_name, current_user):
    """Main function to start template deployment"""
    from app import deployments, save_deployment_history, logger
    
    try:
        # Validate template exists
        template_path = os.path.join(TEMPLATE_DIR, template_name)
        if not os.path.exists(template_path):
            error_msg = f"Template not found: {template_name}"
            logger.error(error_msg)
            return {"error": error_msg}, 404
        
        # Generate deployment ID
        deployment_id = str(uuid.uuid4())
        
        # Store deployment information
        deployments[deployment_id] = {
            "id": deployment_id,
            "type": "template",
            "template": template_name,
            "logged_in_user": current_user['username'],
            "user_role": current_user['role'],
            "status": "running",
            "timestamp": time.time(),
            "logs": []
        }
        
        logger.info(f"[{deployment_id}] Template deployment initiated by {current_user['username']}")
        
        # Save deployment history
        save_deployment_history()
        
        # Start deployment in separate thread
        threading.Thread(target=process_template_deployment, args=(deployment_id,)).start()
        
        return {
            "deploymentId": deployment_id,
            "initiatedBy": current_user['username'],
            "template": template_name
        }, 200
        
    except Exception as e:
        error_msg = f"Failed to start template deployment: {str(e)}"
        logger.exception("Critical error in deploy_template")
        return {"error": error_msg}, 500
