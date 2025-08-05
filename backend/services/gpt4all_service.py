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
                print(f"Model {self.model_name} not found, using {available_models[0]}")
                self.model_name = available_models[0]
            else:
                raise FileNotFoundError(f"No models found in {self.model_path}")
        
        print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
        
        try:
            # Initialize model with minimal parameters to avoid version conflicts
            self.model = GPT4All(self.model_name, model_path=self.model_path)
            
            # Test the model with a simple generation to verify it works
            print("Testing model initialization...")
            test_response = self.model.generate("Test", max_tokens=5)
            print("Model test successful")
            
        except Exception as e:
            print(f"Model initialization failed: {e}")
            raise
        
        # Detect supported parameters for generate() method
        self.supported_params = self._detect_supported_params()
        print(f"Supported generate() parameters: {list(self.supported_params.keys())}")
        
    def _detect_supported_params(self) -> Dict[str, Any]:
        """Detect which parameters are supported by the generate() method"""
        try:
            # Get the signature of the generate method
            sig = inspect.signature(self.model.generate)
            params = sig.parameters
            
            # Common parameters and their default values
            common_params = {
                'max_tokens': 1000,
                'temp': 0.3,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
                'repeat_last_n': 64,
                'n_batch': 8,
                'n_predict': None,
                'streaming': False
            }
            
            # Only include parameters that are actually supported
            supported = {}
            for param_name, default_value in common_params.items():
                if param_name in params:
                    supported[param_name] = default_value
                    
            return supported
            
        except Exception as e:
            print(f"Could not detect supported parameters: {e}")
            # Fallback to minimal set
            return {'max_tokens': 1000}
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """
        Analyze logs using GPT4All and return structured analysis
        """
        # Prepare logs for analysis
        log_sample = self._prepare_logs(logs)
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(log_sample, deployment_id)
        
        # Generate analysis
        try:
            print(f"Sending prompt to GPT4All model...")
            print(f"Prompt length: {len(prompt)} characters")
            
            # Use only supported parameters
            generate_params = {'prompt': prompt}
            generate_params.update(self.supported_params)
            
            print(f"Using parameters: {list(generate_params.keys())}")
            
            # Try with chat session first (newer API)
            try:
                with self.model.chat_session():
                    response = self.model.generate(**generate_params)
            except Exception as chat_error:
                print(f"Chat session failed, trying direct generate: {chat_error}")
                # Fallback to direct generate call
                response = self.model.generate(**generate_params)
            
            print(f"Raw GPT4All response: {response[:500]}...")  # Debug output
            
            # Parse and structure the response
            analysis = self._parse_analysis_response(response)
            return analysis
            
        except Exception as e:
            print(f"GPT4All analysis failed: {str(e)}")
            return self._fallback_analysis(logs, str(e))
    
    def _prepare_logs(self, logs: List[str], max_logs: int = 10, max_log_length: int = 120) -> str:
        """Prepare logs for analysis - be more conservative with size"""
        # Take sample of logs if too many
        sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
        # Clean and format logs
        cleaned_logs = []
        for i, log in enumerate(sample_logs, 1):
            # Remove excessive whitespace and limit length
            clean_log = re.sub(r'\s+', ' ', log.strip())
            if len(clean_log) > max_log_length:
                clean_log = clean_log[:max_log_length] + "..."
            cleaned_logs.append(f"Log {i}: {clean_log}")
        
        return "\n".join(cleaned_logs)
    
    def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
        """Create a simpler, more direct prompt"""
        
        # Keep prompt shorter and more direct for compatibility
        prompt = f"""Analyze these deployment logs and respond with JSON:

DEPLOYMENT: {deployment_id or 'Unknown'}
LOGS:
{logs}

Respond with JSON format:
{{
  "summary": "Brief description of issues found",
  "shortSummary": "One line summary", 
  "category": "deployment|database|network|application",
  "severity": "critical|high|medium|low",
  "errorType": "Main error found",
  "recommendations": ["Fix suggestion 1", "Fix suggestion 2"]
}}

JSON response:"""

        # Ensure prompt isn't too long for the model
        if len(prompt) > 1500:
            # Truncate logs if prompt is too long
            logs_lines = logs.split('\n')
            truncated_logs = '\n'.join(logs_lines[:5])
            prompt = f"""Analyze these logs and respond with JSON:

LOGS:
{truncated_logs}

JSON format:
{{"summary": "Brief issue description", "shortSummary": "One line", "category": "application", "severity": "medium", "errorType": "Error type", "recommendations": ["Fix 1"]}}

JSON:"""

        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse GPT4All response into structured format"""
        try:
            print(f"Parsing response: {response[:200]}...")
            
            # Clean the response
            response = response.strip()
            
            # Find JSON in response - be more flexible
            json_patterns = [
                r'\{[^}]*"summary"[^}]*\}',  # Look for summary field
                r'\{.*?"shortSummary".*?\}',  # Look for shortSummary field
                r'\{.*?\}',  # Any JSON-like structure
            ]
            
            json_str = None
            for pattern in json_patterns:
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    json_str = match.group()
                    break
            
            if json_str:
                print(f"Extracted JSON: {json_str[:200]}...")
                
                # Try to parse JSON
                analysis = json.loads(json_str)
                
                # Validate and fix any missing required fields
                analysis = self._validate_and_fix_analysis(analysis)
                
                return analysis
            else:
                print("No JSON found in response, using text parser")
                return self._parse_text_response(response)
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return self._parse_text_response(response)
        except Exception as e:
            print(f"Parsing error: {e}")
            return self._parse_text_response(response)
    
    def _validate_and_fix_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix analysis structure"""
        
        # Check if we got template values
        template_indicators = [
            "brief description of issues found",
            "one line summary", 
            "main error found",
            "brief issue description"
        ]
        
        analysis_text = json.dumps(analysis).lower()
        has_template_text = any(indicator in analysis_text for indicator in template_indicators)
        
        if has_template_text:
            print("Detected template response, model didn't analyze properly")
            return self._create_generic_analysis()
        
        # Ensure required fields exist with defaults
        defaults = {
            'summary': analysis.get('summary', 'Log analysis completed'),
            'shortSummary': analysis.get('shortSummary', 'Analysis completed'),
            'category': analysis.get('category', 'application'),
            'severity': analysis.get('severity', 'medium'),
            'errorType': analysis.get('errorType', 'Unknown'),
            'rootCause': analysis.get('rootCause', {
                'cause': 'Analysis completed',
                'description': 'Log analysis was performed',
                'confidence': 'medium'
            }),
            'recommendations': analysis.get('recommendations', ['Review logs manually']),
            'urgency': analysis.get('urgency', analysis.get('severity', 'medium')),
            'context': analysis.get('context', {
                'deployment': 'unknown',
                'environment': 'unknown', 
                'service': 'unknown'
            })
        }
        
        # Update analysis with defaults for missing fields
        for key, default_value in defaults.items():
            if key not in analysis or not analysis[key]:
                analysis[key] = default_value
        
        return analysis
    
    def _create_generic_analysis(self) -> Dict[str, Any]:
        """Create a generic analysis when model fails"""
        return {
            "summary": "GPT4All model failed to provide proper analysis. The model may need different prompting or a different model variant should be used.",
            "shortSummary": "GPT4All analysis failed - using fallback",
            "category": "application",
            "severity": "medium", 
            "errorType": "ModelAnalysisFailure",
            "rootCause": {
                "cause": "GPT4All model compatibility issue",
                "description": "The local GPT4All model is not generating proper structured analysis responses",
                "confidence": "high"
            },
            "recommendations": [
                "Try a different GPT4All model (mistral-7b-instruct, nous-hermes)",
                "Check GPT4All version compatibility",
                "Verify model file integrity",
                "Consider using cloud-based analysis as fallback"
            ],
            "urgency": "low",
            "context": {
                "deployment": "unknown",
                "environment": "local",
                "service": "gpt4all-analyzer"
            }
        }
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Enhanced fallback parser for non-JSON responses"""
        
        # Try to extract meaningful information from text response
        severity = "medium"
        error_type = "TextResponse"
        category = "application"
        recommendations = []
        
        response_lower = response.lower()
        
        # Analyze severity from keywords
        if any(word in response_lower for word in ["critical", "fatal", "failed", "error", "crash"]):
            severity = "high"
        elif any(word in response_lower for word in ["warning", "warn", "issue"]):
            severity = "medium"
        
        # Try to determine category
        if any(word in response_lower for word in ["database", "postgres", "mysql", "sql"]):
            category = "database"
        elif any(word in response_lower for word in ["network", "connection", "port", "socket"]):
            category = "network"
        elif any(word in response_lower for word in ["memory", "ram", "oom", "disk", "space"]):
            category = "memory"
        elif any(word in response_lower for word in ["deploy", "deployment", "ansible", "helm"]):
            category = "deployment"
        
        # Extract potential recommendations from response
        if "restart" in response_lower:
            recommendations.append("Consider restarting the service")
        if "config" in response_lower:
            recommendations.append("Check configuration files")
        if "permission" in response_lower:
            recommendations.append("Verify file permissions")
        
        if not recommendations:
            recommendations = ["Review full response for insights", "Manual log analysis recommended"]
        
        return {
            "summary": f"GPT4All provided unstructured response. Key content: {response[:200]}{'...' if len(response) > 200 else ''}",
            "shortSummary": "Model returned text response instead of JSON",
            "category": category,
            "severity": severity,
            "errorType": error_type,
            "rootCause": {
                "cause": "GPT4All unstructured response",
                "description": f"Model provided text instead of JSON structure, content analyzed for keywords",
                "confidence": "low"
            },
            "recommendations": recommendations,
            "urgency": severity,
            "context": {
                "deployment": "unknown",
                "environment": "unknown",
                "service": "gpt4all-analyzer",
                "raw_response": response[:500]
            }
        }
    
    def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
        """Enhanced fallback analysis when AI fails"""
        
        # Enhanced pattern matching with more specific patterns
        error_patterns = {
            r"postgresql.*failed|postgres.*error": ("high", "PostgreSQLError", "database"),
            r"mysql.*failed|mysql.*error": ("high", "MySQLError", "database"),
            r"connection.*refused|connection.*failed": ("high", "ConnectionFailure", "network"),
            r"ansible.*failed|playbook.*failed": ("high", "AnsibleFailure", "deployment"),
            r"systemctl.*failed|service.*failed": ("high", "ServiceFailure", "deployment"),
            r"error|failed|exception|fatal": ("high", "GeneralError", "application"),
            r"warning|warn": ("medium", "Warning", "application"),
            r"timeout|timed out": ("high", "Timeout", "network"),
            r"no such file|file not found|missing": ("medium", "FileNotFound", "filesystem"),
            r"permission denied|access denied": ("medium", "PermissionError", "security"),
            r"out of memory|oom": ("critical", "MemoryError", "memory"),
            r"disk.*full|no space": ("critical", "DiskSpace", "filesystem"),
            r"port.*already in use|address already in use": ("medium", "PortConflict", "network"),
        }
        
        severity = "low"
        found_errors = []
        error_types = []
        categories = []
        recommendations = []
        
        log_text = " ".join(logs[:10]).lower()
        
        for pattern, (sev, error_type, category) in error_patterns.items():
            if re.search(pattern, log_text):
                found_errors.append(pattern.split('|')[0])
                error_types.append(error_type)
                categories.append(category)
                
                # Add specific recommendations based on error type
                if "postgresql" in pattern:
                    recommendations.extend(["Check PostgreSQL service status", "Verify database configuration"])
                elif "connection" in pattern:
                    recommendations.extend(["Check network connectivity", "Verify service ports"])
                elif "ansible" in pattern:
                    recommendations.extend(["Review Ansible playbook", "Check target host connectivity"])
                
                # Update severity
                if (sev == "critical" or 
                    (sev == "high" and severity not in ["critical"]) or 
                    (sev == "medium" and severity == "low")):
                    severity = sev
        
        if not recommendations:
            recommendations = [
                "Check GPT4All service status and logs",
                "Verify model files are accessible", 
                "Review system resources (RAM/CPU)",
                "Manual log review recommended"
            ]
        
        primary_category = categories[0] if categories else "application"
        primary_error = error_types[0] if error_types else "PatternMatched"
        
        return {
            "summary": f"GPT4All analysis failed: {error}. Pattern analysis found {len(found_errors)} issues: {', '.join(found_errors[:3])}",
            "shortSummary": f"AI failed, pattern matching found {len(found_errors)} issues",
            "category": primary_category,
            "severity": severity,
            "errorType": primary_error,
            "rootCause": {
                "cause": f"GPT4All error: {error}",
                "description": f"Local AI failed but pattern matching identified: {', '.join(error_types[:3])}",
                "confidence": "medium"
            },
            "recommendations": recommendations[:5],  # Limit recommendations
            "urgency": severity if severity != "low" else "medium",
            "context": {
                "deployment": "unknown",
                "environment": "local", 
                "service": "gpt4all-analyzer",
                "error": error,
                "patterns_found": found_errors[:5],
                "categories_detected": categories[:3]
            }
        }

# import json
# import re
# import os
# from typing import Dict, List, Any
# from gpt4all import GPT4All
# from backend.config.gpt4all_config import GPT4ALL_CONFIG

# class GPT4AllLogAnalyzer:
#     def __init__(self, model_name=None, model_path=None):
#         self.model_path = model_path or GPT4ALL_CONFIG['model_path']
#         self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
#         # Verify model exists locally
#         model_file_path = os.path.join(self.model_path, self.model_name)
#         if not os.path.exists(model_file_path):
#             available_models = [f for f in os.listdir(self.model_path) if f.endswith('.gguf')]
#             if available_models:
#                 print(f"Model {self.model_name} not found, using {available_models[0]}")
#                 self.model_name = available_models[0]
#             else:
#                 raise FileNotFoundError(f"No models found in {self.model_path}")
        
#         print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
#         self.model = GPT4All(self.model_name, model_path=self.model_path)
        
#     def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
#         """
#         Analyze logs using GPT4All and return structured analysis
#         """
#         # Prepare logs for analysis
#         log_sample = self._prepare_logs(logs)
        
