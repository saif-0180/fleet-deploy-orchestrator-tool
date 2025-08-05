import json
import re
import os
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
        self.model = GPT4All(self.model_name, model_path=self.model_path)
        
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
            with self.model.chat_session():
                response = self.model.generate(
                    prompt, 
                    max_tokens=1000,
                    temp=0.1,
                    top_p=0.9
                )
                
            # Parse and structure the response
            analysis = self._parse_analysis_response(response)
            return analysis
            
        except Exception as e:
            return self._fallback_analysis(logs, str(e))
    
    def _prepare_logs(self, logs: List[str], max_logs: int = 20, max_log_length: int = 100) -> str:
        """Prepare logs for analysis - limit size and clean"""
        # Take sample of logs if too many
        sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
        # Clean and format logs
        cleaned_logs = []
        for log in sample_logs:
            # Remove excessive whitespace and limit length
            clean_log = re.sub(r'\s+', ' ', log.strip())
            if len(clean_log) > max_log_length:
                clean_log = clean_log[:max_log_length] + "..."
            cleaned_logs.append(clean_log)
        
        return "\n".join(cleaned_logs)
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text"""
        return len(text.split())
    
    def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
        """Create structured prompt for log analysis"""
        prompt_template = """
You are an expert system administrator analyzing deployment logs. 
Analyze the following logs and provide a structured JSON response with error analysis.

Deployment ID: {deployment_id}

Logs to analyze:
{logs}

Please provide analysis in this exact JSON format:
{{
    "summary": "Brief summary of main issues found",
    "shortSummary": "One-line summary of the problem",
    "category": "deployment|database|network|security|filesystem|memory|application",
    "severity": "critical|high|medium|low",
    "errorType": "Main error type identified",
    "rootCause": {{
        "cause": "Primary cause of the issue",
        "description": "Detailed description of the root cause",
        "confidence": "high|medium|low"
    }},
    "recommendations": ["Action 1", "Action 2", "Action 3"],
    "urgency": "critical|high|medium|low",
    "context": {{
        "deployment": "{deployment_id}",
        "environment": "detected environment",
        "service": "detected service name"
    }}
}}

Focus on:
1. Error patterns and frequency
2. Critical failures vs warnings
3. System resource issues
4. Configuration problems
5. Actionable recommendations

