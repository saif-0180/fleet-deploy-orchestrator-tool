import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { AlertTriangle, Bug, Database, Network, Shield, HardDrive, Cpu, Code, Clock, User, Server, AlertCircle, CheckCircle, XCircle, Info, X, ChevronDown, ChevronUp } from 'lucide-react';

interface LogSummarizerProps {
  logs: string[];
  isOpen: boolean;
  onClose: () => void;
  deploymentId?: string;
}

interface ErrorAnalysis {
  summary: string;
  shortSummary: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  errorType: string;
  rootCause: {
    cause: string;
    description: string;
    confidence: 'high' | 'medium' | 'low';
  };
  recommendations: string[];
  urgency: 'critical' | 'high' | 'medium' | 'low';
  context: Record<string, string>;
  stackTrace?: {
    language: string;
    frames: Array<{
      className: string;
      method: string;
      location: string;
    }>;
  };
}

const LogSummarizer: React.FC<LogSummarizerProps> = ({ logs, isOpen, onClose, deploymentId }) => {
  const [activeTab, setActiveTab] = useState('summary');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [analysis, setAnalysis] = useState<ErrorAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Real API call to backend
  const analyzeErrors = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/logs/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: logs,
          deployment_id: deploymentId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success && data.analysis) {
        setAnalysis(data.analysis);
      } else {
        throw new Error(data.error || 'Failed to analyze logs');
      }
    } catch (err) {
      console.error('Error analyzing logs:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while analyzing logs');
      
      // Fallback to mock data if API fails
      const mockAnalysis: ErrorAnalysis = {
        summary: 'API Error - Using mock analysis',
        shortSummary: 'Mock Analysis (API Failed)',
        category: 'deployment',
        severity: 'high',
        errorType: 'DeploymentError',
        rootCause: {
          cause: 'Service configuration mismatch',
          description: 'Configuration files may be inconsistent across environments',
          confidence: 'high'
        },
        recommendations: [
          'Verify service configuration files are consistent',
          'Check environment-specific variables',
          'Review deployment pipeline for configuration drift',
          'Implement configuration validation in CI/CD'
        ],
        urgency: 'high',
        context: {
          deployment: deploymentId || 'unknown',
          environment: 'production',
          service: 'multiple'
        }
      };
      
      setAnalysis(mockAnalysis);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <XCircle className="w-4 h-4 text-red-400" />;
      case 'high': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'medium': return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case 'low': return <Info className="w-4 h-4 text-blue-400" />;
      default: return <Info className="w-4 h-4 text-gray-400" />;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'database': return <Database className="w-4 h-4 text-blue-400" />;
      case 'network': return <Network className="w-4 h-4 text-green-400" />;
      case 'deployment': return <Code className="w-4 h-4 text-purple-400" />;
      case 'security': return <Shield className="w-4 h-4 text-red-400" />;
      case 'filesystem': return <HardDrive className="w-4 h-4 text-yellow-400" />;
      case 'memory': return <Cpu className="w-4 h-4 text-orange-400" />;
      default: return <Bug className="w-4 h-4 text-gray-400" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-[#003459] rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <Collapsible open={!isCollapsed} onOpenChange={setIsCollapsed}>
          <div className="flex items-center justify-between p-4 bg-gradient-to-r from-[#00171f] to-[#003459] border-b border-[#00a7e1]/20">
            <div className="flex items-center gap-3">
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-[#EEEEEE] hover:bg-[#00a7e1]/20 p-1"
                >
                  {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                </Button>
              </CollapsibleTrigger>
              <AlertTriangle className="w-5 h-5 text-[#00a7e1]" />
              <h2 className="text-lg font-semibold text-[#EEEEEE]">Log Analysis & Summary</h2>
            </div>
            <Button
              onClick={onClose}
              variant="ghost"
              size="sm"
              className="text-[#EEEEEE] hover:bg-red-500/20 hover:text-red-400 p-1"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          <CollapsibleContent>
            <div className="p-4 max-h-[70vh] overflow-y-auto">
              {/* Error Message */}
              {error && (
                <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                  <p className="text-red-400 text-sm">
                    ⚠️ API Error: {error}
                  </p>
                  <p className="text-red-300 text-xs mt-1">
                    Showing fallback analysis data
                  </p>
                </div>
              )}

              {/* Analysis Button */}
              {!analysis && (
                <div className="text-center mb-6">
                  <Button
                    onClick={analyzeErrors}
                    disabled={loading}
                    className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 px-6 py-2"
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Analyzing Logs...
                      </>
                    ) : (
                      <>
                        <Bug className="w-4 h-4 mr-2" />
                        Summarize Logs
                      </>
                    )}
                  </Button>
                  <p className="text-[#BBBDBC] text-sm mt-2">
                    Analyzing {logs.length} log entries for patterns and issues
                  </p>
                </div>
              )}

              {/* Analysis Results */}
              {analysis && (
                <div className="space-y-6">
                  {/* Tab Navigation */}
                  <div className="flex space-x-1 mb-4">
                    {['summary', 'details', 'recommendations'].map((tab) => (
                      <Button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        variant={activeTab === tab ? "default" : "outline"}
                        size="sm"
                        className={activeTab === tab 
                          ? "bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80" 
                          : "bg-transparent border-[#00a7e1] text-[#00a7e1] hover:bg-[#00a7e1]/10"
                        }
                      >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </Button>
                    ))}
                  </div>

                  {/* Summary Tab */}
                  {activeTab === 'summary' && (
                    <div className="space-y-4">
                      <Card className="bg-[#00171f] border-[#00a7e1]/20">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
                            {getSeverityIcon(analysis.severity)}
                            Analysis Summary
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="flex items-start gap-3">
                            {getCategoryIcon(analysis.category)}
                            <div className="flex-1">
                              <h3 className="font-medium text-[#EEEEEE] mb-1">{analysis.shortSummary}</h3>
                              <p className="text-[#BBBDBC] text-sm">{analysis.summary}</p>
                            </div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              analysis.urgency === 'critical' ? 'bg-red-500/20 text-red-400' :
                              analysis.urgency === 'high' ? 'bg-orange-500/20 text-orange-400' :
                              analysis.urgency === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-blue-500/20 text-blue-400'
                            }`}>
                              {analysis.urgency} priority
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-[#003459] rounded-lg p-3">
                              <h4 className="font-medium text-[#EEEEEE] mb-2 flex items-center gap-1">
                                <AlertCircle className="w-4 h-4 text-[#00a7e1]" />
                                Error Type
                              </h4>
                              <p className="text-[#BBBDBC] text-sm">{analysis.errorType}</p>
                              <p className="text-[#BBBDBC] text-sm capitalize">Category: {analysis.category}</p>
                            </div>

                            <div className="bg-[#003459] rounded-lg p-3">
                              <h4 className="font-medium text-[#EEEEEE] mb-2 flex items-center gap-1">
                                <Server className="w-4 h-4 text-[#00a7e1]" />
                                Context
                              </h4>
                              {Object.entries(analysis.context).map(([key, value]) => (
                                <div key={key} className="flex justify-between text-sm">
                                  <span className="text-[#BBBDBC] capitalize">{key}:</span>
                                  <span className="text-[#EEEEEE] font-medium">{value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {/* Details Tab */}
                  {activeTab === 'details' && (
                    <div className="space-y-4">
                      <Card className="bg-[#00171f] border-[#00a7e1]/20">
                        <CardHeader>
                          <CardTitle className="text-[#EEEEEE]">Root Cause Analysis</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="bg-[#003459] rounded-lg p-4">
                            <h4 className="font-medium text-[#EEEEEE] mb-2">{analysis.rootCause.cause}</h4>
                            <p className="text-[#BBBDBC] text-sm mb-3">{analysis.rootCause.description}</p>
                            <span className={`inline-block px-2 py-1 rounded-full text-xs ${
                              analysis.rootCause.confidence === 'high' 
                                ? 'bg-green-500/20 text-green-400' 
                                : analysis.rootCause.confidence === 'medium'
                                ? 'bg-yellow-500/20 text-yellow-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}>
                              {analysis.rootCause.confidence} confidence
                            </span>
                          </div>

                          <div className="bg-[#003459] rounded-lg p-4">
                            <h4 className="font-medium text-[#EEEEEE] mb-3">Raw Log Sample</h4>
                            <div className="bg-[#00171f] rounded p-3 font-mono text-sm max-h-32 overflow-y-auto">
                              {logs.slice(0, 5).map((log, index) => (
                                <div key={index} className="text-[#BBBDBC] mb-1 break-all">
                                  {log.length > 100 ? log.substring(0, 100) + '...' : log}
                                </div>
                              ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {/* Recommendations Tab */}
                  {activeTab === 'recommendations' && (
                    <div className="space-y-4">
                      <Card className="bg-[#00171f] border-[#00a7e1]/20">
                        <CardHeader>
                          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-green-400" />
                            Recommended Actions
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            {analysis.recommendations.map((rec, index) => (
                              <div key={index} className="flex items-start gap-3 p-3 bg-[#003459] rounded-lg">
                                <div className="flex-shrink-0 w-6 h-6 bg-[#00a7e1]/20 rounded-full flex items-center justify-center text-[#00a7e1] text-sm font-medium">
                                  {index + 1}
                                </div>
                                <span className="text-[#EEEEEE] text-sm">{rec}</span>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
};

export default LogSummarizer;


// import React, { useState } from 'react';
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
// import { AlertTriangle, Bug, Database, Network, Shield, HardDrive, Cpu, Code, Clock, User, Server, AlertCircle, CheckCircle, XCircle, Info, X, ChevronDown, ChevronUp } from 'lucide-react';

// interface LogSummarizerProps {
//   logs: string[];
//   isOpen: boolean;
//   onClose: () => void;
//   deploymentId?: string;
// }

// interface ErrorAnalysis {
//   summary: string;
//   shortSummary: string;
//   category: string;
//   severity: 'critical' | 'high' | 'medium' | 'low';
//   errorType: string;
//   rootCause: {
//     cause: string;
//     description: string;
//     confidence: 'high' | 'medium' | 'low';
//   };
//   recommendations: string[];
//   urgency: 'critical' | 'high' | 'medium' | 'low';
//   context: Record<string, string>;
//   stackTrace?: {
//     language: string;
//     frames: Array<{
//       className: string;
//       method: string;
//       location: string;
//     }>;
//   };
// }

// const response = await fetch('/api/logs/summarize', {
//   method: 'POST',
//   headers: {
//     'Content-Type': 'application/json',
//   },
//   body: JSON.stringify({
//     logs: logs,
//     deployment_id: deploymentId
//   })
// });
// const data = await response.json();
// const LogSummarizer: React.FC<LogSummarizerProps> = ({ logs, isOpen, onClose, deploymentId }) => {
//   const [activeTab, setActiveTab] = useState('summary');
//   const [isCollapsed, setIsCollapsed] = useState(false);
//   const [analysis, setAnalysis] = useState<ErrorAnalysis | null>(null);
//   const [loading, setLoading] = useState(false);

//   // Mock analysis for demonstration - in real implementation, this would call the backend
//   const analyzeErrors = () => {
//     setLoading(true);
    
//     setTimeout(() => {
//       const mockAnalysis: ErrorAnalysis = {
//         summary: 'HIGH ConnectionError in PaymentService - Multiple deployment failures detected',
//         shortSummary: 'Deployment Error Analysis',
//         category: 'deployment',
//         severity: 'high',
//         errorType: 'DeploymentError',
//         rootCause: {
//           cause: 'Service configuration mismatch',
//           description: 'Configuration files may be inconsistent across environments',
//           confidence: 'high'
//         },
//         recommendations: [
//           'Verify service configuration files are consistent',
//           'Check environment-specific variables',
//           'Review deployment pipeline for configuration drift',
//           'Implement configuration validation in CI/CD'
//         ],
//         urgency: 'high',
//         context: {
//           deployment: deploymentId || 'unknown',
//           environment: 'production',
//           service: 'multiple'
//         }
//       };
      
//       setAnalysis(mockAnalysis);
//       setLoading(false);
//     }, 1500);
//   };

//   const getSeverityIcon = (severity: string) => {
//     switch (severity) {
//       case 'critical': return <XCircle className="w-4 h-4 text-red-400" />;
//       case 'high': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
//       case 'medium': return <AlertCircle className="w-4 h-4 text-yellow-400" />;
//       case 'low': return <Info className="w-4 h-4 text-blue-400" />;
//       default: return <Info className="w-4 h-4 text-gray-400" />;
//     }
//   };

//   const getCategoryIcon = (category: string) => {
//     switch (category) {
//       case 'database': return <Database className="w-4 h-4 text-blue-400" />;
//       case 'network': return <Network className="w-4 h-4 text-green-400" />;
//       case 'deployment': return <Code className="w-4 h-4 text-purple-400" />;
//       case 'security': return <Shield className="w-4 h-4 text-red-400" />;
//       case 'filesystem': return <HardDrive className="w-4 h-4 text-yellow-400" />;
//       case 'memory': return <Cpu className="w-4 h-4 text-orange-400" />;
//       default: return <Bug className="w-4 h-4 text-gray-400" />;
//     }
//   };

//   if (!isOpen) return null;

//   return (
//     <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
//       <div className="bg-[#003459] rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
//         <Collapsible open={!isCollapsed} onOpenChange={setIsCollapsed}>
//           <div className="flex items-center justify-between p-4 bg-gradient-to-r from-[#00171f] to-[#003459] border-b border-[#00a7e1]/20">
//             <div className="flex items-center gap-3">
//               <CollapsibleTrigger asChild>
//                 <Button
//                   variant="ghost"
//                   size="sm"
//                   className="text-[#EEEEEE] hover:bg-[#00a7e1]/20 p-1"
//                 >
//                   {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
//                 </Button>
//               </CollapsibleTrigger>
//               <AlertTriangle className="w-5 h-5 text-[#00a7e1]" />
//               <h2 className="text-lg font-semibold text-[#EEEEEE]">Log Analysis & Summary</h2>
//             </div>
//             <Button
//               onClick={onClose}
//               variant="ghost"
//               size="sm"
//               className="text-[#EEEEEE] hover:bg-red-500/20 hover:text-red-400 p-1"
//             >
//               <X className="w-4 h-4" />
//             </Button>
//           </div>

//           <CollapsibleContent>
//             <div className="p-4 max-h-[70vh] overflow-y-auto">
//               {/* Analysis Button */}
//               {!analysis && (
//                 <div className="text-center mb-6">
//                   <Button
//                     onClick={analyzeErrors}
//                     disabled={loading}
//                     className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 px-6 py-2"
//                   >
//                     {loading ? (
//                       <>
//                         <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
//                         Analyzing Logs...
//                       </>
//                     ) : (
//                       <>
//                         <Bug className="w-4 h-4 mr-2" />
//                         Summarize Logs
//                       </>
//                     )}
//                   </Button>
//                   <p className="text-[#BBBDBC] text-sm mt-2">
//                     Analyzing {logs.length} log entries for patterns and issues
//                   </p>
//                 </div>
//               )}

//               {/* Analysis Results */}
//               {analysis && (
//                 <div className="space-y-6">
//                   {/* Tab Navigation */}
//                   <div className="flex space-x-1 mb-4">
//                     {['summary', 'details', 'recommendations'].map((tab) => (
//                       <Button
//                         key={tab}
//                         onClick={() => setActiveTab(tab)}
//                         variant={activeTab === tab ? "default" : "outline"}
//                         size="sm"
//                         className={activeTab === tab 
//                           ? "bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80" 
//                           : "bg-transparent border-[#00a7e1] text-[#00a7e1] hover:bg-[#00a7e1]/10"
//                         }
//                       >
//                         {tab.charAt(0).toUpperCase() + tab.slice(1)}
//                       </Button>
//                     ))}
//                   </div>

//                   {/* Summary Tab */}
//                   {activeTab === 'summary' && (
//                     <div className="space-y-4">
//                       <Card className="bg-[#00171f] border-[#00a7e1]/20">
//                         <CardHeader className="pb-3">
//                           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//                             {getSeverityIcon(analysis.severity)}
//                             Analysis Summary
//                           </CardTitle>
//                         </CardHeader>
//                         <CardContent className="space-y-4">
//                           <div className="flex items-start gap-3">
//                             {getCategoryIcon(analysis.category)}
//                             <div className="flex-1">
//                               <h3 className="font-medium text-[#EEEEEE] mb-1">{analysis.shortSummary}</h3>
//                               <p className="text-[#BBBDBC] text-sm">{analysis.summary}</p>
//                             </div>
//                             <span className={`px-2 py-1 rounded-full text-xs font-medium ${
//                               analysis.urgency === 'critical' ? 'bg-red-500/20 text-red-400' :
//                               analysis.urgency === 'high' ? 'bg-orange-500/20 text-orange-400' :
//                               analysis.urgency === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
//                               'bg-blue-500/20 text-blue-400'
//                             }`}>
//                               {analysis.urgency} priority
//                             </span>
//                           </div>

//                           <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//                             <div className="bg-[#003459] rounded-lg p-3">
//                               <h4 className="font-medium text-[#EEEEEE] mb-2 flex items-center gap-1">
//                                 <AlertCircle className="w-4 h-4 text-[#00a7e1]" />
//                                 Error Type
//                               </h4>
//                               <p className="text-[#BBBDBC] text-sm">{analysis.errorType}</p>
//                               <p className="text-[#BBBDBC] text-sm capitalize">Category: {analysis.category}</p>
//                             </div>

//                             <div className="bg-[#003459] rounded-lg p-3">
//                               <h4 className="font-medium text-[#EEEEEE] mb-2 flex items-center gap-1">
//                                 <Server className="w-4 h-4 text-[#00a7e1]" />
//                                 Context
//                               </h4>
//                               {Object.entries(analysis.context).map(([key, value]) => (
//                                 <div key={key} className="flex justify-between text-sm">
//                                   <span className="text-[#BBBDBC] capitalize">{key}:</span>
//                                   <span className="text-[#EEEEEE] font-medium">{value}</span>
//                                 </div>
//                               ))}
//                             </div>
//                           </div>
//                         </CardContent>
//                       </Card>
//                     </div>
//                   )}

//                   {/* Details Tab */}
//                   {activeTab === 'details' && (
//                     <div className="space-y-4">
//                       <Card className="bg-[#00171f] border-[#00a7e1]/20">
//                         <CardHeader>
//                           <CardTitle className="text-[#EEEEEE]">Root Cause Analysis</CardTitle>
//                         </CardHeader>
//                         <CardContent className="space-y-4">
//                           <div className="bg-[#003459] rounded-lg p-4">
//                             <h4 className="font-medium text-[#EEEEEE] mb-2">{analysis.rootCause.cause}</h4>
//                             <p className="text-[#BBBDBC] text-sm mb-3">{analysis.rootCause.description}</p>
//                             <span className={`inline-block px-2 py-1 rounded-full text-xs ${
//                               analysis.rootCause.confidence === 'high' 
//                                 ? 'bg-green-500/20 text-green-400' 
//                                 : analysis.rootCause.confidence === 'medium'
//                                 ? 'bg-yellow-500/20 text-yellow-400'
//                                 : 'bg-red-500/20 text-red-400'
//                             }`}>
//                               {analysis.rootCause.confidence} confidence
//                             </span>
//                           </div>

//                           <div className="bg-[#003459] rounded-lg p-4">
//                             <h4 className="font-medium text-[#EEEEEE] mb-3">Raw Log Sample</h4>
//                             <div className="bg-[#00171f] rounded p-3 font-mono text-sm max-h-32 overflow-y-auto">
//                               {logs.slice(0, 5).map((log, index) => (
//                                 <div key={index} className="text-[#BBBDBC] mb-1 break-all">
//                                   {log.length > 100 ? log.substring(0, 100) + '...' : log}
//                                 </div>
//                               ))}
//                             </div>
//                           </div>
//                         </CardContent>
//                       </Card>
//                     </div>
//                   )}

//                   {/* Recommendations Tab */}
//                   {activeTab === 'recommendations' && (
//                     <div className="space-y-4">
//                       <Card className="bg-[#00171f] border-[#00a7e1]/20">
//                         <CardHeader>
//                           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//                             <CheckCircle className="w-5 h-5 text-green-400" />
//                             Recommended Actions
//                           </CardTitle>
//                         </CardHeader>
//                         <CardContent>
//                           <div className="space-y-3">
//                             {analysis.recommendations.map((rec, index) => (
//                               <div key={index} className="flex items-start gap-3 p-3 bg-[#003459] rounded-lg">
//                                 <div className="flex-shrink-0 w-6 h-6 bg-[#00a7e1]/20 rounded-full flex items-center justify-center text-[#00a7e1] text-sm font-medium">
//                                   {index + 1}
//                                 </div>
//                                 <span className="text-[#EEEEEE] text-sm">{rec}</span>
//                               </div>
//                             ))}
//                           </div>
//                         </CardContent>
//                       </Card>
//                     </div>
//                   )}
//                 </div>
//               )}
//             </div>
//           </CollapsibleContent>
//         </Collapsible>
//       </div>
//     </div>
//   );
// };

// export default LogSummarizer;