#         # Create analysis prompt
#         prompt = self._create_analysis_prompt(log_sample, deployment_id)
        
#         # Generate analysis
#         try:
#             print(f"Sending prompt to GPT4All model...")
#             print(f"Prompt length: {len(prompt)} characters")
            
#             response = self.model.generate(
#                 prompt, 
#                 max_tokens=2000,  # Increased for more detailed response
#                 temp=0.3,         # Slightly higher for more creativity
#                 top_p=0.9,
#                 repeat_penalty=1.1,  # Prevent repetition
#                 n_threads=4      # Use multiple threads if available
#             )
            
#             print(f"Raw GPT4All response: {response[:500]}...")  # Debug output
            
#             # Parse and structure the response
#             analysis = self._parse_analysis_response(response)
#             return analysis
            
#         except Exception as e:
#             print(f"GPT4All analysis failed: {str(e)}")
#             return self._fallback_analysis(logs, str(e))
    
#     def _prepare_logs(self, logs: List[str], max_logs: int = 15, max_log_length: int = 150) -> str:
#         """Prepare logs for analysis - limit size and clean"""
#         # Take sample of logs if too many
#         sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
#         # Clean and format logs
#         cleaned_logs = []
#         for i, log in enumerate(sample_logs, 1):
#             # Remove excessive whitespace and limit length
#             clean_log = re.sub(r'\s+', ' ', log.strip())
#             if len(clean_log) > max_log_length:
#                 clean_log = clean_log[:max_log_length] + "..."
#             cleaned_logs.append(f"Log {i}: {clean_log}")
        
