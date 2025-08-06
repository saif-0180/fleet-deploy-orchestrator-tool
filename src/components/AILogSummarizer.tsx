
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Brain, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  X, 
  Sparkles,
  Clock,
  Activity,
  Target,
  Lightbulb
} from 'lucide-react';

interface AILogSummarizerProps {
  logs: string[];
  isOpen: boolean;
  onClose: () => void;
  deploymentId?: string;
}

interface AIAnalysis {
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
  keyEvents: string[];
  issuesFound: string[];
  recommendations: string[];
  urgency: 'critical' | 'high' | 'medium' | 'low';
  context: Record<string, string>;
  metadata?: {
    analysis_duration: string;
    log_lines_analyzed: number;
    total_log_lines: number;
    analysis_method: string;
    model_used: string;
  };
}

const AILogSummarizer: React.FC<AILogSummarizerProps> = ({ 
  logs, 
  isOpen, 
  onClose, 
  deploymentId 
}) => {
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && logs.length > 0) {
      analyzeWithAI();
    }
  }, [isOpen, logs]);

  const analyzeWithAI = async () => {
    setLoading(true);
    setError(null);
    setAnalysis(null);

    try {
      console.log('Starting AI log analysis...');
      
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
        throw new Error(`Analysis failed with status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success && data.analysis) {
        setAnalysis(data.analysis);
      } else {
        throw new Error(data.error || 'AI analysis failed');
      }

    } catch (err) {
      console.error('AI analysis error:', err);
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'high': return <AlertTriangle className="w-5 h-5 text-orange-500" />;
      case 'medium': return <Info className="w-5 h-5 text-yellow-500" />;
      case 'low': return <CheckCircle className="w-5 h-5 text-green-500" />;
      default: return <Activity className="w-5 h-5 text-blue-500" />;
    }
  };

  const getStatusColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'low': return 'bg-green-500/10 text-green-400 border-green-500/20';
      default: return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#003459] rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden border border-[#00a7e1]/20">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 bg-gradient-to-r from-[#00171f] to-[#003459] border-b border-[#00a7e1]/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#00a7e1]/20 rounded-lg">
              <Brain className="w-6 h-6 text-[#00a7e1]" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[#EEEEEE]">AI Log Analysis</h2>
              <p className="text-sm text-[#BBBDBC]">Intelligent deployment analysis powered by AI</p>
            </div>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            className="text-[#EEEEEE] hover:bg-red-500/20 hover:text-red-400"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        <ScrollArea className="max-h-[calc(90vh-100px)]">
          <div className="p-6">
            
            {/* Loading State */}
            {loading && (
              <div className="text-center py-12">
                <div className="inline-flex items-center gap-3 text-[#00a7e1]">
                  <Sparkles className="w-6 h-6 animate-spin" />
                  <span className="text-lg">AI is analyzing your logs...</span>
                </div>
                <p className="text-sm text-[#BBBDBC] mt-2">
                  Processing {logs.length} log entries
                </p>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="mb-6">
                <Card className="bg-red-500/10 border-red-500/20">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <XCircle className="w-5 h-5 text-red-400" />
                      <div>
                        <p className="text-red-400 font-medium">Analysis Failed</p>
                        <p className="text-red-300 text-sm mt-1">{error}</p>
                      </div>
                    </div>
                    <Button 
                      onClick={analyzeWithAI}
                      variant="outline"
                      size="sm"
                      className="mt-3 border-red-500/30 text-red-400 hover:bg-red-500/10"
                    >
                      Retry Analysis
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Analysis Results */}
            {analysis && (
              <div className="space-y-6">
                
                {/* Status Overview */}
                <Card className="bg-[#00171f] border-[#00a7e1]/20">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(analysis.severity)}
                        <div>
                          <h3 className="text-lg font-semibold text-[#EEEEEE]">
                            {analysis.shortSummary}
                          </h3>
                          <p className="text-[#BBBDBC] mt-1">{analysis.summary}</p>
                        </div>
                      </div>
                      <Badge className={getStatusColor(analysis.severity)}>
                        {analysis.severity} priority
                      </Badge>
                    </div>

                    {analysis.metadata && (
                      <div className="flex items-center gap-6 text-sm text-[#BBBDBC] bg-[#003459] rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          <span>Analysis: {analysis.metadata.analysis_duration}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Activity className="w-4 h-4" />
                          <span>{analysis.metadata.log_lines_analyzed} lines analyzed</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Brain className="w-4 h-4" />
                          <span>{analysis.metadata.analysis_method}</span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Key Events & Issues */}
                {(analysis.keyEvents?.length > 0 || analysis.issuesFound?.length > 0) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    
                    {/* Key Events */}
                    {analysis.keyEvents?.length > 0 && (
                      <Card className="bg-[#00171f] border-[#00a7e1]/20">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
                            <Target className="w-5 h-5 text-[#00a7e1]" />
                            Key Events
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {analysis.keyEvents.map((event, index) => (
                              <div key={index} className="flex items-start gap-3 p-3 bg-[#003459] rounded-lg">
                                <div className="w-2 h-2 bg-[#00a7e1] rounded-full mt-2 flex-shrink-0" />
                                <span className="text-[#EEEEEE] text-sm">{event}</span>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Issues Found */}
                    {analysis.issuesFound?.length > 0 && (
                      <Card className="bg-[#00171f] border-[#00a7e1]/20">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5 text-orange-400" />
                            Issues Found
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {analysis.issuesFound.map((issue, index) => (
                              <div key={index} className="flex items-start gap-3 p-3 bg-orange-500/10 rounded-lg border border-orange-500/20">
                                <AlertTriangle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                                <span className="text-orange-200 text-sm">{issue}</span>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                )}

                {/* Recommendations */}
                <Card className="bg-[#00171f] border-[#00a7e1]/20">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-green-400" />
                      AI Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {analysis.recommendations.map((rec, index) => (
                        <div key={index} className="flex items-start gap-3 p-4 bg-[#003459] rounded-lg">
                          <div className="flex-shrink-0 w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm font-medium">
                            {index + 1}
                          </div>
                          <span className="text-[#EEEEEE] text-sm leading-relaxed">{rec}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Root Cause Analysis */}
                <Card className="bg-[#00171f] border-[#00a7e1]/20">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-[#EEEEEE]">Root Cause Analysis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="p-4 bg-[#003459] rounded-lg">
                        <h4 className="font-medium text-[#EEEEEE] mb-2">{analysis.rootCause.cause}</h4>
                        <p className="text-[#BBBDBC] text-sm mb-3">{analysis.rootCause.description}</p>
                        <Badge className={`${
                          analysis.rootCause.confidence === 'high' 
                            ? 'bg-green-500/20 text-green-400 border-green-500/30' 
                            : analysis.rootCause.confidence === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                            : 'bg-red-500/20 text-red-400 border-red-500/30'
                        }`}>
                          {analysis.rootCause.confidence} confidence
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

              </div>
            )}

          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default AILogSummarizer;
