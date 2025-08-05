import json
import re
import os
import inspect
from typing import Dict, List, Any
from gpt4all import GPT4All
from backend.config.gpt4all_config import GPT4ALL_CONFIG

class GPT4AllLogAnalyzer:
    def __init__(self, model_name=None, model_path=None):
        self.model_path = model_path or GPT4ALL_CONFIG['model_path']
        self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
        # Verify model exists locally
        model_file_path = os.path.join(self.model_path, self.model_name)
        if not os.path.exists(model_file_path):
            available_models = [f for f in os.listdir(self.model_path) if f.endswith('.gguf')]
            if available_models:
                # Prefer Llama-3 if available
                llama_models = [m for m in available_models if 'llama' in m.lower()]
                if llama_models:
                    self.model_name = llama_models[0]
                else:
                    self.model_name = available_models[0]
                print(f"Model not found, using {self.model_name}")
            else:
                raise FileNotFoundError(f"No models found in {self.model_path}")
        
        print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
        
        try:
            self.model = GPT4All(self.model_name, model_path=self.model_path)
            
            # Test the model
            print("Testing model initialization...")
            test_response = self.model.generate("Hello", max_tokens=5)
            print("Model test successful")
            
        except Exception as e:
            print(f"Model initialization failed: {e}")
            raise
        
        # Get model-specific settings
        self.model_settings = GPT4ALL_CONFIG.get('model_settings', {}).get(
            self.model_name, 
            GPT4ALL_CONFIG.get('model_settings', {}).get('orca-mini-3b-gguf2-q4_0.gguf', {})
        )
        
        # Detect supported parameters
        self.supported_params = self._detect_supported_params()
        print(f"Using model settings: {self.model_settings}")
        print(f"Supported parameters: {list(self.supported_params.keys())}")
        
    def _detect_supported_params(self) -> Dict[str, Any]:
        """Detect supported parameters and apply model-specific settings"""
        try:
            sig = inspect.signature(self.model.generate)
            params = sig.parameters
            
            # Start with model-specific settings
            supported = {}
            for param_name, value in self.model_settings.items():
                if param_name in params and param_name != 'prompt_style':
                    supported[param_name] = value
            
            # Add any missing common parameters
            common_params = {
                'max_tokens': 1000,
                'temp': 0.2,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
            }
            
            for param_name, default_value in common_params.items():
                if param_name in params and param_name not in supported:
                    supported[param_name] = default_value
                    
            return supported
            
        except Exception as e:
            print(f"Could not detect supported parameters: {e}")
            return {'max_tokens': 1000, 'temp': 0.2}
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """Analyze logs using GPT4All with model-specific prompting"""
        
        log_sample = self._prepare_logs(logs)
        prompt = self._create_model_specific_prompt(log_sample, deployment_id)
        
        try:
            print(f"Sending prompt to GPT4All model...")
            print(f"Prompt length: {len(prompt)} characters")
            
            generate_params = {'prompt': prompt}
            generate_params.update(self.supported_params)
            
            print(f"Using parameters: {list(generate_params.keys())}")
            
            # Try multiple approaches
            response = None
            
            # Approach 1: Chat session (newer models)
            if 'llama' in self.model_name.lower() or 'instruct' in self.model_name.lower():
                try:
                    with self.model.chat_session():
                        response = self.model.generate(**generate_params)
                    print("Used chat session successfully")
                except Exception as e:
                    print(f"Chat session failed: {e}")
            
            # Approach 2: Direct generate
            if response is None:
                try:
                    response = self.model.generate(**generate_params)
                    print("Used direct generate successfully")
                except Exception as e:
                    print(f"Direct generate failed: {e}")
                    raise
            
            print(f"Raw GPT4All response length: {len(response)}")
            print(f"Raw GPT4All response preview: {response[:300]}...")
            
            # Parse the response
            analysis = self._parse_analysis_response(response, log_sample)
            return analysis
            
        except Exception as e:
            print(f"GPT4All analysis failed: {str(e)}")
            return self._fallback_analysis(logs, str(e))
    
    def _prepare_logs(self, logs: List[str], max_logs: int = 8, max_log_length: int = 100) -> str:
        """Prepare logs - be conservative with smaller models"""
        sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
        cleaned_logs = []
        for i, log in enumerate(sample_logs, 1):
            clean_log = re.sub(r'\s+', ' ', log.strip())
            if len(clean_log) > max_log_length:
                clean_log = clean_log[:max_log_length] + "..."
            cleaned_logs.append(f"{clean_log}")
        
        return "\n".join(cleaned_logs)
    
    def _create_model_specific_prompt(self, logs: str, deployment_id: str) -> str:
        """Create prompts tailored to specific models"""
        
        prompt_style = self.model_settings.get('prompt_style', 'simple')
        
        if prompt_style == 'llama3':
            # Llama-3 style with system/user format
            prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a log analysis expert. Analyze deployment logs and provide JSON analysis.<|eot_id|><|start_header_id|>user<|end_header_id|>