#         return "\n".join(cleaned_logs)
    
#     def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
#         """Create structured prompt for log analysis"""
#         prompt = f"""You are an expert system administrator. Analyze these deployment logs and provide specific insights.

# DEPLOYMENT ID: {deployment_id or 'Unknown'}

# LOGS TO ANALYZE:
# {logs}

# Based on these specific logs, provide a JSON response with your analysis. Look for:
# - Error messages and their causes
# - Failed services or processes  
# - Resource issues (memory, disk, network)
# - Configuration problems
# - Security issues

# Example of good analysis:
# {{
#     "summary": "PostgreSQL failed to start due to missing postgresql.conf file",
#     "shortSummary": "PostgreSQL service startup failure - missing config",
#     "category": "database",
#     "severity": "critical",
#     "errorType": "ConfigurationMissing",
#     "rootCause": {{
#         "cause": "Missing postgresql.conf configuration file",
#         "description": "PostgreSQL service cannot start because the required configuration file is not found at the expected location",
#         "confidence": "high"
#     }},
#     "recommendations": [
#         "Check if postgresql.conf exists in /etc/postgresql/",
#         "Restore configuration from backup",
#         "Reinstall PostgreSQL if config is corrupted"
#     ],
#     "urgency": "critical",
#     "context": {{
#         "deployment": "{deployment_id or 'Unknown'}",
#         "environment": "production",
#         "service": "postgresql"
#     }}
# }}

