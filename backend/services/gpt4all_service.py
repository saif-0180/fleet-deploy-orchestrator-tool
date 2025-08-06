
import json
import re
import os
import time
from typing import Dict, List, Any, Tuple
from gpt4all import GPT4All
from backend.config.gpt4all_config import GPT4ALL_CONFIG

class GPT4AllLogAnalyzer:
    def __init__(self, model_name=None, model_path=None):
        self.model_path = model_path or GPT4ALL_CONFIG['model_path']
        self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
        # Initialize model only if needed (lazy loading)
        self.model = None
        self.model_initialized = False
        
        print(f"GPT4All analyzer initialized (model will load on demand)")
        
        # Compile optimized patterns for better accuracy
        self._compile_optimized_patterns()
        
    def _compile_optimized_patterns(self):
        """Compile optimized regex patterns for accurate detection"""
        
        # SUCCESS PATTERNS - More specific to avoid false positives
        self.success_patterns = [
            # Explicit success statements
            re.compile(r'(?:successfully|completed successfully|operation successful)', re.IGNORECASE),
            re.compile(r'(?:deployment|installation|configuration)\s+(?:completed|successful|finished)', re.IGNORECASE),
            re.compile(r'(?:service|unit)\s+(?:started|enabled|activated)\s+successfully', re.IGNORECASE),
            
            # Ansible success indicators
            re.compile(r'PLAY RECAP.*failed=0.*unreachable=0', re.IGNORECASE),
            re.compile(r'ok=\d+.*changed=\d+.*unreachable=0.*failed=0', re.IGNORECASE),
            
            # Status success
            re.compile(r'status:\s*(?:success|ok|completed|active)', re.IGNORECASE),
            re.compile(r'result:\s*(?:success|ok|completed)', re.IGNORECASE),
        ]
        
        # FAILURE PATTERNS - Only clear failures
        self.failure_patterns = [
            # Clear failure statements
            re.compile(r'(?:failed to|failure|fatal error|critical error)', re.IGNORECASE),
            re.compile(r'(?:service|unit|deployment)\s+failed', re.IGNORECASE),
            re.compile(r'(?:connection refused|connection failed|timeout)', re.IGNORECASE),
            
            # Ansible failures
            re.compile(r'PLAY RECAP.*failed=[1-9]', re.IGNORECASE),
            re.compile(r'TASK.*FAILED', re.IGNORECASE),
            
            # System failures
            re.compile(r'(?:permission denied|file not found|command not found)', re.IGNORECASE),
        ]
        
        # DEPLOYMENT TYPE PATTERNS
        self.deployment_patterns = {
            'service_deployment': re.compile(r'(?:systemctl|service|daemon|unit)', re.IGNORECASE),
            'ansible_deployment': re.compile(r'(?:ansible|playbook|TASK|PLAY)', re.IGNORECASE),
            'application_deployment': re.compile(r'(?:application|app|deploy|installation)', re.IGNORECASE),
            'database_deployment': re.compile(r'(?:database|mysql|postgresql|db)', re.IGNORECASE),
            'network_deployment': re.compile(r'(?:network|firewall|iptables|route)', re.IGNORECASE),
            'configuration_deployment': re.compile(r'(?:config|configuration|setup|install)', re.IGNORECASE),
        }
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """Optimized log analysis with faster processing"""
        
        start_time = time.time()
        
        # Limit logs for faster processing (last 100 lines are usually most relevant)
        relevant_logs = logs[-100:] if len(logs) > 100 else logs
        full_log_text = "\n".join(relevant_logs)
        
        print(f"Analyzing {len(relevant_logs)} most recent log lines...")
        
        # Fast pattern-based analysis
        analysis_result = self._optimized_pattern_analysis(full_log_text, deployment_id)
        
        # Use AI only if pattern analysis is unclear and logs are short enough
        if (analysis_result.get("severity") == "medium" and 
            analysis_result.get("errorType") == "UnclearStatus" and 
            len(full_log_text) < 5000):  # Only for smaller logs to avoid timeout
            
            print("Pattern analysis unclear, using AI for enhancement...")
            analysis_result = self._enhance_with_ai(full_log_text, analysis_result, deployment_id)
        
        elapsed = time.time() - start_time
        print(f"Analysis completed in {elapsed:.2f} seconds")
        
        analysis_result["context"]["analysis_duration"] = f"{elapsed:.2f}s"
        analysis_result["context"]["log_lines_analyzed"] = len(relevant_logs)
        
        return analysis_result
    
    def _optimized_pattern_analysis(self, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Fast and accurate pattern-based analysis"""
        
        # Count pattern matches
        success_count = sum(1 for pattern in self.success_patterns if pattern.search(log_text))
        failure_count = sum(1 for pattern in self.failure_patterns if pattern.search(log_text))
        
        # Determine deployment type
        deployment_type = self._detect_deployment_type(log_text)
        
        print(f"Pattern analysis - Success: {success_count}, Failures: {failure_count}, Type: {deployment_type}")
        
        # Simple decision logic - prioritize explicit indicators
        if success_count > 0 and failure_count == 0:
            return self._create_success_result(deployment_type, log_text, deployment_id)
        elif failure_count > 0 and success_count == 0:
            return self._create_failure_result(deployment_type, log_text, deployment_id)
        elif success_count > failure_count:
            return self._create_success_result(deployment_type, log_text, deployment_id)
        elif failure_count > success_count:
            return self._create_failure_result(deployment_type, log_text, deployment_id)
        else:
            # Check for completion without explicit success/failure
            if re.search(r'(?:completed|finished|done)', log_text, re.IGNORECASE):
                return self._create_neutral_success_result(deployment_type, log_text, deployment_id)
            return self._create_unclear_result(deployment_type, log_text, deployment_id)
    
    def _detect_deployment_type(self, log_text: str) -> str:
        """Detect the type of deployment from log content"""
        
        type_scores = {}
        for dep_type, pattern in self.deployment_patterns.items():
            matches = len(pattern.findall(log_text))
            if matches > 0:
                type_scores[dep_type] = matches
        
        if type_scores:
            return max(type_scores, key=type_scores.get)
        return 'general_deployment'
    
    def _enhance_with_ai(self, log_text: str, base_analysis: Dict[str, Any], deployment_id: str) -> Dict[str, Any]:
        """Use AI to enhance unclear analysis with timeout protection"""
        
        try:
            if not self.model_initialized:
                print("Loading GPT4All model...")
                self.model = GPT4All(self.model_name, model_path=self.model_path)
                self.model_initialized = True
                print("Model loaded successfully")
            
            # Create concise prompt for faster processing
            prompt = f"""Analyze this deployment log briefly:

{log_text[:2000]}

Respond in exactly this format:
STATUS: [SUCCESS/FAILED/WARNING]
TYPE: [service/application/database/network/configuration]
SUMMARY: [One sentence summary]"""

            print("Generating AI analysis...")
            
            # Use shorter settings for faster response
            response = self.model.generate(
                prompt=prompt,
                max_tokens=150,  # Reduced for faster response
                temp=0.1,
                top_p=0.9
            )
            
            print(f"AI response received: {response[:100]}...")
            
            # Parse AI response
            return self._parse_ai_response(response, base_analysis, deployment_id)
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return base_analysis  # Return pattern-based analysis as fallback
    
    def _parse_ai_response(self, ai_response: str, base_analysis: Dict[str, Any], deployment_id: str) -> Dict[str, Any]:
        """Parse AI response and merge with base analysis"""
        
        try:
            lines = ai_response.strip().split('\n')
            
            status = "UNCLEAR"
            dep_type = "general"
            summary = "Analysis completed"
            
            for line in lines:
                if line.startswith('STATUS:'):
                    status = line.split(':', 1)[1].strip()
                elif line.startswith('TYPE:'):
                    dep_type = line.split(':', 1)[1].strip()
                elif line.startswith('SUMMARY:'):
                    summary = line.split(':', 1)[1].strip()
            
            # Map AI status to our format
            if status.upper() == 'SUCCESS':
                severity = 'low'
                error_type = 'Success'
                urgency = 'low'
            elif status.upper() == 'FAILED':
                severity = 'high'
                error_type = 'DeploymentError'
                urgency = 'high'
            else:
                severity = 'medium'
                error_type = 'CompletedWithWarnings'
                urgency = 'medium'
            
            # Update base analysis with AI insights
            base_analysis.update({
                "summary": summary,
                "shortSummary": f"{dep_type.title()} {status.lower()}",
                "category": dep_type,
                "severity": severity,
                "errorType": error_type,
                "urgency": urgency,
                "context": {
                    **base_analysis.get("context", {}),
                    "ai_enhanced": True,
                    "deployment_type": dep_type
                }
            })
            
            return base_analysis
            
        except Exception as e:
            print(f"Failed to parse AI response: {e}")
            return base_analysis
    
    def _create_success_result(self, deployment_type: str, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create success analysis result"""
        
        type_name = deployment_type.replace('_', ' ').title()
        
        return {
            "summary": f"{type_name} completed successfully without errors. All operations executed as expected.",
            "shortSummary": f"Successful {type_name}",
            "category": self._map_type_to_category(deployment_type),
            "severity": "low",
            "errorType": "Success",
            "rootCause": {
                "cause": f"Successful {deployment_type} execution",
                "description": f"The {deployment_type} completed successfully with all tasks executed properly",
                "confidence": "high"
            },
            "recommendations": [
                "No action required - deployment completed successfully",
                "Monitor system to ensure all changes are working as expected",
                "Document the successful deployment for future reference"
            ],
            "urgency": "low",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": deployment_type,
                "status": "success",
                "deployment_type": deployment_type
            }
        }
    
    def _create_failure_result(self, deployment_type: str, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create failure analysis result"""
        
        type_name = deployment_type.replace('_', ' ').title()
        
        return {
            "summary": f"{type_name} failed during execution. Critical errors were detected that prevented successful completion.",
            "shortSummary": f"Failed {type_name}",
            "category": self._map_type_to_category(deployment_type),
            "severity": "high",
            "errorType": "DeploymentError",
            "rootCause": {
                "cause": f"Failed {deployment_type} execution",
                "description": f"The {deployment_type} encountered critical errors that prevented successful completion",
                "confidence": "high"
            },
            "recommendations": [
                "Review the complete error logs to identify root cause",
                "Check system prerequisites and dependencies",
                "Verify configuration files and parameters",
                "Consider rolling back changes if system is unstable"
            ],
            "urgency": "high",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": deployment_type,
                "status": "failed",
                "deployment_type": deployment_type
            }
        }
    
    def _create_neutral_success_result(self, deployment_type: str, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create result for completed operations without clear indicators"""
        
        type_name = deployment_type.replace('_', ' ').title()
        
        return {
            "summary": f"{type_name} completed execution without detecting any critical errors. Manual verification recommended to confirm success.",
            "shortSummary": f"{type_name} Completed",
            "category": self._map_type_to_category(deployment_type),
            "severity": "low",
            "errorType": "Completed",
            "rootCause": {
                "cause": "Normal completion",
                "description": f"The {deployment_type} finished execution without explicit error indicators",
                "confidence": "medium"
            },
            "recommendations": [
                "Verify that all intended changes were applied correctly",
                "Check system functionality to confirm successful deployment",
                "Monitor system for any unexpected behavior"
            ],
            "urgency": "low",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": deployment_type,
                "status": "completed",
                "deployment_type": deployment_type
            }
        }
    
    def _create_unclear_result(self, deployment_type: str, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create result when analysis is unclear"""
        
        type_name = deployment_type.replace('_', ' ').title()
        
        return {
            "summary": f"{type_name} status is unclear from the available logs. Manual review is required to determine the actual deployment outcome.",
            "shortSummary": f"{type_name} Status Unclear",
            "category": self._map_type_to_category(deployment_type),
            "severity": "medium",
            "errorType": "UnclearStatus",
            "rootCause": {
                "cause": "Insufficient status indicators",
                "description": f"The {deployment_type} logs do not contain clear success or failure indicators",
                "confidence": "low"
            },
            "recommendations": [
                "Manually review the complete deployment logs",
                "Check system state to verify if deployment succeeded",
                "Test functionality to confirm deployment status",
                "Consider re-running deployment with verbose logging"
            ],
            "urgency": "medium",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": deployment_type,
                "status": "unclear",
                "deployment_type": deployment_type
            }
        }
    
    def _map_type_to_category(self, deployment_type: str) -> str:
        """Map deployment type to category"""
        mapping = {
            'service_deployment': 'system',
            'ansible_deployment': 'deployment',
            'application_deployment': 'application',
            'database_deployment': 'database',
            'network_deployment': 'network',
            'configuration_deployment': 'system',
            'general_deployment': 'application'
        }
        return mapping.get(deployment_type, 'application')
