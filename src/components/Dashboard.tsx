
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { FTSelector } from "./FTSelector";
import { FileSelector } from "./FileSelector";
import { TargetSelector } from "./TargetSelector";
import { DeploymentLogs } from "./DeploymentLogs";

const Dashboard = () => {
  const { toast } = useToast();
  const [selectedFT, setSelectedFT] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [deploymentStatus, setDeploymentStatus] = useState<'idle' | 'running' | 'success' | 'failed'>('idle');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  const handleDeploy = () => {
    // Validation
    if (!selectedFT) {
      toast({
        title: "Error",
        description: "Please select a Feature Team",
        variant: "destructive",
      });
      return;
    }

    if (selectedFiles.length === 0) {
      toast({
        title: "Error",
        description: "Please select at least one file to deploy",
        variant: "destructive",
      });
      return;
    }

    if (selectedTargets.length === 0) {
      toast({
        title: "Error",
        description: "Please select at least one target VM",
        variant: "destructive",
      });
      return;
    }

    // Start deployment
    setDeploymentStatus('running');
    setProgress(0);
    setLogs([]);

    // Simulate deployment process
    const startTime = new Date().toISOString();
    addLog(`[${startTime}] Deployment started for FT: ${selectedFT}`);
    addLog(`[${startTime}] Files selected: ${selectedFiles.join(', ')}`);
    addLog(`[${startTime}] Target VMs: ${selectedTargets.join(', ')}`);
    
    // Mock deployment progress
    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += 10;
      setProgress(currentProgress);
      
      if (currentProgress === 30) {
        addLog(`[${new Date().toISOString()}] Connecting to target VMs...`);
      } else if (currentProgress === 50) {
        addLog(`[${new Date().toISOString()}] Preparing files for deployment...`);
        addLog(`[${new Date().toISOString()}] Running ansible playbook...`);
      } else if (currentProgress === 70) {
        addLog(`[${new Date().toISOString()}] Copying files to target VMs...`);
        
        // Add colored logs for each target
        selectedTargets.forEach((target, index) => {
          setTimeout(() => {
            addLog(`<span class="ansi-green-fg">[${new Date().toISOString()}] ✓ Successfully deployed to ${target}</span>`);
          }, index * 800);
        });
      }
      
      if (currentProgress >= 100) {
        clearInterval(interval);
        setProgress(100);
        setDeploymentStatus('success');
        addLog(`<span class="ansi-bright-green-fg">[${new Date().toISOString()}] ✓ Deployment completed successfully!</span>`);
        
        toast({
          title: "Deployment Successful",
          description: `Deployed ${selectedFiles.length} files to ${selectedTargets.length} targets`,
        });
      }
    }, 1000);
  };

  const handleCancel = () => {
    setDeploymentStatus('failed');
    setProgress(0);
    addLog(`<span class="ansi-red-fg">[${new Date().toISOString()}] ✕ Deployment canceled by user</span>`);
    
    toast({
      title: "Deployment Canceled",
      description: "The deployment process has been canceled",
      variant: "destructive",
    });
  };

  const addLog = (message: string) => {
    setLogs(prev => [...prev, message]);
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Deployment Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Deployment Configuration</CardTitle>
            <CardDescription>Configure your deployment settings</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="ft">
              <TabsList className="grid w-full grid-cols-3 mb-6">
                <TabsTrigger value="ft">FT Select</TabsTrigger>
                <TabsTrigger value="files">Files</TabsTrigger>
                <TabsTrigger value="targets">Targets</TabsTrigger>
              </TabsList>
              
              <TabsContent value="ft" className="space-y-4">
                <FTSelector
                  selectedFT={selectedFT}
                  onSelectFT={setSelectedFT}
                />
              </TabsContent>
              
              <TabsContent value="files" className="space-y-4">
                <FileSelector
                  selectedFT={selectedFT}
                  selectedFiles={selectedFiles}
                  onSelectFiles={setSelectedFiles}
                />
              </TabsContent>
              
              <TabsContent value="targets" className="space-y-4">
                <TargetSelector
                  selectedTargets={selectedTargets}
                  onSelectTargets={setSelectedTargets}
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
        
        {/* Deployment Status */}
        <Card>
          <CardHeader>
            <CardTitle>Deployment Status</CardTitle>
            <CardDescription>
              {deploymentStatus === 'idle' && "No active deployment"}
              {deploymentStatus === 'running' && "Deployment in progress"}
              {deploymentStatus === 'success' && "Deployment completed successfully"}
              {deploymentStatus === 'failed' && "Deployment failed or canceled"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {deploymentStatus !== 'idle' && (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Progress: {progress}%</span>
                    {deploymentStatus === 'running' ? (
                      <span className="text-deploy-pending animate-pulse-opacity">● Running</span>
                    ) : deploymentStatus === 'success' ? (
                      <span className="text-deploy-success">● Completed</span>
                    ) : (
                      <span className="text-deploy-error">● Failed</span>
                    )}
                  </div>
                  <Progress value={progress} className="w-full" />
                </div>
                
                {selectedFT && (
                  <Alert variant="outline" className="bg-secondary/40">
                    <AlertTitle>Deployment Info</AlertTitle>
                    <AlertDescription>
                      <div className="text-sm">
                        <p><strong>FT:</strong> {selectedFT}</p>
                        <p><strong>Files:</strong> {selectedFiles.length} selected</p>
                        <p><strong>Targets:</strong> {selectedTargets.length} VMs</p>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </>
            )}
            
            <div className="flex flex-col gap-2 pt-4">
              <Button 
                onClick={handleDeploy} 
                disabled={deploymentStatus === 'running' || !selectedFT || selectedFiles.length === 0 || selectedTargets.length === 0}
                className="w-full"
                variant={deploymentStatus === 'success' ? "outline" : "default"}
              >
                {deploymentStatus === 'success' ? 'Deploy Again' : 'Deploy'}
              </Button>
              
              {deploymentStatus === 'running' && (
                <Button 
                  onClick={handleCancel} 
                  variant="destructive" 
                  className="w-full"
                >
                  Cancel
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Deployment Logs */}
      <DeploymentLogs logs={logs} />
    </div>
  );
};

export default Dashboard;