# Now analyze the actual logs above and respond with similar JSON containing your specific findings:"""

#         return prompt

#     def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
#         """Parse GPT4All response into structured format"""
#         try:
#             print(f"Parsing response: {response[:200]}...")
            
#             # Clean the response - remove any text before/after JSON
#             response = response.strip()
            
#             # Find JSON in response
#             json_start = response.find('{')
#             json_end = response.rfind('}') + 1
            
#             if json_start >= 0 and json_end > json_start:
#                 json_str = response[json_start:json_end]
#                 print(f"Extracted JSON: {json_str[:200]}...")
                
#                 analysis = json.loads(json_str)
                
#                 # Validate and fix any missing required fields
#                 analysis = self._validate_and_fix_analysis(analysis)
                
#                 return analysis
#             else:
#                 print("No JSON found in response, using text parser")
#                 return self._parse_text_response(response)
                
#         except json.JSONDecodeError as e:
#             print(f"JSON decode error: {e}")
#             return self._parse_text_response(response)
#         except Exception as e:
#             print(f"Parsing error: {e}")
#             return self._parse_text_response(response)
    
#     def _validate_and_fix_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
#         """Validate and fix analysis structure"""
        
#         # Check if we got template values (indicates model didn't analyze properly)
#         template_indicators = [
#             "Brief summary of main issues found",
#             "One-line summary of the problem", 
#             "Main error type identified",
#             "which category to which it belongs",
#             "inferred from logs or 'unknown'"
#         ]
        
#         # If analysis contains template text, it means the model didn't analyze properly
#         analysis_text = json.dumps(analysis).lower()
#         has_template_text = any(indicator.lower() in analysis_text for indicator in template_indicators)
        
#         if has_template_text:
#             print("Detected template response, model didn't analyze properly")
#             return self._create_generic_analysis()
        
#         # Ensure required fields exist
#         required_fields = {
#             'summary': 'Log analysis completed',
#             'shortSummary': 'Analysis summary',
#             'category': 'application',
#             'severity': 'medium',
#             'errorType': 'Unknown',
#             'rootCause': {
#                 'cause': 'Analysis completed',
#                 'description': 'Log analysis was performed',
#                 'confidence': 'medium'
#             },
#             'recommendations': ['Review logs for specific issues'],
#             'urgency': 'medium',
#             'context': {
#                 'deployment': 'unknown',
#                 'environment': 'unknown', 
#                 'service': 'unknown'
#             }
#         }
        
#         for field, default in required_fields.items():
#             if field not in analysis or not analysis[field]:
#                 analysis[field] = default
        
#         return analysis
    
#     def _create_generic_analysis(self) -> Dict[str, Any]:
#         """Create a generic analysis when model fails to analyze properly"""
#         return {
#             "summary": "Model returned template response instead of analysis. This indicates the local LLM may need fine-tuning for log analysis tasks.",
#             "shortSummary": "GPT4All model needs better prompting or fine-tuning",
#             "category": "application",
#             "severity": "medium", 
#             "errorType": "ModelAnalysisFailure",
#             "rootCause": {
#                 "cause": "Local LLM returned template instead of analysis",
#                 "description": "The GPT4All model is not properly analyzing the logs and instead returning the prompt template structure",
#                 "confidence": "high"
#             },
#             "recommendations": [
#                 "Try a different GPT4All model variant",
#                 "Adjust prompt temperature and parameters",
#                 "Consider using a model specifically trained for log analysis",
#                 "Manually review the logs for now"
#             ],
#             "urgency": "low",
#             "context": {
#                 "deployment": "unknown",
#                 "environment": "local",
#                 "service": "gpt4all-analyzer"
#             }
#         }
    
