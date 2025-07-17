import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Terminal, Loader2 } from 'lucide-react';
import VMSelector from '@/components/VMSelector';
import LogDisplay from '@/components/LogDisplay';

const ShellCommandOperations: React.FC = () => {
  const { toast } = useToast();
  const [selectedVMs, setSelectedVMs] = useState<string[]>([]);
  const [command, setCommand] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed'>('idle');
  const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);

  const executeMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/shell/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vms: selectedVMs, command }),
      });
      if (!response.ok) {
        throw new Error('Failed to execute command');
      }
      const data = await response.json();
      return data;
    },
    onSuccess: (data) => {
      setCurrentDeploymentId(data.deployment_id);
      setLogStatus('running');
      setLogs([]);
      toast({
        title: "Command Executed",
        description: `Command execution started with ID: ${data.deployment_id}`,
      });
      pollForLogs(data.deployment_id);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to execute command",
        variant: "destructive",
      });
    },
  });

  const pollForLogs = async (deploymentId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/deploy/${deploymentId}/logs`);
        if (!response.ok) {
          clearInterval(pollInterval);
          return;
        }
        
        const data = await response.json();
        setLogs(data.logs || []);
        
        if (data.status === 'success' || data.status === 'failed') {
          setLogStatus(data.status);
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Error polling logs:', error);
        clearInterval(pollInterval);
        setLogStatus('failed');
      }
    }, 2000);
  };

  const handleExecute = () => {
    if (selectedVMs.length > 0 && command) {
      executeMutation.mutate();
    } else {
      toast({
        title: "Error",
        description: "Please select VMs and enter a command.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold bg-gradient-to-r from-[#00171f] to-[#00a7e1] bg-clip-text text-transparent mb-4">Shell Command Operations</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="bg-white border border-[#00171f]/20 shadow-sm">
            <CardHeader>
              <CardTitle className="text-[#00171f] text-lg">Execute Commands</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <VMSelector selectedVMs={selectedVMs} onSelectionChange={setSelectedVMs} />
              
              <div>
                <Label htmlFor="command" className="text-[#00171f]">Command</Label>
                <Textarea
                  id="command"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="Enter shell command..."
                  className="min-h-[100px] bg-white border-[#00171f]/30 text-[#00171f]"
                />
              </div>
              
              <Button
                onClick={handleExecute}
                disabled={executeMutation.isPending || logStatus === 'running' || !command.trim() || selectedVMs.length === 0}
                className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/90"
              >
                {executeMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Terminal className="mr-2 h-4 w-4" />
                    Execute Command
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <LogDisplay 
            logs={logs} 
            height="400px" 
            title={`Command Execution Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
            status={logStatus}
          />
        </div>
      </div>
    </div>
  );
};

export default ShellCommandOperations;
