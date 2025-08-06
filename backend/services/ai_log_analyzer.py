
import json
import time
from typing import Dict, List, Any
from gpt4all import GPT4All
from backend.config.gpt4all_config import GPT4ALL_CONFIG

class AILogAnalyzer:
    def __init__(self, model_name=None, model_path=None):
        self.model_path = model_path or GPT4ALL_CONFIG['model_path']
        self.model_name = model_name or GPT4ALL_CONFIG['model_name']
        
        # Initialize model immediately for faster subsequent calls
        self.model = None
        self.model_initialized = False
        
        print(f"AI Log Analyzer initialized with model: {self.model_name}")
    
    def _init_model(self):
        """Initialize the model only when needed"""
        if not self.model_initialized:
            print("Loading AI model for log analysis...")
            start_time = time.time()
            self.model = GPT4All(self.model_name, model_path=self.model_path)
            self.model_initialized = True
            load_time = time.time() - start_time
            print(f"Model loaded in {load_time:.2f} seconds")
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """AI-powered log analysis with intelligent summarization"""
        
        start_time = time.time()
        
        # Take recent logs for analysis (last 50 lines for speed)
        recent_logs = logs[-50:] if len(logs) > 50 else logs
        log_content = "\n".join(recent_logs)
        
        print(f"Analyzing {len(recent_logs)} log entries with AI...")
        
        try:
            self._init_model()
            analysis_result = self._generate_ai_analysis(log_content, deployment_id)
            
            elapsed = time.time() - start_time
            print(f"AI analysis completed in {elapsed:.2f} seconds")
            
            analysis_result["metadata"] = {
                "analysis_duration": f"{elapsed:.2f}s",
                "log_lines_analyzed": len(recent_logs),
                "total_log_lines": len(logs),
                "analysis_method": "AI-powered",
                "model_used": self.model_name
            }
            
            return analysis_result
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return self._create_fallback_analysis(log_content, deployment_id, str(e))
    
    def _generate_ai_analysis(self, log_content: str, deployment_id: str) -> Dict[str, Any]:
        """Generate comprehensive AI analysis of logs"""
        
        # Create focused prompt for deployment log analysis
        prompt = f"""You are an expert DevOps engineer analyzing deployment logs. Analyze the following logs and provide a structured response.

LOGS:
{log_content[:3000]}

Provide analysis in this EXACT JSON format:
{{
    "status": "SUCCESS|FAILURE|WARNING|UNCLEAR",
    "deployment_type": "ansible|systemctl|application|database|network|general",
    "summary": "Clear one-sentence summary of what happened",
    "detailed_explanation": "2-3 sentence detailed explanation",
    "key_events": ["event1", "event2", "event3"],
    "issues_found": ["issue1", "issue2"] or [],
    "recommendations": ["rec1", "rec2", "rec3"],
    "confidence": "high|medium|low",
    "severity": "critical|high|medium|low"
}}

Respond ONLY with valid JSON, no other text."""

        try:
            print("Generating AI analysis...")
            
            response = self.model.generate(
                prompt=prompt,
                max_tokens=400,
                temp=0.2,
                top_p=0.9
            )
            
            print(f"AI response length: {len(response)} chars")
            
            # Parse JSON response
            return self._parse_ai_json_response(response, deployment_id)
            
        except Exception as e:
            print(f"AI generation failed: {e}")
            raise e
    
    def _parse_ai_json_response(self, response: str, deployment_id: str) -> Dict[str, Any]:
        """Parse AI JSON response and convert to standard format"""
        
        try:
            # Clean up response and extract JSON
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '')
            
            # Find JSON block
            start_idx = clean_response.find('{')
            end_idx = clean_response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = clean_response[start_idx:end_idx]
                ai_data = json.loads(json_str)
                
                # Convert AI response to our standard format
                return {
                    "summary": ai_data.get("detailed_explanation", ai_data.get("summary", "Analysis completed")),
                    "shortSummary": f"{ai_data.get('deployment_type', 'Deployment').title()} - {ai_data.get('status', 'Unknown').title()}",
                    "category": self._map_deployment_type(ai_data.get("deployment_type", "general")),
                    "severity": ai_data.get("severity", "medium"),
                    "errorType": self._determine_error_type(ai_data.get("status", "UNCLEAR")),
                    "rootCause": {
                        "cause": ai_data.get("summary", "Analysis completed"),
                        "description": ai_data.get("detailed_explanation", "AI analysis of deployment logs"),
                        "confidence": ai_data.get("confidence", "medium")
                    },
                    "keyEvents": ai_data.get("key_events", []),
                    "issuesFound": ai_data.get("issues_found", []),
                    "recommendations": ai_data.get("recommendations", ["Review logs for more details"]),
                    "urgency": self._map_severity_to_urgency(ai_data.get("severity", "medium")),
                    "context": {
                        "deployment": deployment_id or "unknown",
                        "status": ai_data.get("status", "unknown").lower(),
                        "deployment_type": ai_data.get("deployment_type", "general"),
                        "confidence": ai_data.get("confidence", "medium")
                    }
                }
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"Failed to parse AI JSON response: {e}")
            print(f"Raw response: {response[:200]}...")
            
            # Fallback to text parsing
            return self._parse_ai_text_fallback(response, deployment_id)
    
    def _parse_ai_text_fallback(self, response: str, deployment_id: str) -> Dict[str, Any]:
        """Fallback text parsing when JSON parsing fails"""
        
        # Extract key information from text response
        status = "UNCLEAR"
        if any(word in response.upper() for word in ["SUCCESS", "SUCCESSFUL", "COMPLETED"]):
            status = "SUCCESS"
        elif any(word in response.upper() for word in ["FAILED", "FAILURE", "ERROR"]):
            status = "FAILURE"
        elif any(word in response.upper() for word in ["WARNING", "WARN"]):
            status = "WARNING"
        
        deployment_type = "general"
        if "ansible" in response.lower():
            deployment_type = "ansible"
        elif "systemctl" in response.lower() or "service" in response.lower():
            deployment_type = "systemctl"
        elif "database" in response.lower() or "sql" in response.lower():
            deployment_type = "database"
        
        # Extract first sentence as summary
        sentences = response.split('.')
        summary = sentences[0].strip() if sentences else "Analysis completed"
        
        return {
            "summary": summary,
            "shortSummary": f"{deployment_type.title()} - {status.title()}",
            "category": self._map_deployment_type(deployment_type),
            "severity": "medium" if status == "WARNING" else ("low" if status == "SUCCESS" else "high"),
            "errorType": self._determine_error_type(status),
            "rootCause": {
                "cause": summary,
                "description": response[:200] + "..." if len(response) > 200 else response,
                "confidence": "low"
            },
            "keyEvents": [],
            "issuesFound": [],
            "recommendations": ["Review complete analysis", "Check system status"],
            "urgency": "medium",
            "context": {
                "deployment": deployment_id or "unknown",
                "status": status.lower(),
                "deployment_type": deployment_type,
                "confidence": "low",
                "note": "Parsed from text fallback"
            }
        }
    
    def _map_deployment_type(self, deployment_type: str) -> str:
        """Map deployment type to category"""
        mapping = {
            'ansible': 'deployment',
            'systemctl': 'system',
            'application': 'application',
            'database': 'database',
            'network': 'network',
            'general': 'system'
        }
        return mapping.get(deployment_type.lower(), 'system')
    
    def _determine_error_type(self, status: str) -> str:
        """Determine error type from status"""
        if status.upper() == "SUCCESS":
            return "Success"
        elif status.upper() == "FAILURE":
            return "DeploymentError"
        elif status.upper() == "WARNING":
            return "Warning"
        else:
            return "UnknownStatus"
    
    def _map_severity_to_urgency(self, severity: str) -> str:
        """Map severity to urgency"""
        mapping = {
            'critical': 'critical',
            'high': 'high', 
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(severity.lower(), 'medium')
    
    def _create_fallback_analysis(self, log_content: str, deployment_id: str, error: str) -> Dict[str, Any]:
        """Create fallback analysis when AI fails"""
        
        return {
            "summary": f"AI analysis failed: {error}. Showing basic analysis.",
            "shortSummary": "AI Analysis Failed",
            "category": "system",
            "severity": "medium",
            "errorType": "AnalysisError",
            "rootCause": {
                "cause": "AI model analysis failure",
                "description": f"The AI model failed to analyze the logs: {error}",
                "confidence": "high"
            },
            "keyEvents": [],
            "issuesFound": [f"AI analysis error: {error}"],
            "recommendations": [
                "Check AI model availability",
                "Review logs manually",
                "Verify system resources"
            ],
            "urgency": "medium",
            "context": {
                "deployment": deployment_id or "unknown",
                "status": "analysis_failed",
                "deployment_type": "unknown",
                "confidence": "high",
                "error": error
            },
            "metadata": {
                "analysis_method": "fallback",
                "error": error
            }
        }