#     def _parse_text_response(self, response: str) -> Dict[str, Any]:
#         """Fallback parser for non-JSON responses"""
        
#         # Try to extract meaningful information from text response
#         severity = "medium"
#         error_type = "TextResponse"
#         category = "application"
        
#         response_lower = response.lower()
        
#         # Analyze severity from keywords
#         if any(word in response_lower for word in ["critical", "fatal", "failed", "error", "crash"]):
#             severity = "high"
#         elif any(word in response_lower for word in ["warning", "warn", "issue"]):
#             severity = "medium"
        
#         # Try to determine category
#         if any(word in response_lower for word in ["database", "postgres", "mysql", "sql"]):
#             category = "database"
#         elif any(word in response_lower for word in ["network", "connection", "port", "socket"]):
#             category = "network"
#         elif any(word in response_lower for word in ["memory", "ram", "oom", "disk", "space"]):
#             category = "memory"
#         elif any(word in response_lower for word in ["deploy", "deployment", "ansible", "helm"]):
#             category = "deployment"
        
#         return {
#             "summary": f"GPT4All provided text response: {response[:300]}{'...' if len(response) > 300 else ''}",
#             "shortSummary": "Model returned unstructured text response",
#             "category": category,
#             "severity": severity,
#             "errorType": error_type,
#             "rootCause": {
#                 "cause": "GPT4All text response parsing",
#                 "description": f"Model provided unstructured response, extracted key information where possible",
#                 "confidence": "low"
#             },
#             "recommendations": [
#                 "Review full GPT4All response for insights",
#                 "Try adjusting model parameters",
#                 "Consider using structured prompting techniques",
#                 "Manual log review may be needed"
#             ],
#             "urgency": "low",
#             "context": {
#                 "deployment": "unknown",
#                 "environment": "unknown",
#                 "service": "gpt4all-analyzer",
#                 "raw_response": response[:1000]  # Include more of raw response
#             }
#         }
    
#     def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
#         """Enhanced fallback analysis when AI fails"""
#         # Enhanced pattern matching
#         error_patterns = {
#             r"error|failed|exception|fatal": ("high", "Error"),
#             r"warning|warn": ("medium", "Warning"), 
#             r"timeout|timed out": ("high", "Timeout"),
#             r"connection.*refused|connection.*failed": ("high", "ConnectionFailure"),
#             r"no such file|file not found|missing": ("medium", "FileNotFound"),
#             r"permission denied|access denied": ("medium", "PermissionError"),
#             r"out of memory|oom|memory": ("critical", "MemoryError"),
#             r"disk.*full|no space": ("critical", "DiskSpace"),
#             r"port.*already in use|address already in use": ("medium", "PortConflict"),
#             r"authentication.*failed|login.*failed": ("high", "AuthenticationFailure")
#         }
        
#         severity = "low"
#         found_errors = []
#         error_types = []
#         categories = []
        
#         log_text = " ".join(logs[:20]).lower()  # Combine logs for analysis
        
#         for pattern, (sev, error_type) in error_patterns.items():
#             if re.search(pattern, log_text):
#                 found_errors.append(pattern.split('|')[0])  # Take first alternative
#                 error_types.append(error_type)
                
#                 # Update severity (critical > high > medium > low)
#                 if sev == "critical" or (sev == "high" and severity not in ["critical"]) or (sev == "medium" and severity == "low"):
#                     severity = sev
        
#         # Determine category from content
#         if re.search(r"postgres|mysql|database|sql", log_text):
#             categories.append("database")
#         if re.search(r"network|connection|port|socket", log_text):
#             categories.append("network") 
#         if re.search(r"memory|disk|filesystem", log_text):
#             categories.append("memory")
#         if re.search(r"deploy|ansible|helm|systemctl", log_text):
#             categories.append("deployment")
            
#         primary_category = categories[0] if categories else "application"
#         primary_error = error_types[0] if error_types else "PatternMatched"
        
#         return {
#             "summary": f"Fallback analysis: GPT4All failed ({error}). Pattern matching found: {', '.join(found_errors[:3])}",
#             "shortSummary": f"AI analysis failed - found {len(found_errors)} potential issues",
#             "category": primary_category,
#             "severity": severity,
#             "errorType": primary_error,
#             "rootCause": {
#                 "cause": f"GPT4All processing error: {error}",
#                 "description": f"Local AI model failed, but pattern matching identified: {', '.join(error_types[:3])}",
#                 "confidence": "medium"
#             },
#             "recommendations": [
#                 "Fix GPT4All service issues first",
#                 "Check system resources (RAM/CPU usage)",
#                 "Verify model files are not corrupted",
#                 f"Address found issues: {', '.join(found_errors[:3])}" if found_errors else "Manual log review needed"
#             ],
#             "urgency": severity if severity != "low" else "medium",
#             "context": {
#                 "deployment": "unknown",
#                 "environment": "local", 
#                 "service": "gpt4all-analyzer",
#                 "error": error,
#                 "patterns_found": found_errors,
#                 "categories_detected": categories
#             }
#         }

