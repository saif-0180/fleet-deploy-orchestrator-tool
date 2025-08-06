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
        
        # Compile all regex patterns for performance
        self._compile_comprehensive_patterns()
        
    def _compile_comprehensive_patterns(self):
        """Compile comprehensive regex patterns for accurate detection"""
        
        # SUCCESS PATTERNS - Very specific and comprehensive
        self.success_patterns = [
            # Direct success statements
            re.compile(r'successfully\s+completed', re.IGNORECASE),
            re.compile(r'completed\s+successfully', re.IGNORECASE),
            re.compile(r'operation\s+successful', re.IGNORECASE),
            re.compile(r'task\s+completed\s+successfully', re.IGNORECASE),
            re.compile(r'deployment\s+successful', re.IGNORECASE),
            
            # Systemctl specific success
            re.compile(r'systemctl.*started.*successfully', re.IGNORECASE),
            re.compile(r'systemctl.*enabled.*successfully', re.IGNORECASE),
            re.compile(r'systemctl.*restarted.*successfully', re.IGNORECASE),
            re.compile(r'service.*started.*successfully', re.IGNORECASE),
            re.compile(r'unit.*started.*successfully', re.IGNORECASE),
            
            # Status indicators
            re.compile(r'status:\s*(success|ok|completed)', re.IGNORECASE),
            re.compile(r'result:\s*(success|ok|completed)', re.IGNORECASE),
            re.compile(r'state:\s*(running|active|started)', re.IGNORECASE),
            
            # Validation and verification success
            re.compile(r'validation\s+passed', re.IGNORECASE),
            re.compile(r'checksum\s+verified', re.IGNORECASE),
            re.compile(r'integrity\s+check\s+passed', re.IGNORECASE),
            re.compile(r'all\s+tests\s+passed', re.IGNORECASE),
            
            # Ansible specific success
            re.compile(r'play\s+recap.*failed=0', re.IGNORECASE),
            re.compile(r'ok=\d+.*changed=\d+.*unreachable=0.*failed=0', re.IGNORECASE),
            
            # Generic positive completions
            re.compile(r'backup\s+completed', re.IGNORECASE),
            re.compile(r'rollback\s+completed', re.IGNORECASE),
            re.compile(r'installation\s+completed', re.IGNORECASE),
            re.compile(r'configuration\s+applied', re.IGNORECASE),
        ]
        
        # STRONG FAILURE PATTERNS - Clear failures only
        self.failure_patterns = [
            # Service failures
            re.compile(r'failed\s+to\s+start', re.IGNORECASE),
            re.compile(r'service\s+failed', re.IGNORECASE),
            re.compile(r'systemctl.*failed', re.IGNORECASE),
            re.compile(r'unit\s+failed', re.IGNORECASE),
            
            # Connection failures
            re.compile(r'connection\s+refused', re.IGNORECASE),
            re.compile(r'connection\s+failed', re.IGNORECASE),
            re.compile(r'connection\s+timeout', re.IGNORECASE),
            re.compile(r'network\s+unreachable', re.IGNORECASE),
            
            # File system failures
            re.compile(r'no\s+such\s+file\s+or\s+directory', re.IGNORECASE),
            re.compile(r'permission\s+denied', re.IGNORECASE),
            re.compile(r'access\s+denied', re.IGNORECASE),
            re.compile(r'file\s+not\s+found', re.IGNORECASE),
            
            # Process failures
            re.compile(r'command\s+not\s+found', re.IGNORECASE),
            re.compile(r'execution\s+failed', re.IGNORECASE),
            re.compile(r'process\s+failed', re.IGNORECASE),
            re.compile(r'fatal\s+error', re.IGNORECASE),
            
            # Ansible failures
            re.compile(r'failed=[1-9]\d*', re.IGNORECASE),
            re.compile(r'unreachable=[1-9]\d*', re.IGNORECASE),
            re.compile(r'task\s+failed', re.IGNORECASE),
            
            # Generic serious errors
            re.compile(r'critical\s+error', re.IGNORECASE),
            re.compile(r'exception.*occurred', re.IGNORECASE),
            re.compile(r'stack\s+trace', re.IGNORECASE),
        ]
        
        # WARNING PATTERNS - Not failures but concerns
        self.warning_patterns = [
            re.compile(r'warning(?!.*critical)', re.IGNORECASE),
            re.compile(r'deprecated', re.IGNORECASE),
            re.compile(r'skipping', re.IGNORECASE),
            re.compile(r'retrying', re.IGNORECASE),
        ]
        
        # INFORMATIONAL PATTERNS - Should not count as failures
        self.info_patterns = [
            re.compile(r'info:', re.IGNORECASE),
            re.compile(r'debug:', re.IGNORECASE),
            re.compile(r'notice:', re.IGNORECASE),
            re.compile(r'log\s+level', re.IGNORECASE),
            re.compile(r'starting.*process', re.IGNORECASE),
            re.compile(r'loading.*configuration', re.IGNORECASE),
        ]
        
        # COMPLETION INDICATORS - Suggest operation finished
        self.completion_patterns = [
            re.compile(r'finished', re.IGNORECASE),
            re.compile(r'completed', re.IGNORECASE),
            re.compile(r'done', re.IGNORECASE),
            re.compile(r'ended', re.IGNORECASE),
        ]
    
    def analyze_logs(self, logs: List[str], deployment_id: str = None) -> Dict[str, Any]:
        """Fast pattern-based log analysis with minimal AI usage"""
        
        start_time = time.time()
        
        # Combine logs for better context
        full_log_text = "\n".join(logs)
        
        print(f"Analyzing {len(logs)} log lines...")
        
        # Enhanced pattern-based analysis
        analysis_result = self._comprehensive_pattern_analysis(full_log_text, deployment_id)
        
        elapsed = time.time() - start_time
        print(f"Pattern analysis completed in {elapsed:.2f} seconds")
        
        # Add analysis metadata
        analysis_result["context"]["analysis_duration"] = f"{elapsed:.2f}s"
        analysis_result["context"]["analysis_method"] = "pattern_based"
        analysis_result["context"]["log_lines_analyzed"] = len(logs)
        
        return analysis_result
    
    def _comprehensive_pattern_analysis(self, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Comprehensive pattern-based analysis"""
        
        # Count different types of patterns
        success_matches = []
        failure_matches = []
        warning_matches = []
        info_matches = []
        completion_matches = []
        
        # Find all pattern matches with context
        for pattern in self.success_patterns:
            matches = pattern.finditer(log_text)
            for match in matches:
                success_matches.append({
                    'pattern': pattern.pattern,
                    'match': match.group(),
                    'context': self._extract_context(log_text, match.start(), match.end())
                })
        
        for pattern in self.failure_patterns:
            matches = pattern.finditer(log_text)
            for match in matches:
                failure_matches.append({
                    'pattern': pattern.pattern,
                    'match': match.group(),
                    'context': self._extract_context(log_text, match.start(), match.end())
                })
        
        for pattern in self.warning_patterns:
            matches = pattern.finditer(log_text)
            warning_matches.extend([match.group() for match in matches])
        
        for pattern in self.info_patterns:
            matches = pattern.finditer(log_text)
            info_matches.extend([match.group() for match in matches])
        
        for pattern in self.completion_patterns:
            matches = pattern.finditer(log_text)
            completion_matches.extend([match.group() for match in matches])
        
        # Debug output
        print(f"Pattern matches - Success: {len(success_matches)}, Failures: {len(failure_matches)}, Warnings: {len(warning_matches)}")
        
        # Determine overall result
        return self._determine_final_result(
            log_text, success_matches, failure_matches, warning_matches, 
            completion_matches, deployment_id
        )
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 100) -> str:
        """Extract context around a match"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        return text[context_start:context_end].strip()
    
    def _determine_final_result(self, log_text: str, success_matches: List[Dict], 
                               failure_matches: List[Dict], warning_matches: List[str],
                               completion_matches: List[str], deployment_id: str) -> Dict[str, Any]:
        """Determine final analysis result with improved logic"""
        
        success_count = len(success_matches)
        failure_count = len(failure_matches)
        warning_count = len(warning_matches)
        completion_count = len(completion_matches)
        
        log_lower = log_text.lower()
        
        print(f"Analysis scores - Success: {success_count}, Failure: {failure_count}, Warnings: {warning_count}, Completions: {completion_count}")
        
        # RULE 1: Strong success indicators override everything
        if success_count > 0:
            # Check if there are any real failures that contradict success
            real_failures = [f for f in failure_matches if not self._is_false_positive_failure(f, log_text)]
            
            if len(real_failures) == 0 or success_count > len(real_failures):
                print(f"SUCCESS: {success_count} success patterns, {len(real_failures)} real failures")
                return self._create_success_result(success_matches, log_text, deployment_id)
        
        # RULE 2: Clear failures with no success indicators
        if failure_count > 0 and success_count == 0:
            print(f"FAILURE: {failure_count} failure patterns, no success patterns")
            return self._create_failure_result(failure_matches, log_text, deployment_id)
        
        # RULE 3: Mixed signals - analyze context
        if success_count > 0 and failure_count > 0:
            # Check if failures are actually informational
            real_failures = [f for f in failure_matches if not self._is_false_positive_failure(f, log_text)]
            
            if len(real_failures) == 0:
                print(f"SUCCESS: Success patterns present, failures are false positives")
                return self._create_success_result(success_matches, log_text, deployment_id)
            elif success_count >= len(real_failures):
                print(f"SUCCESS: More success indicators ({success_count}) than real failures ({len(real_failures)})")
                return self._create_success_result(success_matches, log_text, deployment_id)
            else:
                print(f"FAILURE: More real failures ({len(real_failures)}) than success indicators ({success_count})")
                return self._create_failure_result(real_failures, log_text, deployment_id)
        
        # RULE 4: No clear success/failure patterns - check completion
        if success_count == 0 and failure_count == 0:
            if completion_count > 0 and warning_count == 0:
                print(f"SUCCESS: Operation completed without errors")
                return self._create_neutral_success_result(log_text, deployment_id)
            elif warning_count > 0:
                print(f"WARNING: Operation completed with warnings")
                return self._create_warning_result(warning_matches, log_text, deployment_id)
            else:
                print(f"UNCLEAR: No clear indicators")
                return self._create_unclear_result(log_text, deployment_id)
        
        # Default fallback
        print(f"DEFAULT: Defaulting to unclear status")
        return self._create_unclear_result(log_text, deployment_id)
    
    def _is_false_positive_failure(self, failure_match: Dict, log_text: str) -> bool:
        """Check if a failure match is actually a false positive"""
        context = failure_match['context'].lower()
        match_text = failure_match['match'].lower()
        
        # Check if the failure is mentioned in a success context
        false_positive_contexts = [
            'successfully',
            'completed',
            'recovered',
            'fixed',
            'resolved',
            'handled',
            'ignored',
            'skipped'
        ]
        
        return any(fp_context in context for fp_context in false_positive_contexts)
    
    def _create_success_result(self, success_matches: List[Dict], log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create success analysis result"""
        
        # Determine operation type from success matches
        operation_type = "operation"
        if any('systemctl' in match['match'].lower() for match in success_matches):
            operation_type = "service_management"
        elif any('deployment' in match['match'].lower() for match in success_matches):
            operation_type = "deployment"
        elif any('backup' in match['match'].lower() for match in success_matches):
            operation_type = "backup"
        elif any('validation' in match['match'].lower() for match in success_matches):
            operation_type = "validation"
        
        # Extract specific success details
        success_details = []
        for match in success_matches[:3]:  # Top 3 success indicators
            success_details.append(match['match'])
        
        return {
            "summary": f"{operation_type.replace('_', ' ').title()} completed successfully. Key indicators: {', '.join(success_details)}",
            "shortSummary": f"Successful {operation_type.replace('_', ' ')}",
            "category": self._determine_category(operation_type, log_text),
            "severity": "low",
            "errorType": "Success",
            "rootCause": {
                "cause": f"Successful {operation_type}",
                "description": f"Operation completed successfully with {len(success_matches)} positive indicators",
                "confidence": "high"
            },
            "recommendations": [
                "No action required - operation successful",
                "Monitor system for expected changes",
                "Document successful configuration"
            ],
            "urgency": "low",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": operation_type,
                "success_indicators": len(success_matches),
                "operation_type": operation_type
            }
        }
    
    def _create_failure_result(self, failure_matches: List[Dict], log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create failure analysis result"""
        
        # Determine primary failure type
        failure_types = []
        for match in failure_matches:
            match_lower = match['match'].lower()
            if 'service' in match_lower or 'systemctl' in match_lower:
                failure_types.append("service_failure")
            elif 'connection' in match_lower or 'network' in match_lower:
                failure_types.append("network_failure")
            elif 'file' in match_lower or 'permission' in match_lower:
                failure_types.append("filesystem_failure")
            elif 'command' in match_lower or 'execution' in match_lower:
                failure_types.append("execution_failure")
            else:
                failure_types.append("general_failure")
        
        primary_failure = max(set(failure_types), key=failure_types.count) if failure_types else "general_failure"
        
        # Generate specific recommendations based on failure type
        recommendations = self._get_failure_recommendations(primary_failure, failure_matches)
        
        # Extract key failure details
        failure_details = []
        for match in failure_matches[:3]:  # Top 3 failure indicators
            failure_details.append(match['match'])
        
        return {
            "summary": f"{primary_failure.replace('_', ' ').title()} detected. Key issues: {', '.join(failure_details)}",
            "shortSummary": f"{primary_failure.replace('_', ' ').title()}",
            "category": self._map_failure_to_category(primary_failure),
            "severity": "high",
            "errorType": primary_failure.replace('_', '').title(),
            "rootCause": {
                "cause": primary_failure.replace('_', ' '),
                "description": f"Multiple failure indicators detected: {len(failure_matches)} issues found",
                "confidence": "high"
            },
            "recommendations": recommendations,
            "urgency": "high",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production", 
                "service": primary_failure,
                "failure_count": len(failure_matches),
                "primary_failure_type": primary_failure
            }
        }
    
    def _create_neutral_success_result(self, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create result for operations that completed without clear success/failure indicators"""
        return {
            "summary": "Operation completed without errors detected",
            "shortSummary": "Operation completed",
            "category": "application",
            "severity": "low",
            "errorType": "Completed",
            "rootCause": {
                "cause": "Normal completion",
                "description": "Operation finished without explicit errors",
                "confidence": "medium"
            },
            "recommendations": [
                "Verify expected results manually",
                "Check if all intended changes were applied"
            ],
            "urgency": "low",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": "general",
                "status": "completed_without_errors"
            }
        }
    
    def _create_warning_result(self, warning_matches: List[str], log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create result for operations with warnings"""
        return {
            "summary": f"Operation completed with {len(warning_matches)} warnings that should be reviewed",
            "shortSummary": f"Completed with {len(warning_matches)} warnings",
            "category": "application",
            "severity": "medium",
            "errorType": "CompletedWithWarnings",
            "rootCause": {
                "cause": "Operation completed with warnings",
                "description": f"Found {len(warning_matches)} warning indicators",
                "confidence": "medium"
            },
            "recommendations": [
                "Review warnings to ensure they don't indicate future issues",
                "Consider addressing deprecated features",
                "Monitor system for any impact from warnings"
            ],
            "urgency": "medium",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": "general",
                "warning_count": len(warning_matches)
            }
        }
    
    def _create_unclear_result(self, log_text: str, deployment_id: str) -> Dict[str, Any]:
        """Create result when analysis is unclear"""
        return {
            "summary": "Log analysis inconclusive - manual review recommended to determine operation status",
            "shortSummary": "Status unclear - review needed",
            "category": "application",
            "severity": "medium",
            "errorType": "UnclearStatus",
            "rootCause": {
                "cause": "Insufficient clear indicators",
                "description": "No definitive success or failure patterns detected",
                "confidence": "low"
            },
            "recommendations": [
                "Manually review complete logs for operation status",
                "Verify if intended operation completed successfully",
                "Check system state to confirm operation results"
            ],
            "urgency": "medium",
            "context": {
                "deployment": deployment_id or "unknown",
                "environment": "production",
                "service": "analysis",
                "status": "unclear"
            }
        }
    
    def _determine_category(self, operation_type: str, log_text: str) -> str:
        """Determine category based on operation type and log content"""
        if operation_type == "service_management":
            return "system"
        elif operation_type == "deployment":
            return "deployment"
        elif operation_type == "backup":
            return "maintenance"
        elif operation_type == "validation":
            return "verification"
        elif "database" in log_text.lower():
            return "database"
        elif "network" in log_text.lower():
            return "network"
        else:
            return "application"
    
    def _map_failure_to_category(self, failure_type: str) -> str:
        """Map failure type to category"""
        mapping = {
            "service_failure": "system",
            "network_failure": "network",
            "filesystem_failure": "filesystem",
            "execution_failure": "application",
            "general_failure": "application"
        }
        return mapping.get(failure_type, "application")
    
    def _get_failure_recommendations(self, failure_type: str, failure_matches: List[Dict]) -> List[str]:
        """Get specific recommendations based on failure type"""
        
        base_recommendations = {
            "service_failure": [
                "Check service status: systemctl status <service>",
                "Review service logs: journalctl -u <service>",
                "Verify service configuration files",
                "Check for dependency issues"
            ],
            "network_failure": [
                "Test network connectivity: ping <target>",
                "Check firewall rules and port access",
                "Verify DNS resolution",
                "Check network interface status"
            ],
            "filesystem_failure": [
                "Verify file and directory permissions",
                "Check if files/directories exist",
                "Confirm available disk space",
                "Review file ownership settings"
            ],
            "execution_failure": [
                "Check command syntax and parameters",
                "Verify executable permissions",
                "Check PATH environment variable",
                "Review execution environment"
            ],
            "general_failure": [
                "Review complete error logs",
                "Check system resource availability",
                "Verify configuration settings",
                "Consider restarting affected services"
            ]
        }
        
        return base_recommendations.get(failure_type, base_recommendations["general_failure"])