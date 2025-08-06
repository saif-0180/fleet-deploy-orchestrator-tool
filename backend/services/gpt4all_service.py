import json
import re
import os
import inspect
import time
from typing import Dict, List, Any, Optional
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
                # Prefer fastest model for performance
                orca_models = [m for m in available_models if 'orca' in m.lower()]
                if orca_models:
                    self.model_name = orca_models[0]
                else:
                    self.model_name = available_models[0]
                print(f"Model not found, using {self.model_name}")
            else:
                raise FileNotFoundError(f"No models found in {self.model_path}")
        
        print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
        
        try:
            self.model = GPT4All(self.model_name, model_path=self.model_path)
            print("Model initialization successful")
            
        except Exception as e:
            print(f"Model initialization failed: {e}")
            raise
        
        # Ultra-fast settings for maximum speed
        self.supported_params = self._get_ultra_fast_params()
        print(f"Using ultra-fast parameters: {list(self.supported_params.keys())}")
        
        # Precompiled regex patterns for better performance
        self._compile_patterns()
        
    def _get_ultra_fast_params(self) -> Dict[str, Any]:
        """Ultra-fast parameters for maximum speed"""
        try:
            sig = inspect.signature(self.model.generate)
            params = sig.parameters
            
            # Minimal settings for maximum speed
            optimized = {
                'max_tokens': 200,      # Very short responses
                'temp': 0.05,           # Very low temperature for consistency
                'top_p': 0.5,           # Very focused output
                'repeat_penalty': 1.0,  # No penalty for speed
                'top_k': 10             # Very limited choices for speed
            }
            
            # Only include supported parameters
            supported = {}
            for param_name, value in optimized.items():
                if param_name in params:
                    supported[param_name] = value
                    
            return supported
            
        except Exception as e:
            print(f"Parameter detection failed: {e}")
            return {'max_tokens': 200, 'temp': 0.05}
    
    def _compile_patterns(self):
        """Precompile regex patterns for better performance"""
        # Strong success indicators - comprehensive patterns
        self.success_patterns = [
            re.compile(r'successfully\s+completed', re.IGNORECASE),
            re.compile(r'operation\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'deployment\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'rollback\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'backup\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'task\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'validation\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'checksum\s+validation\s+passed', re.IGNORECASE),
            re.compile(r'file\s+permissions\s+validated', re.IGNORECASE),
            re.compile(r'all\s+checks\s+passed', re.IGNORECASE),
            re.compile(r'status:\s*success', re.IGNORECASE),
            re.compile(r'result:\s*success', re.IGNORECASE),
            re.compile(r'files\s+backed\s+up\s+successfully', re.IGNORECASE),
            re.compile(r'play\s+recap.*ok=\d+.*changed=\d+.*unreachable=0.*failed=0', re.IGNORECASE),
            re.compile(r'batch\d+.*ok=\d+.*changed=\d+.*failed=0', re.IGNORECASE),
            # Additional success patterns for validation logs
            re.compile(r'validation:\s*passed', re.IGNORECASE),
            re.compile(r'check:\s*ok', re.IGNORECASE),
            re.compile(r'verification:\s*successful', re.IGNORECASE),
            re.compile(r'integrity\s+check\s+passed', re.IGNORECASE),
        ]
        
        # Failure indicators - be more specific to avoid false positives
        self.failure_patterns = [
            re.compile(r'error(?!\s*(log|message):\s*$)(?!.*successfully)', re.IGNORECASE),
            re.compile(r'failed(?!\s*=\s*0)(?!\s*(to\s+)?log)', re.IGNORECASE),
            re.compile(r'exception(?!.*handled)', re.IGNORECASE),
            re.compile(r'fatal(?!\s*log)', re.IGNORECASE),
            re.compile(r'connection\s+(refused|failed|timeout)', re.IGNORECASE),
            re.compile(r'timeout(?!\s*set)', re.IGNORECASE),
            re.compile(r'permission\s+denied', re.IGNORECASE),
            re.compile(r'no\s+such\s+file', re.IGNORECASE),
            re.compile(r'unreachable=[1-9]\d*', re.IGNORECASE),
            re.compile(r'failed=[1-9]\d*', re.IGNORECASE),
            re.compile(r'exit\s+code:\s*[1-9]', re.IGNORECASE),
            re.compile(r'command\s+not\s+found', re.IGNORECASE),
            re.compile(r'syntax\s+error', re.IGNORECASE),
            re.compile(r'connection\s+lost', re.IGNORECASE),
        ]
        
        # Neutral/informational patterns that shouldn't trigger failure
        self.neutral_patterns = [
            re.compile(r'error\s*log', re.IGNORECASE),
            re.compile(r'failed\s*log', re.IGNORECASE),
            re.compile(r'debug', re.IGNORECASE),
            re.compile(r'info', re.IGNORECASE),
            re.compile(r'warning(?!\s*(:|.*critical))', re.IGNORECASE),
        ]
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """Ultra-fast log analysis with improved success/failure detection"""
        
        start_time = time.time()
        
        # Join logs for analysis - more context-aware
        log_text = "\n".join(logs)
        
        # Enhanced success/failure detection
        is_success, confidence = self._enhanced_success_detection(log_text)
        
        if is_success and confidence > 0.8:
            print(f"High confidence success detected ({confidence:.2f}) - using fast path")
            analysis = self._create_success_analysis(logs, deployment_id, log_text)
            print(f"Analysis completed in {time.time() - start_time:.2f} seconds")
            return analysis
        
        # For potential failures or low confidence, use pattern-based analysis first
        if confidence < 0.6:
            print(f"Low confidence ({confidence:.2f}) - using pattern analysis")
            pattern_analysis = self._create_enhanced_pattern_analysis(log_text, deployment_id)
            
            # Only use AI if pattern analysis is inconclusive
            if pattern_analysis['severity'] == 'high':
                print(f"Pattern analysis found high severity issue - skipping AI")
                print(f"Analysis completed in {time.time() - start_time:.2f} seconds")
                return pattern_analysis
        
        # Last resort - AI analysis with timeout
        print("Using AI analysis with timeout")
        return self._ai_analysis_with_timeout(logs, deployment_id, start_time, timeout=15)
    
    def _enhanced_success_detection(self, log_text: str) -> tuple[bool, float]:
        """Enhanced success detection with confidence scoring"""
        
        # Count matches for different patterns
        success_score = 0
        failure_score = 0
        neutral_score = 0
        
        # Success pattern matching
        for pattern in self.success_patterns:
            matches = pattern.findall(log_text)
            success_score += len(matches) * 2  # Weight success higher
        
        # Failure pattern matching
        for pattern in self.failure_patterns:
            matches = pattern.findall(log_text)
            failure_score += len(matches)
        
        # Neutral pattern matching (reduces failure score)
        for pattern in self.neutral_patterns:
            matches = pattern.findall(log_text)
            neutral_score += len(matches)
        
        # Adjust failure score for neutral patterns
        adjusted_failure_score = max(0, failure_score - neutral_score * 0.5)
        
        # Special checks for validation logs
        if self._is_validation_log(log_text):
            validation_success = self._check_validation_success(log_text)
            if validation_success:
                success_score += 3  # Strong boost for validation success
        
        # Calculate confidence and decision
        total_score = success_score + adjusted_failure_score
        
        if total_score == 0:
            # No clear indicators - look for implicit success
            implicit_success = self._check_implicit_success(log_text)
            return implicit_success, 0.5
        
        success_ratio = success_score / total_score
        is_success = success_ratio > 0.6
        confidence = abs(success_ratio - 0.5) * 2  # Convert to 0-1 scale
        
        print(f"Success detection: success_score={success_score}, failure_score={adjusted_failure_score}, ratio={success_ratio:.2f}, confidence={confidence:.2f}")
        
        return is_success, min(confidence, 1.0)
    
    def _is_validation_log(self, log_text: str) -> bool:
        """Check if this is a validation/checksum log"""
        validation_indicators = [
            'checksum', 'validation', 'verify', 'integrity', 'permissions', 
            'file check', 'md5', 'sha', 'hash'
        ]
        log_lower = log_text.lower()
        return any(indicator in log_lower for indicator in validation_indicators)
    
    def _check_validation_success(self, log_text: str) -> bool:
        """Specific validation success checks"""
        validation_success_patterns = [
            r'checksum.*(?:ok|passed|valid|correct|match)',
            r'validation.*(?:passed|successful|ok)',
            r'permissions.*(?:ok|valid|correct)',
            r'integrity.*(?:check.*passed|ok)',
            r'verify.*(?:successful|passed|ok)',
            r'all.*checks.*passed',
            r'hash.*(?:match|valid|correct)'
        ]
        
        for pattern in validation_success_patterns:
            if re.search(pattern, log_text, re.IGNORECASE):
                return True
        return False
    
    def _check_implicit_success(self, log_text: str) -> bool:
        """Check for implicit success indicators"""
        log_lower = log_text.lower()
        
        # No errors but has completion indicators
        has_completion = any(word in log_lower for word in ['completed', 'finished', 'done'])
        has_errors = any(word in log_lower for word in ['error', 'failed', 'exception'])
        
        if has_completion and not has_errors:
            return True
        
        # Check for positive ending
        lines = log_text.strip().split('\n')
        if lines:
            last_line = lines[-1].lower()
            positive_endings = ['ok', 'success', 'complete', 'done', 'passed']
            if any(ending in last_line for ending in positive_endings):
                return True
        
        return False
    
    def _create_success_analysis(self, logs: List[str], deployment_id: str, log_text: str) -> Dict[str, Any]:
        """Enhanced success analysis with better categorization"""
        
        log_lower = log_text.lower()
        
        # Determine operation type and extract metrics
        operation_type, summary, metrics = self._analyze_successful_operation(log_lower)
        
        return {
            "summary": f"{summary}. {metrics}",
            "shortSummary": f"Successful {operation_type}",
            "category": self._categorize_operation(operation_type, log_lower),
            "severity": "low",
            "errorType": "Success",
            "rootCause": {
                "cause": f"Successful {operation_type}",
                "description": f"The {operation_type} operation completed without errors",
                "confidence": "high"
            },
            "recommendations": [
                "No action required - operation successful",
                "Monitor system for any post-operation effects",
                "Document successful configuration for future reference"
            ],
            "urgency": "low",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": operation_type,
                "metrics": metrics,
                "analysis_type": "fast_success_detection"
            }
        }
    
    def _analyze_successful_operation(self, log_text: str) -> tuple[str, str, str]:
        """Analyze what type of successful operation occurred"""
        
        metrics = []
        
        # Extract Ansible metrics
        ok_match = re.search(r'ok=(\d+)', log_text)
        changed_match = re.search(r'changed=(\d+)', log_text)
        failed_match = re.search(r'failed=(\d+)', log_text)
        
        if ok_match:
            metrics.append(f"{ok_match.group(1)} tasks OK")
        if changed_match:
            metrics.append(f"{changed_match.group(1)} changes")
        if failed_match and failed_match.group(1) == '0':
            metrics.append("0 failures")
        
        metrics_text = ", ".join(metrics) if metrics else "Operation completed successfully"
        
        # Determine operation type
        if 'rollback' in log_text:
            return "rollback", "Rollback operation completed successfully", metrics_text
        elif 'backup' in log_text:
            return "backup", "Backup operation completed successfully", metrics_text
        elif 'deployment' in log_text or 'deploy' in log_text:
            return "deployment", "Deployment completed successfully", metrics_text
        elif 'validation' in log_text or 'checksum' in log_text:
            return "validation", "Validation completed successfully", metrics_text
        elif 'playbook' in log_text or 'ansible' in log_text:
            return "playbook", "Ansible playbook executed successfully", metrics_text
        else:
            return "operation", "Operation completed successfully", metrics_text
    
    def _categorize_operation(self, operation_type: str, log_text: str) -> str:
        """Categorize the operation type"""
        if operation_type in ['backup', 'rollback']:
            return 'maintenance'
        elif operation_type in ['validation', 'checksum']:
            return 'verification'
        elif operation_type in ['deployment', 'playbook']:
            return 'deployment'
        elif 'database' in log_text or 'postgres' in log_text or 'mysql' in log_text:
            return 'database'
        elif 'network' in log_text or 'connection' in log_text:
            return 'network'
        else:
            return 'application'
    
    def _create_enhanced_pattern_analysis(self, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Enhanced pattern analysis with better accuracy"""
        
        log_lower = log_text.lower()
        
        # Priority-based pattern matching
        analyses = []
        
        # Database issues (high priority)
        if re.search(r'postgresql|postgres', log_lower):
            if re.search(r'failed.*start|connection.*refused|could not connect', log_lower):
                analyses.append({
                    "summary": "PostgreSQL service failure - unable to start or accept connections",
                    "shortSummary": "PostgreSQL service down",
                    "category": "database",
                    "severity": "critical",
                    "errorType": "PostgreSQLServiceFailure",
                    "recommendations": [
                        "Check PostgreSQL service: sudo systemctl status postgresql",
                        "Verify configuration: check /etc/postgresql/*/main/postgresql.conf",
                        "Check port availability: netstat -tlnp | grep 5432",
                        "Review PostgreSQL logs: tail -f /var/log/postgresql/*.log"
                    ],
                    "priority": 10
                })
        
        # Network issues (high priority)
        if re.search(r'connection\s+(refused|failed|timeout)|network.*unreachable', log_lower):
            analyses.append({
                "summary": "Network connectivity failure - target hosts unreachable or refusing connections",
                "shortSummary": "Network connectivity failure",
                "category": "network",
                "severity": "high",
                "errorType": "NetworkConnectivityFailure",
                "recommendations": [
                    "Test connectivity: ping <target_host>",
                    "Check firewall rules: iptables -L",
                    "Verify DNS resolution: nslookup <target_host>",
                    "Test specific ports: telnet <host> <port>"
                ],
                "priority": 9
            })
        
        # Ansible deployment failures
        if re.search(r'ansible.*failed|playbook.*failed|task.*failed.*fatal', log_lower):
            analyses.append({
                "summary": "Ansible playbook execution failed - one or more tasks could not complete",
                "shortSummary": "Ansible deployment failed",
                "category": "deployment", 
                "severity": "high",
                "errorType": "AnsibleDeploymentFailure",
                "recommendations": [
                    "Run with verbose output: ansible-playbook -vvv",
                    "Check target host connectivity and SSH access",
                    "Verify inventory file and host configuration",
                    "Review playbook syntax and task definitions"
                ],
                "priority": 8
            })
        
        # File system issues
        if re.search(r'no such file|file not found|permission denied|disk.*full', log_lower):
            analyses.append({
                "summary": "File system issue detected - missing files, permission problems, or disk space",
                "shortSummary": "File system issue",
                "category": "filesystem",
                "severity": "medium",
                "errorType": "FileSystemError",
                "recommendations": [
                    "Check file existence and paths",
                    "Verify permissions: ls -la <file_path>", 
                    "Check disk space: df -h",
                    "Review directory structure and ownership"
                ],
                "priority": 6
            })
        
        # Memory issues
        if re.search(r'out of memory|oom|memory.*error|killed.*process', log_lower):
            analyses.append({
                "summary": "System memory exhaustion - processes being killed due to insufficient memory",
                "shortSummary": "Out of memory",
                "category": "system",
                "severity": "critical",
                "errorType": "OutOfMemoryError",
                "recommendations": [
                    "Check memory usage: free -h && top",
                    "Identify memory-intensive processes",
                    "Consider increasing system memory",
                    "Review application memory limits"
                ],
                "priority": 10
            })
        
        # Generic error detection
        error_patterns = re.findall(r'error|failed|exception|fatal', log_lower)
        if error_patterns and not analyses:
            error_count = len(error_patterns)
            severity = "high" if error_count > 3 else "medium"
            
            analyses.append({
                "summary": f"Multiple error indicators detected ({error_count} errors found) - requires investigation",
                "shortSummary": f"{error_count} errors detected",
                "category": "application",
                "severity": severity,
                "errorType": "MultipleErrors",
                "recommendations": [
                    "Review complete logs for specific error details",
                    "Check system resources and service status",
                    "Verify configuration files",
                    "Consider restarting affected services"
                ],
                "priority": 5
            })
        
        # Select highest priority analysis or default
        if analyses:
            best_analysis = max(analyses, key=lambda x: x.get('priority', 0))
            best_analysis.pop('priority', None)  # Remove priority from final result
        else:
            # Default analysis for unclear logs
            best_analysis = {
                "summary": "Log analysis completed - no clear errors detected but requires manual review",
                "shortSummary": "Manual review required",
                "category": "application",
                "severity": "low",
                "errorType": "UnclearStatus",
                "recommendations": [
                    "Manually review complete logs",
                    "Verify expected operation completed",
                    "Check system status and metrics"
                ]
            }
        
        # Add standard fields
        best_analysis.update({
            "rootCause": {
                "cause": best_analysis["errorType"],
                "description": best_analysis["summary"],
                "confidence": "high" if analyses else "low"
            },
            "urgency": best_analysis["severity"],
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production", 
                "service": best_analysis["category"],
                "analysis_type": "enhanced_pattern_matching"
            }
        })
        
        return best_analysis
    
    def _ai_analysis_with_timeout(self, logs: List[str], deployment_id: str, start_time: float, timeout: int = 15) -> Dict[str, Any]:
        """AI analysis with strict timeout and fallback"""
        
        log_sample = self._prepare_logs_minimal(logs)
        prompt = self._create_minimal_prompt(log_sample)
        
        try:
            print(f"Starting AI analysis with {timeout}s timeout...")
            
            ai_start = time.time()
            generate_params = {'prompt': prompt}
            generate_params.update(self.supported_params)
            
            response = self.model.generate(**generate_params)
            ai_duration = time.time() - ai_start
            
            print(f"AI response received in {ai_duration:.2f} seconds")
            
            if ai_duration > timeout:
                print(f"AI analysis exceeded timeout ({timeout}s), using fallback")
                return self._create_enhanced_pattern_analysis("\n".join(logs), deployment_id)
            
            analysis = self._parse_minimal_response(response, log_sample)
            print(f"Total analysis time: {time.time() - start_time:.2f} seconds")
            return analysis
            
        except Exception as e:
            print(f"AI analysis failed: {str(e)}, using pattern fallback")
            return self._create_enhanced_pattern_analysis("\n".join(logs), deployment_id)
    
    def _prepare_logs_minimal(self, logs: List[str], max_logs: int = 3, max_length: int = 60) -> str:
        """Minimal log preparation for fastest AI processing"""
        sample_logs = logs[:max_logs]
        
        cleaned = []
        for log in sample_logs:
            clean = re.sub(r'\s+', ' ', log.strip())
            if len(clean) > max_length:
                clean = clean[:max_length] + "..."
            cleaned.append(clean)
        
        return "\n".join(cleaned)
    
    def _create_minimal_prompt(self, logs: str) -> str:
        """Minimal prompt for fastest AI processing"""
        return f"""Logs: {logs}

JSON only: {{"summary": "brief issue", "severity": "high", "errorType": "Type"}}"""
    
    def _parse_minimal_response(self, response: str, original_logs: str) -> Dict[str, Any]:
        """Minimal response parsing with pattern fallback"""
        try:
            # Quick JSON extraction
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return self._expand_minimal_analysis(analysis, original_logs)
        except:
            pass
        
        # Fallback to pattern analysis
        return self._create_enhanced_pattern_analysis(original_logs, "unknown")
    
    def _expand_minimal_analysis(self, minimal: Dict[str, Any], logs: str) -> Dict[str, Any]:
        """Expand minimal AI analysis to full format"""
        return {
            "summary": minimal.get("summary", "Analysis completed"),
            "shortSummary": minimal.get("summary", "Analysis completed")[:50],
            "category": "application",
            "severity": minimal.get("severity", "medium"),
            "errorType": minimal.get("errorType", "Unknown"),
            "rootCause": {
                "cause": minimal.get("errorType", "Unknown"),
                "description": minimal.get("summary", "AI analysis completed"),
                "confidence": "medium"
            },
            "recommendations": [
                "Review detailed logs for specific issues",
                "Check system status and service health"
            ],
            "urgency": minimal.get("severity", "medium"),
            "context": {
                "deployment": "unknown",
                "environment": "production",
                "service": "ai-analyzer",
                "analysis_type": "minimal_ai_analysis"
            }
        }