# # import json
# # import re
# # import os
# # from typing import Dict, List, Any
# # from gpt4all import GPT4All
# # from backend.config.gpt4all_config import GPT4ALL_CONFIG

# # class GPT4AllLogAnalyzer:
# #     def __init__(self, model_name=None, model_path=None):
# #         self.model_path = model_path or GPT4ALL_CONFIG['model_path']
# #         self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
# #         # Verify model exists locally
# #         model_file_path = os.path.join(self.model_path, self.model_name)
# #         if not os.path.exists(model_file_path):
# #             available_models = [f for f in os.listdir(self.model_path) if f.endswith('.gguf')]
# #             if available_models:
# #                 print(f"Model {self.model_name} not found, using {available_models[0]}")
# #                 self.model_name = available_models[0]
# #             else:
# #                 raise FileNotFoundError(f"No models found in {self.model_path}")
        
# #         print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
# #         self.model = GPT4All(self.model_name, model_path=self.model_path)
        
# #     def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
# #         """
# #         Analyze logs using GPT4All and return structured analysis
# #         """
# #         # Prepare logs for analysis
# #         log_sample = self._prepare_logs(logs)
        
# #         # Create analysis prompt
# #         prompt = self._create_analysis_prompt(log_sample, deployment_id)
        
# #         # Generate analysis
# #         try:
# #             with self.model.chat_session():
# #                 response = self.model.generate(
# #                     prompt, 
# #                     max_tokens=1000,
# #                     temp=0.1,
# #                     top_p=0.9
# #                 )
                
# #             # Parse and structure the response
# #             analysis = self._parse_analysis_response(response)
# #             return analysis
            
# #         except Exception as e:
# #             return self._fallback_analysis(logs, str(e))
    
# #     def _prepare_logs(self, logs: List[str], max_logs: int = 20, max_log_length: int = 100) -> str:
# #         """Prepare logs for analysis - limit size and clean"""
# #         # Take sample of logs if too many
# #         sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
# #         # Clean and format logs
# #         cleaned_logs = []
# #         for log in sample_logs:
# #             # Remove excessive whitespace and limit length
# #             clean_log = re.sub(r'\s+', ' ', log.strip())
# #             if len(clean_log) > max_log_length:
# #                 clean_log = clean_log[:max_log_length] + "..."
# #             cleaned_logs.append(clean_log)
        
# #         return "\n".join(cleaned_logs)
    
# #     def count_tokens(self, text: str) -> int:
# #         """Count the number of tokens in the text"""
# #         return len(text.split())
    
# #     def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
# #         """Create structured prompt for log analysis"""
# #         prompt_template = """
# # You are an expert system administrator analyzing deployment logs. 
# # Analyze the following logs and provide a structured JSON response with error analysis.

# # Deployment ID: {deployment_id}

# # Logs to analyze:
# # {logs}

# # Please provide analysis in this exact JSON format:
# # {{
# #     "summary": "Brief summary of main issues found",
# #     "shortSummary": "One-line summary of the problem",
# #     "category": "which category to which it belongs deployment|database|network|security|filesystem|memory|application",
# #     "severity": "critical|high|medium|low",
# #     "errorType": "Main error type identified",
# #     "rootCause": {{
# #         "cause": "Summarized root cause",
# #         "description": "Explanation of what caused the issue based on logs",
# #         "confidence": "Model confidence in this diagnosis: high|medium|low"
# #     }},
# #     "recommendations": ["Suggested remediation steps based on log context, e.g., restart service, update config, free memory"],
# #     "urgency": "critical|high|medium|low",
# #     "context": {{
# #         "deployment": "{deployment_id}",
# #         "environment": "inferred from logs or 'unknown'",
# #         "service": "inferred from logs it could be file copy, sql operation, systemctl service , helm etc or 'unknown'"
# #     }}
# # }}

# # Focus on:
# # 1. Error patterns and frequency
# # 2. Critical failures vs warnings
# # 3. System resource issues
# # 4. Configuration problems
# # 5. Actionable recommendations

# # Respond only with the JSON, no additional text.
# # """
# #         prompt = prompt_template.format(deployment_id=deployment_id or 'Unknown', logs=logs)
        
# #         # Ensure the prompt does not exceed the token limit
# #         max_tokens = 2048
# #         while self.count_tokens(prompt) > max_tokens:
# #             logs = logs.rsplit('\n', 1)[0]  # Remove the last log entry
# #             prompt = prompt_template.format(deployment_id=deployment_id or 'Unknown', logs=logs)
        
# #         return prompt

# #     def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
# #         """Parse GPT4All response into structured format"""
# #         try:
# #             # Try to extract JSON from response
# #             json_match = re.search(r'\{.*\}', response, re.DOTALL)
# #             if json_match:
# #                 json_str = json_match.group()
# #                 analysis = json.loads(json_str)
                
# #                 # Validate required fields
# #                 required_fields = ['summary', 'shortSummary', 'category', 'severity', 'errorType']
# #                 for field in required_fields:
# #                     if field not in analysis:
# #                         analysis[field] = 'Unknown'
                
# #                 return analysis
# #             else:
# #                 # Fallback parsing if JSON extraction fails
# #                 return self._parse_text_response(response)
                
