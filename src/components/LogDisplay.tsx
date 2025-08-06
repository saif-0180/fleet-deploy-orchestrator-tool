
import React, { useState } from 'react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Brain, Download, Trash2 } from 'lucide-react';
import AILogSummarizer from './AILogSummarizer';

interface LogDisplayProps {
  logs: string[];
  isLoading: boolean;
  deploymentId?: string;
  onClear?: () => void;
}

const LogDisplay: React.FC<LogDisplayProps> = ({ logs, isLoading, deploymentId, onClear }) => {
  const [showAISummary, setShowAISummary] = useState(false);

  const exportLogs = () => {
    const logContent = logs.join('\n');
    const blob = new Blob([logContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deployment-logs-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-[#BBBDBC]">
            {logs.length} log entries
          </span>
          {isLoading && (
            <div className="flex items-center gap-2 text-[#00a7e1]">
              <div className="w-4 h-4 border-2 border-[#00a7e1] border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">Processing...</span>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {logs.length > 0 && (
            <>
              <Button
                onClick={() => setShowAISummary(true)}
                size="sm"
                className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80"
              >
                <Brain className="w-4 h-4 mr-2" />
                AI Analysis
              </Button>
              
              <Button
                onClick={exportLogs}
                size="sm"
                variant="outline"
                className="border-[#00a7e1] text-[#00a7e1] hover:bg-[#00a7e1]/10"
              >
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
              
              {onClear && (
                <Button
                  onClick={onClear}
                  size="sm"
                  variant="outline"
                  className="border-red-500 text-red-400 hover:bg-red-500/10"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Log Content */}
      <div className="bg-[#00171f] rounded-md border border-[#00a7e1]/20 overflow-hidden">
        <ScrollArea className="h-96">
          <div className="p-4 font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-center text-[#BBBDBC] py-8">
                No logs to display
              </div>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="text-[#EEEEEE] leading-relaxed mb-1 break-all">
                  <span className="text-[#00a7e1] mr-2">[{index + 1}]</span>
                  {log}
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* AI Summarizer Modal */}
      <AILogSummarizer
        logs={logs}
        isOpen={showAISummary}
        onClose={() => setShowAISummary(false)}
        deploymentId={deploymentId}
      />
    </div>
  );
};

export default LogDisplay;
