import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Upload, RefreshCw, Loader2 } from 'lucide-react';
import VMSelector from '@/components/VMSelector';
import LogDisplay from '@/components/LogDisplay';

interface FileOperationsProps {
  // Define any props here
}

const FileOperations: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedVMs, setSelectedVMs] = useState<string[]>([]);
  const [selectedFT, setSelectedFT] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed'>('idle');
  const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);

  // Fetch FTs
  const { data: fts = [], refetch: refetchFts, isLoading: isLoadingFts } = useQuery({
    queryKey: ['fts'],
    queryFn: async () => {
      const response = await fetch('/api/fts');
      if (!response.ok) {
        throw new Error('Failed to fetch FTs');
      }
      const data = await response.json();
      return data as string[];
    },
    staleTime: 300000,
    refetchOnWindowFocus: false,
  });

  // Fetch Files for selected FT
  const { data: files = [], refetch: refetchFiles, isLoading: isLoadingFiles } = useQuery({
    queryKey: ['ft-files', selectedFT],
    queryFn: async () => {
      if (!selectedFT) return [];
      const response = await fetch(`/api/fts/${selectedFT}/files`);
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      const data = await response.json();
      return data as string[];
    },
    enabled: !!selectedFT,
    refetchOnWindowFocus: false,
  });

  // Deploy mutation
  const deployMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFT || !selectedFile) {
        throw new Error('FT and File must be selected');
      }
      if (selectedVMs.length === 0) {
        throw new Error('At least one VM must be selected');
      }

      const response = await fetch('/api/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ft: selectedFT,
          file: selectedFile,
          vms: selectedVMs,
        }),
      });
      if (!response.ok) {
        throw new Error('Failed to deploy files');
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
        description: `Deployment ID: ${data.deployment_id}`,
      });
      // Start polling for logs
      pollForLogs(data.deployment_id);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to deploy files",
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
    deployMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold bg-gradient-to-r from-[#00171f] to-[#00a7e1] bg-clip-text text-transparent mb-4">File Operations</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="bg-white border border-[#00171f]/20 shadow-sm">
            <CardHeader>
              <CardTitle className="text-[#00171f] text-lg">File Deployment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <VMSelector selectedVMs={selectedVMs} onSelectionChange={setSelectedVMs} />
              
              <div className="flex items-center space-x-2">
                <Select value={selectedFT} onValueChange={setSelectedFT}>
                  <SelectTrigger className="flex-1 bg-white border-[#00171f]/30 text-[#00171f]">
                    <SelectValue placeholder="Select an FT" />
                  </SelectTrigger>
                  <SelectContent>
                    {fts.map((ft) => (
                      <SelectItem key={ft} value={ft}>
                        {ft}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  onClick={() => refetchFts()}
                  className="bg-[#00171f] text-white hover:bg-[#00171f]/80 h-10 w-10 p-0"
                  title="Refresh FTs"
                  disabled={isLoadingFts}
                >
                  {isLoadingFts ? 
                    <Loader2 className="h-4 w-4 animate-spin" /> : 
                    <RefreshCw className="h-4 w-4" />
                  }
                </Button>
              </div>

              <div className="flex items-center space-x-2">
                <Select value={selectedFile} onValueChange={setSelectedFile}>
                  <SelectTrigger className="flex-1 bg-white border-[#00171f]/30 text-[#00171f]">
                    <SelectValue placeholder="Select a file" />
                  </SelectTrigger>
                  <SelectContent>
                    {files.map((file) => (
                      <SelectItem key={file} value={file}>
                        {file}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  onClick={() => refetchFiles()}
                  className="bg-[#00171f] text-white hover:bg-[#00171f]/80 h-10 w-10 p-0"
                  title="Refresh Files"
                  disabled={isLoadingFiles}
                >
                  {isLoadingFiles ? 
                    <Loader2 className="h-4 w-4 animate-spin" /> : 
                    <RefreshCw className="h-4 w-4" />
                  }
                </Button>
              </div>
              
              <Button
                onClick={handleDeploy}
                disabled={deployMutation.isPending || logStatus === 'running'}
                className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/90"
              >
                {deployMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Deploying...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Deploy Files
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

export default FileOperations;