Analyze these deployment logs:

DEPLOYMENT ID: {deployment_id or 'Unknown'}
LOGS:
{logs}

Provide analysis as JSON with these exact fields:
- summary: What went wrong (be specific)
- shortSummary: One line description
- category: Choose from [deployment, database, network, application, filesystem]
- severity: Choose from [critical, high, medium, low]  
- errorType: Main error found
- recommendations: Array of 2-3 fix suggestions

Example for PostgreSQL error:
{{"summary": "PostgreSQL service failed to start due to missing config file", "shortSummary": "PostgreSQL startup failure", "category": "database", "severity": "high", "errorType": "ConfigMissing", "recommendations": ["Check /etc/postgresql/ for config files", "Restore from backup"]}}

Now analyze the actual logs above:<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        else:
            # Simple style for smaller models
            prompt = f"""Task: Analyze these deployment logs and respond with JSON only.

Logs:
{logs}

Required JSON format:
{{"summary": "describe the problem found", "shortSummary": "brief description", "category": "deployment", "severity": "high", "errorType": "ErrorName", "recommendations": ["fix 1", "fix 2"]}}

Look for:
- Failed services
- Error messages  
- Connection issues
- Missing files

Respond with JSON:"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str, original_logs: str) -> Dict[str, Any]:
        """Enhanced parsing with validation"""
        try:
            response = response.strip()
            print(f"Parsing response: {response[:200]}...")
            
            # Multiple JSON extraction strategies
            json_str = None
            
            # Strategy 1: Look for complete JSON blocks
            json_patterns = [
                r'\{[^{}]*"summary"[^{}]*"recommendations"[^{}]*\}',
                r'\{.*?"summary".*?\}',
                r'\{.*?\}'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    try:
                        # Test if it's valid JSON
                        test_json = json.loads(match)
                        if 'summary' in test_json:
                            json_str = match
                            break
                    except:
                        continue
                if json_str:
                    break
            
            if json_str:
                print(f"Extracted JSON: {json_str[:150]}...")
                analysis = json.loads(json_str)
                
                # Validate it's not a template response
                if self._is_template_response(analysis):
                    print("Template response detected, creating smart analysis")
                    return self._create_smart_analysis(original_logs)
                
                return self._validate_and_fix_analysis(analysis)
            
            else:
                print("No valid JSON found, creating smart analysis")
                return self._create_smart_analysis(original_logs)
                
        except Exception as e:
            print(f"JSON parsing failed: {e}")
            return self._create_smart_analysis(original_logs)
    
    def _is_template_response(self, analysis: Dict[str, Any]) -> bool:
        """Check if response is just template"""
        template_phrases = [
            "brief description", "one line", "main error found", 
            "fix suggestion", "describe the problem", "errorname"
        ]
        
        analysis_text = json.dumps(analysis).lower()
        return any(phrase in analysis_text for phrase in template_phrases)
    
    def _create_smart_analysis(self, logs: str) -> Dict[str, Any]:
        """Create intelligent analysis based on log content"""
        
        logs_lower = logs.lower()
        
        # Smart pattern detection
        analysis_data = {
            "summary": "Log analysis completed using pattern matching",
            "shortSummary": "Pattern-based analysis",
            "category": "application",
            "severity": "medium",
            "errorType": "Unknown",
            "recommendations": []
        }
        
        # Database issues
        if re.search(r'postgresql|postgres', logs_lower):
            if re.search(r'failed.*start|connection.*refused', logs_lower):
                analysis_data.update({
                    "summary": "PostgreSQL service failed to start or connection was refused",
                    "shortSummary": "PostgreSQL service failure",
                    "category": "database",
                    "severity": "high",
                    "errorType": "PostgreSQLFailure",
                    "recommendations": [
                        "Check PostgreSQL service status: systemctl status postgresql",
                        "Verify configuration files in /etc/postgresql/",
                        "Check port 5432 availability",
                        "Review PostgreSQL logs for detailed errors"
                    ]
                })
        
        # MySQL issues
        elif re.search(r'mysql|mariadb', logs_lower):
            analysis_data.update({
                "summary": "MySQL/MariaDB related issue detected",
                "shortSummary": "MySQL database issue", 
                "category": "database",
                "severity": "high",
                "errorType": "MySQLError",
                "recommendations": [
                    "Check MySQL service status",
                    "Verify database credentials",
                    "Check MySQL configuration"
                ]
            })
        
        # Network/Connection issues
        elif re.search(r'connection.*refused|connection.*failed|timeout|network', logs_lower):
            analysis_data.update({
                "summary": "Network connectivity or connection issue detected",
                "shortSummary": "Network connection failure",
                "category": "network", 
                "severity": "high",
                "errorType": "ConnectionFailure",
                "recommendations": [
                    "Check network connectivity to target hosts",
                    "Verify firewall rules and port accessibility",
                    "Test with telnet or nc to verify connectivity",
                    "Check DNS resolution"
                ]
            })
        
        # Ansible/Deployment issues  
        elif re.search(r'ansible|playbook|task.*failed|deployment.*failed', logs_lower):
            analysis_data.update({
                "summary": "Ansible deployment or playbook execution failed",
                "shortSummary": "Deployment failure",
                "category": "deployment",
                "severity": "high", 
                "errorType": "DeploymentFailure",
                "recommendations": [
                    "Review Ansible playbook syntax and tasks",
                    "Check target host connectivity and credentials",
                    "Verify required packages are available",
                    "Run ansible with -vvv for detailed debugging"
                ]
            })
        
        # File system issues
        elif re.search(r'no such file|file not found|permission denied|disk.*full', logs_lower):
            analysis_data.update({
                "summary": "File system related issue - missing files or permission problems",
                "shortSummary": "File system issue",
                "category": "filesystem",
                "severity": "medium",
                "errorType": "FileSystemError", 
                "recommendations": [
                    "Check if required files exist",
                    "Verify file and directory permissions",
                    "Check available disk space",
                    "Ensure correct file paths"
                ]
            })
        
        # Memory issues
        elif re.search(r'out of memory|oom|memory.*error', logs_lower):
            analysis_data.update({
                "summary": "System running out of memory",
                "shortSummary": "Memory exhaustion",
                "category": "memory",
                "severity": "critical",
                "errorType": "OutOfMemory",
                "recommendations": [
                    "Check memory usage: free -h",
                    "Identify memory-intensive processes: top",
                    "Consider increasing system memory",
                    "Review application memory configuration"
                ]
            })
        
        # Generic error detection
        elif re.search(r'error|failed|exception|fatal', logs_lower):
            error_count = len(re.findall(r'error|failed', logs_lower))
            severity = "high" if error_count > 2 else "medium"
            
            analysis_data.update({
                "summary": f"Multiple errors detected in logs ({error_count} error indicators found)",
                "shortSummary": f"{error_count} errors found in deployment logs",
                "severity": severity,
                "errorType": "MultipleErrors",
                "recommendations": [
                    "Review full logs for specific error messages",
                    "Check system resources and dependencies", 
                    "Verify configuration files",
                    "Consider restarting failed services"
                ]
            })
        
        # Add context information
        analysis_data["rootCause"] = {
            "cause": "Pattern-based analysis",
            "description": f"Analysis performed using pattern matching on log content",
            "confidence": "medium"
        }
        
        analysis_data["urgency"] = analysis_data["severity"]
        analysis_data["context"] = {
            "deployment": "unknown",
            "environment": "inferred",
            "service": "pattern-analyzer"
        }
        
        return analysis_data
    
    def _validate_and_fix_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix analysis structure"""
        
        # Ensure all required fields
        defaults = {
            'summary': 'Log analysis completed',
            'shortSummary': 'Analysis completed',
            'category': 'application',
            'severity': 'medium',
            'errorType': 'Unknown',
            'recommendations': ['Review logs manually'],
            'rootCause': {
                'cause': 'Analysis completed',
                'description': 'Log analysis performed',
                'confidence': 'medium'
            },
            'urgency': 'medium',
            'context': {
                'deployment': 'unknown',
                'environment': 'unknown',
                'service': 'gpt4all-analyzer'
            }
        }
        
        for key, default_value in defaults.items():
            if key not in analysis or not analysis[key]:
                analysis[key] = default_value
        
        # Ensure urgency matches severity if not set
        if analysis.get('urgency') == 'medium' and analysis.get('severity') != 'medium':
            analysis['urgency'] = analysis['severity']
        
        return analysis
    
    def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
        """Smart fallback when AI completely fails"""
        
        log_text = " ".join(logs[:10]).lower()
        
        # Use the same smart analysis logic
        smart_analysis = self._create_smart_analysis(log_text)
        
        # Override with error information
        smart_analysis["summary"] = f"GPT4All failed ({error[:100]}), but pattern analysis found: {smart_analysis['errorType']}"
        smart_analysis["shortSummary"] = f"AI failed - pattern analysis: {smart_analysis['errorType']}"
        
        return smart_analysis