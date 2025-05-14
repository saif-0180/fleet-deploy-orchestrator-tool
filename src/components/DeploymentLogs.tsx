
import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface DeploymentLogsProps {
  logs: string[];
}

export const DeploymentLogs = ({ logs }: DeploymentLogsProps) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto scroll to bottom of logs
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCopyLogs = () => {
    const plainLogs = logs.map(log => {
      // Create a temporary div to strip HTML tags
      const div = document.createElement('div');
      div.innerHTML = log;
      return div.textContent || div.innerText || "";
    }).join('\n');
    
    navigator.clipboard.writeText(plainLogs);
  };

  return (
    <Card>
      <CardHeader className="px-6 py-4 flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Deployment Logs</CardTitle>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Switch
              id="auto-scroll"
              checked={autoScroll}
              onCheckedChange={setAutoScroll}
            />
            <Label htmlFor="auto-scroll">Auto-scroll</Label>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLogs}
            disabled={logs.length === 0}
          >
            Copy Logs
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div 
          className="relative bg-secondary/40 rounded-b-lg overflow-hidden"
          style={{ height: "300px" }}
        >
          <ScrollArea 
            className="h-full w-full p-4" 
            ref={scrollRef}
          >
            {logs.length > 0 ? (
              <pre className="code-log">
                {logs.map((log, index) => (
                  <div 
                    key={index}
                    className="py-0.5"
                    dangerouslySetInnerHTML={{ __html: log }}
                  />
                ))}
              </pre>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                No logs available
              </div>
            )}
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
};