# #         except json.JSONDecodeError:
# #             return self._parse_text_response(response)
    
# #     def _parse_text_response(self, response: str) -> Dict[str, Any]:
# #         """Fallback parser for non-JSON responses"""
# #         return {
# #             "summary": f"AI Analysis: {response[:200]}...",
# #             "shortSummary": "Log analysis completed with text response",
# #             "category": "application",
# #             "severity": "medium",
# #             "errorType": "AnalysisError",
# #             "rootCause": {
# #                 "cause": "Response parsing issue",
# #                 "description": "GPT4All provided text response instead of JSON",
# #                 "confidence": "low"
# #             },
# #             "recommendations": [
# #                 "Review raw AI response for insights",
# #                 "Check log format and content",
# #                 "Consider model retraining for structured output"
# #             ],
# #             "urgency": "low",
# #             "context": {
# #                 "deployment": "unknown",
# #                 "environment": "unknown",
# #                 "service": "log-analyzer",
# #                 "raw_response": response[:500]
# #             }
# #         }
    
# #     def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
# #         """Fallback analysis when AI fails"""
# #         # Basic pattern matching fallback
# #         error_patterns = {
# #             "error": "high",
# #             "failed": "high", 
# #             "exception": "medium",
# #             "warning": "low",
# #             "timeout": "high",
# #             "connection": "medium"
# #         }
        
# #         severity = "low"
# #         found_errors = []
        
# #         for log in logs[:10]:  # Check first 10 logs
# #             log_lower = log.lower()
# #             for pattern, sev in error_patterns.items():
# #                 if pattern in log_lower:
# #                     found_errors.append(pattern)
# #                     if sev == "high":
# #                         severity = "high"
# #                     elif sev == "medium" and severity != "high":
# #                         severity = "medium"
        
# #         return {
# #             "summary": f"GPT4All analysis failed: {error}. Found patterns: {', '.join(found_errors)}",
# #             "shortSummary": "Offline AI analysis unavailable - using pattern matching",
# #             "category": "application",
# #             "severity": severity,
# #             "errorType": "AIAnalysisFailure",
# #             "rootCause": {
# #                 "cause": "GPT4All processing error",
# #                 "description": f"Local AI model encountered error: {error}",
# #                 "confidence": "high"
# #             },
# #             "recommendations": [
# #                 "Check GPT4All service status",
# #                 "Verify model files are accessible",
# #                 "Review system resources (RAM/CPU)",
# #                 "Consider fallback to manual log review"
# #             ],
# #             "urgency": "medium",
# #             "context": {
# #                 "deployment": "unknown",
# #                 "environment": "local",
# #                 "service": "gpt4all-analyzer",
# #                 "error": error,
# #                 "patterns_found": found_errors
# #             }
# #         }
# # # import json
# # # import re
# # # import os
# # # from typing import Dict, List, Any
# # # from gpt4all import GPT4All
# # # from backend.config.gpt4all_config import GPT4ALL_CONFIG

# # # class GPT4AllLogAnalyzer:
# # #     def __init__(self, model_name=None, model_path=None):
# # #         self.model_path = model_path or GPT4ALL_CONFIG['model_path']
# # #         self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
# # #         # Verify model exists locally
# # #         model_file_path = os.path.join(self.model_path, self.model_name)
# # #         if not os.path.exists(model_file_path):
# # #             available_models = [f for f in os.listdir(self.model_path) if f.endswith('.gguf')]
# # #             if available_models:
# # #                 print(f"Model {self.model_name} not found, using {available_models[0]}")
# # #                 self.model_name = available_models[0]
# # #             else:
# # #                 raise FileNotFoundError(f"No models found in {self.model_path}")
        
# # #         print(f"Initializing GPT4All with model: {self.model_name} from {self.model_path}")
# # #         self.model = GPT4All(self.model_name, model_path=self.model_path)
        
# # #     def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
# # #         """
# # #         Analyze logs using GPT4All and return structured analysis
# # #         """
# # #         # Prepare logs for analysis
# # #         log_sample = self._prepare_logs(logs)
        
# # #         # Create analysis prompt
# # #         prompt = self._create_analysis_prompt(log_sample, deployment_id)
        
# # #         # Generate analysis
# # #         try:
# # #             with self.model.chat_session():
# # #                 response = self.model.generate(
# # #                     prompt, 
# # #                     max_tokens=1000,
# # #                     temp=0.1,
# # #                     top_p=0.9
# # #                 )
                
# # #             # Parse and structure the response
# # #             analysis = self._parse_analysis_response(response)
# # #             return analysis
            
# # #         except Exception as e:
# # #             return self._fallback_analysis(logs, str(e))
    
# # #     def _prepare_logs(self, logs: List[str], max_logs: int = 50) -> str:
# # #         """Prepare logs for analysis - limit size and clean"""
# # #         # Take sample of logs if too many
# # #         sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
# # #         # Clean and format logs
# # #         cleaned_logs = []
# # #         for log in sample_logs:
# # #             # Remove excessive whitespace and limit length
# # #             clean_log = re.sub(r'\s+', ' ', log.strip())
# # #             if len(clean_log) > 200:
# # #                 clean_log = clean_log[:200] + "..."
# # #             cleaned_logs.append(clean_log)
        