Respond only with the JSON, no additional text.
"""
        prompt = prompt_template.format(deployment_id=deployment_id or 'Unknown', logs=logs)
        
        # Ensure the prompt does not exceed the token limit
        max_tokens = 2048
        while self.count_tokens(prompt) > max_tokens:
            logs = logs.rsplit('\n', 1)[0]  # Remove the last log entry
            prompt = prompt_template.format(deployment_id=deployment_id or 'Unknown', logs=logs)
        
        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse GPT4All response into structured format"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['summary', 'shortSummary', 'category', 'severity', 'errorType']
                for field in required_fields:
                    if field not in analysis:
                        analysis[field] = 'Unknown'
                
                return analysis
            else:
                # Fallback parsing if JSON extraction fails
                return self._parse_text_response(response)
                
        except json.JSONDecodeError:
            return self._parse_text_response(response)
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Fallback parser for non-JSON responses"""
        return {
            "summary": f"AI Analysis: {response[:200]}...",
            "shortSummary": "Log analysis completed with text response",
            "category": "application",
            "severity": "medium",
            "errorType": "AnalysisError",
            "rootCause": {
                "cause": "Response parsing issue",
                "description": "GPT4All provided text response instead of JSON",
                "confidence": "low"
            },
            "recommendations": [
                "Review raw AI response for insights",
                "Check log format and content",
                "Consider model retraining for structured output"
            ],
            "urgency": "low",
            "context": {
                "deployment": "unknown",
                "environment": "unknown",
                "service": "log-analyzer",
                "raw_response": response[:500]
            }
        }
    
    def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
        """Fallback analysis when AI fails"""
        # Basic pattern matching fallback
        error_patterns = {
            "error": "high",
            "failed": "high", 
            "exception": "medium",
            "warning": "low",
            "timeout": "high",
            "connection": "medium"
        }
        
        severity = "low"
        found_errors = []
        
        for log in logs[:10]:  # Check first 10 logs
            log_lower = log.lower()
            for pattern, sev in error_patterns.items():
                if pattern in log_lower:
                    found_errors.append(pattern)
                    if sev == "high":
                        severity = "high"
                    elif sev == "medium" and severity != "high":
                        severity = "medium"
        
        return {
            "summary": f"GPT4All analysis failed: {error}. Found patterns: {', '.join(found_errors)}",
            "shortSummary": "Offline AI analysis unavailable - using pattern matching",
            "category": "application",
            "severity": severity,
            "errorType": "AIAnalysisFailure",
            "rootCause": {
                "cause": "GPT4All processing error",
                "description": f"Local AI model encountered error: {error}",
                "confidence": "high"
            },
            "recommendations": [
                "Check GPT4All service status",
                "Verify model files are accessible",
                "Review system resources (RAM/CPU)",
                "Consider fallback to manual log review"
            ],
            "urgency": "medium",
            "context": {
                "deployment": "unknown",
                "environment": "local",
                "service": "gpt4all-analyzer",
                "error": error,
                "patterns_found": found_errors
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
#             with self.model.chat_session():
#                 response = self.model.generate(
#                     prompt, 
#                     max_tokens=1000,
#                     temp=0.1,
#                     top_p=0.9
#                 )
                
#             # Parse and structure the response
#             analysis = self._parse_analysis_response(response)
#             return analysis
            
#         except Exception as e:
#             return self._fallback_analysis(logs, str(e))
    
#     def _prepare_logs(self, logs: List[str], max_logs: int = 50) -> str:
#         """Prepare logs for analysis - limit size and clean"""
#         # Take sample of logs if too many
#         sample_logs = logs[:max_logs] if len(logs) > max_logs else logs
        
#         # Clean and format logs
#         cleaned_logs = []
#         for log in sample_logs:
#             # Remove excessive whitespace and limit length
#             clean_log = re.sub(r'\s+', ' ', log.strip())
#             if len(clean_log) > 200:
#                 clean_log = clean_log[:200] + "..."
#             cleaned_logs.append(clean_log)
        
#         return "\n".join(cleaned_logs)
    
#     def _create_analysis_prompt(self, logs: str, deployment_id: str) -> str:
#         """Create structured prompt for log analysis"""
#         return f"""
# You are an expert system administrator analyzing deployment logs. 
# Analyze the following logs and provide a structured JSON response with error analysis.

# Deployment ID: {deployment_id or 'Unknown'}

# Logs to analyze:
# {logs}

# Please provide analysis in this exact JSON format:
# {{
#     "summary": "Brief summary of main issues found",
#     "shortSummary": "One-line summary of the problem",
#     "category": "deployment|database|network|security|filesystem|memory|application",
#     "severity": "critical|high|medium|low",
#     "errorType": "Main error type identified",
#     "rootCause": {{
#         "cause": "Primary cause of the issue",
#         "description": "Detailed description of the root cause",
#         "confidence": "high|medium|low"
#     }},
#     "recommendations": ["Action 1", "Action 2", "Action 3"],
#     "urgency": "critical|high|medium|low",
#     "context": {{
#         "deployment": "{deployment_id or 'unknown'}",
#         "environment": "detected environment",
#         "service": "detected service name"
#     }}
# }}

# Focus on:
# 1. Error patterns and frequency
# 2. Critical failures vs warnings
# 3. System resource issues
# 4. Configuration problems
# 5. Actionable recommendations

# Respond only with the JSON, no additional text.
# """

#     def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
#         """Parse GPT4All response into structured format"""
#         try:
#             # Try to extract JSON from response
#             json_match = re.search(r'\{.*\}', response, re.DOTALL)
#             if json_match:
#                 json_str = json_match.group()
#                 analysis = json.loads(json_str)
                
#                 # Validate required fields
#                 required_fields = ['summary', 'shortSummary', 'category', 'severity', 'errorType']
#                 for field in required_fields:
#                     if field not in analysis:
#                         analysis[field] = 'Unknown'
                
#                 return analysis
#             else:
#                 # Fallback parsing if JSON extraction fails
#                 return self._parse_text_response(response)
                
#         except json.JSONDecodeError:
#             return self._parse_text_response(response)
    
#     def _parse_text_response(self, response: str) -> Dict[str, Any]:
#         """Fallback parser for non-JSON responses"""
#         return {
#             "summary": f"AI Analysis: {response[:200]}...",
#             "shortSummary": "Log analysis completed with text response",
#             "category": "application",
#             "severity": "medium",
#             "errorType": "AnalysisError",
#             "rootCause": {
#                 "cause": "Response parsing issue",
#                 "description": "GPT4All provided text response instead of JSON",
#                 "confidence": "low"
#             },
#             "recommendations": [
#                 "Review raw AI response for insights",
#                 "Check log format and content",
#                 "Consider model retraining for structured output"
#             ],
#             "urgency": "low",
#             "context": {
#                 "deployment": "unknown",
#                 "environment": "unknown",
#                 "service": "log-analyzer",
#                 "raw_response": response[:500]
#             }
#         }
    
#     def _fallback_analysis(self, logs: List[str], error: str) -> Dict[str, Any]:
#         """Fallback analysis when AI fails"""
#         # Basic pattern matching fallback
#         error_patterns = {
#             "error": "high",
#             "failed": "high", 
#             "exception": "medium",
#             "warning": "low",
#             "timeout": "high",
#             "connection": "medium"
#         }
        
#         severity = "low"
#         found_errors = []
        
#         for log in logs[:10]:  # Check first 10 logs
#             log_lower = log.lower()
#             for pattern, sev in error_patterns.items():
#                 if pattern in log_lower:
#                     found_errors.append(pattern)
#                     if sev == "high":
#                         severity = "high"
#                     elif sev == "medium" and severity != "high":
#                         severity = "medium"
        
#         return {
#             "summary": f"GPT4All analysis failed: {error}. Found patterns: {', '.join(found_errors)}",
#             "shortSummary": "Offline AI analysis unavailable - using pattern matching",
#             "category": "application",
#             "severity": severity,
#             "errorType": "AIAnalysisFailure",
#             "rootCause": {
#                 "cause": "GPT4All processing error",
#                 "description": f"Local AI model encountered error: {error}",
#                 "confidence": "high"
#             },
#             "recommendations": [
#                 "Check GPT4All service status",
#                 "Verify model files are accessible",
#                 "Review system resources (RAM/CPU)",
#                 "Consider fallback to manual log review"
#             ],
#             "urgency": "medium",
#             "context": {
#                 "deployment": "unknown",
#                 "environment": "local",
#                 "service": "gpt4all-analyzer",
#                 "error": error,
#                 "patterns_found": found_errors
#             }
#         }
