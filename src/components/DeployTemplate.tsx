import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Play, Loader2 } from 'lucide-react';
import VMSelector from '@/components/VMSelector';
import LogDisplay from '@/components/LogDisplay';

const DeployTemplate: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedVMs, setSelectedVMs] = useState<string[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
  const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);

  // Fetch available templates
  const { data: templates = [], refetch: refetchTemplates, isLoading: isLoadingTemplates } = useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      const response = await fetch('/api/templates');
      if (!response.ok) {
        throw new Error('Failed to fetch templates');
      }
      const data = await response.json();
      return data as { id: string; name: string; description: string; content: string; }[];
    },
    staleTime: 300000,
    refetchOnWindowFocus: false,
  });

  // Mutation to execute deployment
  const deploymentMutation = useMutation({
    mutationFn: async ({ vms, templateId }: { vms: string[], templateId: string }) => {
      const response = await fetch('/api/deploy/template', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vms, templateId }),
      });
      if (!response.ok) {
        throw new Error('Failed to initiate deployment');
      }
      const data = await response.json();
      return data;
    },
    onSuccess: (data) => {
      setCurrentDeploymentId(data.deployment_id);
      setLogStatus('running');
      setLogs([]);
      toast({
        title: "Deployment Started",
        description: `Deployment started with ID: ${data.deployment_id}`,
      });
      // Start polling for logs
      pollForLogs(data.deployment_id);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to initiate deployment",
        variant: "destructive",
      });
    },
  });

  // Function to poll for logs
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
          // Refresh deployment history
          queryClient.invalidateQueries({ queryKey: ['deployment-history'] });
        }
      } catch (error) {
        console.error('Error polling logs:', error);
        clearInterval(pollInterval);
        setLogStatus('failed');
      }
    }, 2000);

    // Clean up interval after 10 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      if (logStatus === 'running') {
        setLogStatus('completed');
      }
    }, 600000);
  };

  const handleDeploy = () => {
    if (selectedVMs.length > 0 && selectedTemplate) {
      deploymentMutation.mutate({ vms: selectedVMs, templateId: selectedTemplate });
    } else {
      toast({
        title: "Error",
        description: "Please select VMs and a template.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold gradient-heading mb-6">Deploy Template</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-t-lg">
              <CardTitle className="text-primary text-lg font-semibold">Template Deployment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-6">
              <VMSelector selectedVMs={selectedVMs} onSelectionChange={setSelectedVMs} />
              
              <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                <SelectTrigger className="w-full bg-input border-border text-foreground">
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Button
                onClick={handleDeploy}
                disabled={deploymentMutation.isPending || logStatus === 'running'}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-medium py-2"
              >
                {deploymentMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Deploying...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Deploy Template
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
            title={`Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
            status={logStatus}
          />
        </div>
      </div>
    </div>
  );
};

export default DeployTemplate;