# # #         return "\n".join(cleaned_logs)
    
# # #     def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
# # #         """Create structured prompt for log analysis"""
# # #         return f"""
# # # You are an expert system administrator analyzing deployment logs. 
# # # Analyze the following logs and provide a structured JSON response with error analysis.

# # # Deployment ID: {deployment_id or 'Unknown'}

# # # Logs to analyze:
# # # {logs}

# # # Please provide analysis in this exact JSON format:
# # # {{
# # #     "summary": "Brief summary of main issues found",
# # #     "shortSummary": "One-line summary of the problem",
# # #     "category": "deployment|database|network|security|filesystem|memory|application",
# # #     "severity": "critical|high|medium|low",
# # #     "errorType": "Main error type identified",
# # #     "rootCause": {{
# # #         "cause": "Primary cause of the issue",
# # #         "description": "Detailed description of the root cause",
# # #         "confidence": "high|medium|low"
# # #     }},
# # #     "recommendations": ["Action 1", "Action 2", "Action 3"],
# # #     "urgency": "critical|high|medium|low",
# # #     "context": {{
# # #         "deployment": "{deployment_id or 'unknown'}",
# # #         "environment": "detected environment",
# # #         "service": "detected service name"
# # #     }}
# # # }}

# # # Focus on:
# # # 1. Error patterns and frequency
# # # 2. Critical failures vs warnings
# # # 3. System resource issues
# # # 4. Configuration problems
# # # 5. Actionable recommendations

# # # Respond only with the JSON, no additional text.
# # # """

# # #     def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
# # #         """Parse GPT4All response into structured format"""
# # #         try:
# # #             # Try to extract JSON from response
# # #             json_match = re.search(r'\{.*\}', response, re.DOTALL)
# # #             if json_match:
# # #                 json_str = json_match.group()
# # #                 analysis = json.loads(json_str)
                
# # #                 # Validate required fields
# # #                 required_fields = ['summary', 'shortSummary', 'category', 'severity', 'errorType']
# # #                 for field in required_fields:
# # #                     if field not in analysis:
# # #                         analysis[field] = 'Unknown'
                
# # #                 return analysis
# # #             else:
# # #                 # Fallback parsing if JSON extraction fails
# # #                 return self._parse_text_response(response)
                
# # #         except json.JSONDecodeError:
# # #             return self._parse_text_response(response)
    
# # #     def _parse_text_response(self, response: str) -> Dict[str, Any]:
# # #         """Fallback parser for non-JSON responses"""
# # #         return {
# # #             "summary": f"AI Analysis: {response[:200]}...",
# # #             "shortSummary": "Log analysis completed with text response",
# # #             "category": "application",
# # #             "severity": "medium",
# # #             "errorType": "AnalysisError",
# # #             "rootCause": {
# # #                 "cause": "Response parsing issue",
# # #                 "description": "GPT4All provided text response instead of JSON",
# # #                 "confidence": "low"
# # #             },
# # #             "recommendations": [
# # #                 "Review raw AI response for insights",
# # #                 "Check log format and content",
# # #                 "Consider model retraining for structured output"
# # #             ],
# # #             "urgency": "low",
# # #             "context": {
# # #                 "deployment": "unknown",
# # #                 "environment": "unknown",
# # #                 "service": "log-analyzer",
# # #                 "raw_response": response[:500]
# # #             }
# # #         }
    
# # #     def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
# # #         """Fallback analysis when AI fails"""
# # #         # Basic pattern matching fallback
# # #         error_patterns = {
# # #             "error": "high",
# # #             "failed": "high", 
# # #             "exception": "medium",
# # #             "warning": "low",
# # #             "timeout": "high",
# # #             "connection": "medium"
# # #         }
        
# # #         severity = "low"
# # #         found_errors = []
        
# # #         for log in logs[:10]:  # Check first 10 logs
# # #             log_lower = log.lower()
# # #             for pattern, sev in error_patterns.items():
# # #                 if pattern in log_lower:
# # #                     found_errors.append(pattern)
# # #                     if sev == "high":
# # #                         severity = "high"
# # #                     elif sev == "medium" and severity != "high":
# # #                         severity = "medium"
        
# # #         return {
# # #             "summary": f"GPT4All analysis failed: {error}. Found patterns: {', '.join(found_errors)}",
# # #             "shortSummary": "Offline AI analysis unavailable - using pattern matching",
# # #             "category": "application",
# # #             "severity": severity,
# # #             "errorType": "AIAnalysisFailure",
# # #             "rootCause": {
# # #                 "cause": "GPT4All processing error",
# # #                 "description": f"Local AI model encountered error: {error}",
# # #                 "confidence": "high"
# # #             },
# # #             "recommendations": [
# # #                 "Check GPT4All service status",
# # #                 "Verify model files are accessible",
# # #                 "Review system resources (RAM/CPU)",
# # #                 "Consider fallback to manual log review"
# # #             ],
# # #             "urgency": "medium",
# # #             "context": {
# # #                 "deployment": "unknown",
# # #                 "environment": "local",
# # #                 "service": "gpt4all-analyzer",
# # #                 "error": error,
# # #                 "patterns_found": found_errors
# # #             }
# # #         }
