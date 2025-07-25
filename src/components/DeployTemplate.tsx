import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, Play, Loader2, CheckCircle, XCircle } from 'lucide-react';
import LogDisplay from '@/components/LogDisplay';
import TemplateFlowchart from '@/components/TemplateFlowchart';

interface DeploymentTemplate {
  metadata: {
    ft_number: string;
    generated_at: string;
    description: string;
    total_steps?: number;
  };
  steps: Array<{
    type: string;
    description: string;
    order: number;
    ftNumber?: string;
    files?: string[];
    targetVMs?: string[];
    targetUser?: string;
    targetPath?: string;
    service?: string;
    operation?: string;
    playbook?: string;
    helmDeploymentType?: string;
    dbConnection?: string;
    dbUser?: string;
    dbPassword?: string;
    [key: string]: any;
  }>;
  dependencies: Array<{
    step: number;
    depends_on: number[];
    parallel: boolean;
  }>;
}

// Progress Bar Component
const ProgressBar: React.FC<{
  progress: number;
  status: 'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed';
  className?: string;
}> = ({ progress, status, className = '' }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      default:
        return null;
    }
  };

  const getProgressBarColor = () => {
    switch (status) {
      case 'success':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      <div className="flex-1">
        <div className="w-full bg-gray-700 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-300 ease-out ${getProgressBarColor()}`}
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <span className="text-sm text-[#EEEEEE] font-medium min-w-[3rem]">
          {Math.round(progress)}%
        </span>
        {getStatusIcon()}
      </div>
    </div>
  );
};

const DeployTemplate: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [loadedTemplate, setLoadedTemplate] = useState<DeploymentTemplate | null>(null);
  const [deploymentLogs, setDeploymentLogs] = useState<string[]>([]);
  const [deploymentId, setDeploymentId] = useState<string | null>(null);
  const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
  const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);

  useEffect(() => {
    if (!deploymentId || !loadedTemplate) return;

    const totalSteps = loadedTemplate.metadata.total_steps || 0;

    const cleanup = pollLogs(
      deploymentId,
      setDeploymentLogs,
      setLogStatus,
      totalSteps
    );

    return () => {
      if (cleanup) cleanup();
    };
  }, [deploymentId, loadedTemplate]);

  const {
    data: templates = [],
    refetch: refetchTemplates,
    isLoading: isLoadingTemplates
  } = useQuery({
    queryKey: ['deploy-templates'],
    queryFn: async () => {
      const response = await fetch('/api/deploy/templates');
      if (!response.ok) throw new Error('Failed to fetch templates');
      const data = await response.json();
      return data.templates as string[];
    },
    staleTime: 300000,
    refetchOnWindowFocus: false,
  });

  const loadTemplateMutation = useMutation({
    mutationFn: async (templateName: string) => {
      console.log("Loading template:", templateName);
      const response = await fetch(`/api/deploy/templates/${templateName}`);
      if (!response.ok) throw new Error('Failed to load template');
      const data = await response.json();
      return data.template as DeploymentTemplate;
    },
    onSuccess: (template) => {
      setLoadedTemplate(template);
      setProgress(0); // Reset progress when new template is loaded
      setLogStatus('idle');
      toast({
        title: "Template Loaded",
        description: `Template ${template.metadata.ft_number} loaded successfully`,
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to load template",
        variant: "destructive",
      });
    },
  });

  const deployTemplateMutation = useMutation({
    mutationFn: async (templateName: string) => {
      console.log(`Deploying template: ${templateName}`);
      const response = await fetch('/api/deploy/templates/execute', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
         },
        body: JSON.stringify({ template_name: templateName }),
      });
      
      if (!response.ok) throw new Error('Failed to start template deployment');
      const data = await response.json();
      console.log("Template deployment started:", data);
      return data;
    },
    onSuccess: (data) => {
      setCurrentDeploymentId(data.deployment_id);
      setLogStatus('running');
      setDeploymentLogs([]);
      setProgress(0);
      toast({
        title: "Deployment Started",
        description: `Template deployment started with ID: ${data.deployment_id}`,
      });
      pollLogs(data.deployment_id, setDeploymentLogs, setLogStatus, loadedTemplate?.metadata.total_steps || 0);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start template deployment",
        variant: "destructive",
      });
    },
  });

  const pollLogs = (
    id: string,
    logSetter: React.Dispatch<React.SetStateAction<string[]>>,
    statusSetter: React.Dispatch<React.SetStateAction<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>>,
    totalSteps: number
  ) => {
    if (!id || !totalSteps) return;
    logSetter([]);
    statusSetter("running");
    setIsPolling(true);
    let pollCount = 0;
    let lastLogLength = 0;
    let completedSteps = 0;
    let hasActualFailure = false;
    let isDeploymentComplete = false;
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/deploy/${id}/logs`);
        if (!response.ok) {
          throw new Error("Failed to fetch logs");
        }
        const data = await response.json();
        if (data.logs) {
          logSetter(data.logs);
          
          // Track failures but don't immediately set status
          hasActualFailure = checkForActualFailures(data.logs);
          
          // Update completed steps
          completedSteps = countCompletedSteps(data.logs);
          
          // Update progress bar
          const currentProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
          setProgress(currentProgress);
          
          // Check if deployment has completed (either success or failure)
          if (completedSteps >= totalSteps || hasActualFailure) {
            isDeploymentComplete = true;
            
            // If all steps completed successfully
            if (completedSteps >= totalSteps && checkFinalSuccess(data.logs)) {
              console.log("All steps completed successfully");
              setProgress(100);
              statusSetter("success");
              clearInterval(pollInterval);
              setIsPolling(false);
              return;
            }
            
            // If we have a failure and deployment has stopped
            if (hasActualFailure && !checkIfActivelyRunning(data.logs)) {
              console.log("Deployment failed due to step failure");
              statusSetter("failed");
              clearInterval(pollInterval);
              setIsPolling(false);
              return;
            }
          }
          
          // Check for active execution
          const isActivelyRunning = checkIfActivelyRunning(data.logs);
          if (isActivelyRunning) {
            console.log("Deployment is actively running");
            return; // Keep status as "running"
          }
          
          // Check for unchanged logs (potential stall)
          if (data.logs.length === lastLogLength) {
            pollCount++;
            
            // Be more patient during step transitions
            const waitThreshold = completedSteps < totalSteps ? 30 : 10;
            
            if (pollCount >= waitThreshold) {
              console.log(`Logs unchanged for ${waitThreshold} seconds. Completed: ${completedSteps}/${totalSteps}`);
              
              if (isDeploymentComplete) {
                // If we thought it was complete but no success indicators
                if (completedSteps >= totalSteps) {
                  statusSetter("failed");
                } else {
                  statusSetter("failed");
                }
              } else {
                // Not all steps completed - continue waiting unless stalled too long
                if (pollCount >= 60) {
                  console.log("Deployment appears genuinely stalled");
                  statusSetter("failed");
                }
              }
              
              clearInterval(pollInterval);
              setIsPolling(false);
              return;
            }
          } else {
            pollCount = 0;
            lastLogLength = data.logs.length;
          }
        }
        
        // Timeout after 10 minutes
        if (pollCount > 600) {
          console.log("Operation timed out after 10 minutes");
          const finalCheck = completedSteps >= totalSteps && 
                            (checkFinalSuccess(data.logs) || checkRecentStepCompletion(data.logs));
          if (finalCheck) {
            setProgress(100);
            statusSetter("success");
          } else {
            statusSetter("failed");
          }
          clearInterval(pollInterval);
          setIsPolling(false);
        }
      } catch (error) {
        console.error("Error fetching logs:", error);
        pollCount += 5;
        if (pollCount > 30) {
          console.log("Too many polling errors - marking as failed");
          statusSetter("failed");
          clearInterval(pollInterval);
          setIsPolling(false);
        }
      }
    }, 1000);
    
    return () => {
      clearInterval(pollInterval);
      setIsPolling(false);
    };
  };

  // Helper function to check for actual deployment failures
  const checkForActualFailures = (logs: string[]): boolean => {
    const failurePatterns = [
      /FAILED - RETRYING:/i,
      /fatal:/i,
      /^error:/i, // Only lines that start with "error:", not containing "error"
      /deployment failed/i,
      /step \d+ failed/i,
      /unreachable=[1-9]/i, // Unreachable hosts (not unreachable=0)
      /failed=[1-9]/i, // Actual failed tasks (not failed=0)
      /ansible.*failed.*[^=][1-9]/i // Ansible failures that are not "failed=0"
    ];

    // Check last 20 lines for failure patterns, excluding PLAY RECAP success lines
    const recentLogs = logs.slice(-20);
    
    return recentLogs.some(line => {
      // Skip PLAY RECAP lines with failed=0 and unreachable=0 (these indicate success)
      if (line.includes('PLAY RECAP') && (line.includes('failed=0') || line.includes('unreachable=0'))) {
        return false;
      }
      
      // Skip SUCCESS messages
      if (line.includes('SUCCESS:') || line.includes('completed successfully')) {
        return false;
      }
      
      return failurePatterns.some(pattern => pattern.test(line));
    });
  };

  // Helper function to count completed steps more accurately
  const countCompletedSteps = (logs: string[]): number => {
    const processedSteps = new Set<number>();
    
    // Only count explicit step completion messages, not intermediate success messages
    logs.forEach(line => {
      // Match exact patterns for step completion
      const stepCompletionPatterns = [
        /^Step (\d+) completed successfully$/i,
        /^=== .* Step (\d+) Completed Successfully ===$/i,
        /^--- Step (\d+) succeeded ---$/i
      ];
      
      stepCompletionPatterns.forEach(pattern => {
        const match = line.match(pattern);
        if (match) {
          const stepNum = parseInt(match[1]);
          if (stepNum && stepNum > 0) {
            processedSteps.add(stepNum);
          }
        }
      });
    });

    return processedSteps.size;
  };

  // Helper function to check if the final deployment is successful
  const checkFinalSuccess = (logs: string[]): boolean => {
    const successPatterns = [
      /All files deployed successfully/i,
      /Template deployment completed successfully/i,
      /All steps completed successfully/i,
      /Deployment finished successfully/i,
      /SUCCESS: .* completed successfully/i
    ];

    // Check the last 30 lines for final success indicators
    const recentLogs = logs.slice(-30);
    
    return recentLogs.some(line => 
      successPatterns.some(pattern => pattern.test(line))
    );
  };

  // Helper function to check if a step was recently completed
  const checkRecentStepCompletion = (logs: string[]): boolean => {
    const recentLogs = logs.slice(-20); // Check last 20 lines
    
    const recentCompletionPatterns = [
      /Step \d+ completed successfully/i,
      /=== .* Step \d+ Completed Successfully ===/i,
      /SUCCESS: .* completed successfully/i,
      /PLAY RECAP.*failed=0/i // Ansible success recap
    ];
    
    return recentLogs.some(line => 
      recentCompletionPatterns.some(pattern => pattern.test(line))
    );
  };

  // Helper function to check if deployment is actively running
  const checkIfActivelyRunning = (logs: string[]): boolean => {
    const recentLogs = logs.slice(-15); // Check last 15 lines
    
    const activePatterns = [
      /=== Starting Step \d+:/i,
      /=== Executing File Deployment Step \d+ ===/i,
      /PLAY \[/i,
      /TASK \[/i,
      /changed:/i,
      /ok:/i,
      /Executing: ansible-playbook/i,
      /Using .* as config file/i,
      /PLAY RECAP \*+/i, // Ansible is running a playbook
      /ansible-playbook -i/i,
      /Created inventory file/i
    ];
    
    const isActive = recentLogs.some(line => 
      activePatterns.some(pattern => pattern.test(line))
    );
    
    // Additional check: if we see step completion but not the final step, it's still active
    const hasRecentStepCompletion = recentLogs.some(line => 
      /Step \d+ completed successfully/i.test(line)
    );
    
    const hasFinalSuccess = recentLogs.some(line => 
      /=== Template Deployment SUCCESS ===/i.test(line) ||
      /All steps completed successfully/i.test(line)
    );
    
    return isActive || (hasRecentStepCompletion && !hasFinalSuccess);
  };

  // Additional helper to get current deployment status for UI display
  const getCurrentDeploymentStatus = (logs: string[], completedSteps: number, totalSteps: number): string => {
    if (logs.length === 0) return "Initializing deployment...";
    
    const lastFewLines = logs.slice(-10);
    
    // Look for current step indicators
    for (const line of lastFewLines.reverse()) {
      if (line.includes("=== Starting Step")) {
        const stepMatch = line.match(/Step (\d+)/);
        if (stepMatch) {
          return `Executing Step ${stepMatch[1]} of ${totalSteps}...`;
        }
      }
      if (line.includes("=== Executing")) {
        return "Executing deployment step...";
      }
    }
    
    return `Progress: ${completedSteps}/${totalSteps} steps completed`;
  };

  const handleLoadTemplate = () => {
    if (selectedTemplate) {
      loadTemplateMutation.mutate(selectedTemplate);
    }
  };

  const handleDeployTemplate = () => {
    if (selectedTemplate && loadedTemplate) {
      setDeploymentLogs([]);
      deployTemplateMutation.mutate(selectedTemplate); 
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Template Selection and Deployment Flow */}
        <div className="space-y-4">
          <Card className="bg-[#1a2b42]">
            <CardHeader>
              <CardTitle className="text-[#EEEEEE] text-lg">Template Selection</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger className="flex-1 bg-[#1a2b42] border-[#EEEEEE] text-[#EEEEEE]">
                    <SelectValue placeholder="Select a template" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((template) => (
                      <SelectItem key={template} value={template}>
                        {template}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  onClick={() => refetchTemplates()}
                  className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/80 h-10 w-10 p-0"
                  title="Refresh Templates"
                  disabled={isLoadingTemplates}
                >
                  {isLoadingTemplates ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                </Button>
              </div>

              <div className="flex space-x-2">
                <Button
                  onClick={handleLoadTemplate}
                  disabled={!selectedTemplate || loadTemplateMutation.isPending}
                  className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 flex-1"
                >
                  {loadTemplateMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    "Load Template"
                  )}
                </Button>

                <Button
                  onClick={handleDeployTemplate}
                  disabled={!loadedTemplate || deployTemplateMutation.isPending || logStatus === 'running'}
                  className="bg-green-600 text-white hover:bg-green-600/80 flex-1"
                >
                  {deployTemplateMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Deploy
                    </>
                  )}
                </Button>
              </div>

              {loadedTemplate && (
                <div className="text-sm text-[#EEEEEE] bg-[#2A4759] p-3 rounded">
                  <p><strong>FT Number:</strong> {loadedTemplate.metadata.ft_number}</p>
                  <p><strong>Description:</strong> {loadedTemplate.metadata.description}</p>
                  <p><strong>Total Steps:</strong> {loadedTemplate.metadata.total_steps}</p>
                </div>
              )}

              {/* Progress Bar Section */}
              {loadedTemplate && (logStatus === 'running' || logStatus === 'success' || logStatus === 'failed') && (
                <div className="bg-[#2A4759] p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#EEEEEE]">
                      Deployment Progress
                    </span>
                    <span className="text-xs text-gray-400">
                      {getCurrentDeploymentStatus(deploymentLogs, Math.round((progress / 100) * (loadedTemplate?.metadata.total_steps || 0)), loadedTemplate?.metadata.total_steps || 0)}
                    </span>
                  </div>
                  <ProgressBar
                    progress={progress}
                    status={logStatus}
                    className="mt-2"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Deployment Flow moved to left column */}
          {loadedTemplate && (
            <Card className="bg-[#1a2b42]">
              <CardHeader>
                <CardTitle className="text-[#EEEEEE] text-lg">Deployment Flow</CardTitle>
              </CardHeader>
              <CardContent>
                <div 
                  className="overflow-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
                  style={{ height: "400px", maxHeight: "400px" }}
                >
                  <TemplateFlowchart template={loadedTemplate} />
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Logs (Fixed Height) */}
        <div className="space-y-4">
          <Card className="bg-[#1a2b42]">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-[#EEEEEE] text-lg">
                  Template Deployment Logs{currentDeploymentId ? ` - ${currentDeploymentId}` : ''}
                </CardTitle>
                <div className="flex items-center">
                  {logStatus === 'running' && (
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  )}
                  {logStatus === 'success' && (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  {logStatus === 'failed' && (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div 
                ref={(el) => {
                  if (el && deploymentLogs.length > 0) {
                    el.scrollTop = el.scrollHeight;
                  }
                }}
                className="bg-black text-white font-mono text-sm p-4 overflow-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
                style={{ 
                  height: "480px",
                  maxHeight: "480px"
                }}
              >
                {deploymentLogs.length === 0 ? (
                  <div className="text-gray-500 italic">No logs available...</div>
                ) : (
                  deploymentLogs.map((log, index) => (
                    <div key={index} className="whitespace-pre-wrap break-words">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DeployTemplate;

// import React, { useState, useEffect } from 'react';
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// import { useToast } from "@/hooks/use-toast";
// import { RefreshCw, Play, Loader2, CheckCircle, XCircle } from 'lucide-react';
// import LogDisplay from '@/components/LogDisplay';
// import TemplateFlowchart from '@/components/TemplateFlowchart';

// interface DeploymentTemplate {
//   metadata: {
//     ft_number: string;
//     generated_at: string;
//     description: string;
//     total_steps?: number;
//   };
//   steps: Array<{
//     type: string;
//     description: string;
//     order: number;
//     ftNumber?: string;
//     files?: string[];
//     targetVMs?: string[];
//     targetUser?: string;
//     targetPath?: string;
//     service?: string;
//     operation?: string;
//     playbook?: string;
//     helmDeploymentType?: string;
//     dbConnection?: string;
//     dbUser?: string;
//     dbPassword?: string;
//     [key: string]: any;
//   }>;
//   dependencies: Array<{
//     step: number;
//     depends_on: number[];
//     parallel: boolean;
//   }>;
// }

// // Progress Bar Component
// const ProgressBar: React.FC<{
//   progress: number;
//   status: 'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed';
//   className?: string;
// }> = ({ progress, status, className = '' }) => {
//   const getStatusIcon = () => {
//     switch (status) {
//       case 'success':
//         return <CheckCircle className="h-5 w-5 text-green-500" />;
//       case 'failed':
//         return <XCircle className="h-5 w-5 text-red-500" />;
//       case 'running':
//         return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
//       default:
//         return null;
//     }
//   };

//   const getProgressBarColor = () => {
//     switch (status) {
//       case 'success':
//         return 'bg-green-500';
//       case 'failed':
//         return 'bg-red-500';
//       case 'running':
//         return 'bg-blue-500';
//       default:
//         return 'bg-gray-500';
//     }
//   };

//   return (
//     <div className={`flex items-center space-x-3 ${className}`}>
//       <div className="flex-1">
//         <div className="w-full bg-gray-700 rounded-full h-2.5">
//           <div
//             className={`h-2.5 rounded-full transition-all duration-300 ease-out ${getProgressBarColor()}`}
//             style={{ width: `${Math.min(progress, 100)}%` }}
//           />
//         </div>
//       </div>
//       <div className="flex items-center space-x-2">
//         <span className="text-sm text-[#EEEEEE] font-medium min-w-[3rem]">
//           {Math.round(progress)}%
//         </span>
//         {getStatusIcon()}
//       </div>
//     </div>
//   );
// };

// const DeployTemplate: React.FC = () => {
//   const { toast } = useToast();
//   const queryClient = useQueryClient();
//   const [selectedTemplate, setSelectedTemplate] = useState<string>('');
//   const [loadedTemplate, setLoadedTemplate] = useState<DeploymentTemplate | null>(null);
//   const [deploymentLogs, setDeploymentLogs] = useState<string[]>([]);
//   const [deploymentId, setDeploymentId] = useState<string | null>(null);
//   const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
//   const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);
//   const [isPolling, setIsPolling] = useState<boolean>(false);
//   const [progress, setProgress] = useState<number>(0);

//   useEffect(() => {
//     if (!deploymentId || !loadedTemplate) return;

//     const totalSteps = loadedTemplate.metadata.total_steps || 0;

//     const cleanup = pollLogs(
//       deploymentId,
//       setDeploymentLogs,
//       setLogStatus,
//       totalSteps
//     );

//     return () => {
//       if (cleanup) cleanup();
//     };
//   }, [deploymentId, loadedTemplate]);

//   const {
//     data: templates = [],
//     refetch: refetchTemplates,
//     isLoading: isLoadingTemplates
//   } = useQuery({
//     queryKey: ['deploy-templates'],
//     queryFn: async () => {
//       const response = await fetch('/api/deploy/templates');
//       if (!response.ok) throw new Error('Failed to fetch templates');
//       const data = await response.json();
//       return data.templates as string[];
//     },
//     staleTime: 300000,
//     refetchOnWindowFocus: false,
//   });

//   const loadTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log("Loading template:", templateName);
//       const response = await fetch(`/api/deploy/templates/${templateName}`);
//       if (!response.ok) throw new Error('Failed to load template');
//       const data = await response.json();
//       return data.template as DeploymentTemplate;
//     },
//     onSuccess: (template) => {
//       setLoadedTemplate(template);
//       setProgress(0); // Reset progress when new template is loaded
//       setLogStatus('idle');
//       toast({
//         title: "Template Loaded",
//         description: `Template ${template.metadata.ft_number} loaded successfully`,
//       });
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to load template",
//         variant: "destructive",
//       });
//     },
//   });

//   const deployTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Deploying template: ${templateName}`);
//       const response = await fetch('/api/deploy/templates/execute', {
//         method: 'POST',
//         headers: { 
//           'Content-Type': 'application/json',
//          },
//         body: JSON.stringify({ template_name: templateName }),
//       });
      
//       if (!response.ok) throw new Error('Failed to start template deployment');
//       const data = await response.json();
//       console.log("Template deployment started:", data);
//       return data;
//     },
//     onSuccess: (data) => {
//       setCurrentDeploymentId(data.deployment_id);
//       setLogStatus('running');
//       setDeploymentLogs([]);
//       setProgress(0);
//       toast({
//         title: "Deployment Started",
//         description: `Template deployment started with ID: ${data.deployment_id}`,
//       });
//       pollLogs(data.deployment_id, setDeploymentLogs, setLogStatus, loadedTemplate?.metadata.total_steps || 0);
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to start template deployment",
//         variant: "destructive",
//       });
//     },
//   });

//   const pollLogs = (
//     id: string,
//     logSetter: React.Dispatch<React.SetStateAction<string[]>>,
//     statusSetter: React.Dispatch<React.SetStateAction<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>>,
//     totalSteps: number
//   ) => {
//     if (!id || !totalSteps) return;
//     logSetter([]);
//     statusSetter("running");
//     setIsPolling(true);
//     let pollCount = 0;
//     let lastLogLength = 0;
//     let completedSteps = 0;
//     let hasActualFailure = false;
//     let isDeploymentComplete = false;
    
//     const pollInterval = setInterval(async () => {
//       try {
//         const response = await fetch(`/api/deploy/${id}/logs`);
//         if (!response.ok) {
//           throw new Error("Failed to fetch logs");
//         }
//         const data = await response.json();
//         if (data.logs) {
//           logSetter(data.logs);
          
//           // Track failures but don't immediately set status
//           hasActualFailure = checkForActualFailures(data.logs);
          
//           // Update completed steps
//           completedSteps = countCompletedSteps(data.logs);
          
//           // Update progress bar
//           const currentProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
//           setProgress(currentProgress);
          
//           // Check if deployment has completed (either success or failure)
//           if (completedSteps >= totalSteps || hasActualFailure) {
//             isDeploymentComplete = true;
            
//             // If all steps completed successfully
//             if (completedSteps >= totalSteps && checkFinalSuccess(data.logs)) {
//               console.log("All steps completed successfully");
//               setProgress(100);
//               statusSetter("success");
//               clearInterval(pollInterval);
//               setIsPolling(false);
//               return;
//             }
            
//             // If we have a failure and deployment has stopped
//             if (hasActualFailure && !checkIfActivelyRunning(data.logs)) {
//               console.log("Deployment failed due to step failure");
//               statusSetter("failed");
//               clearInterval(pollInterval);
//               setIsPolling(false);
//               return;
//             }
//           }
          
//           // Check for active execution
//           const isActivelyRunning = checkIfActivelyRunning(data.logs);
//           if (isActivelyRunning) {
//             console.log("Deployment is actively running");
//             return; // Keep status as "running"
//           }
          
//           // Check for unchanged logs (potential stall)
//           if (data.logs.length === lastLogLength) {
//             pollCount++;
            
//             // Be more patient during step transitions
//             const waitThreshold = completedSteps < totalSteps ? 30 : 10;
            
//             if (pollCount >= waitThreshold) {
//               console.log(`Logs unchanged for ${waitThreshold} seconds. Completed: ${completedSteps}/${totalSteps}`);
              
//               if (isDeploymentComplete) {
//                 // If we thought it was complete but no success indicators
//                 if (completedSteps >= totalSteps) {
//                   statusSetter("failed");
//                 } else {
//                   statusSetter("failed");
//                 }
//               } else {
//                 // Not all steps completed - continue waiting unless stalled too long
//                 if (pollCount >= 60) {
//                   console.log("Deployment appears genuinely stalled");
//                   statusSetter("failed");
//                 }
//               }
              
//               clearInterval(pollInterval);
//               setIsPolling(false);
//               return;
//             }
//           } else {
//             pollCount = 0;
//             lastLogLength = data.logs.length;
//           }
//         }
        
//         // Timeout after 10 minutes
//         if (pollCount > 600) {
//           console.log("Operation timed out after 10 minutes");
//           const finalCheck = completedSteps >= totalSteps && 
//                             (checkFinalSuccess(data.logs) || checkRecentStepCompletion(data.logs));
//           if (finalCheck) {
//             setProgress(100);
//             statusSetter("success");
//           } else {
//             statusSetter("failed");
//           }
//           clearInterval(pollInterval);
//           setIsPolling(false);
//         }
//       } catch (error) {
//         console.error("Error fetching logs:", error);
//         pollCount += 5;
//         if (pollCount > 30) {
//           console.log("Too many polling errors - marking as failed");
//           statusSetter("failed");
//           clearInterval(pollInterval);
//           setIsPolling(false);
//         }
//       }
//     }, 1000);
    
//     return () => {
//       clearInterval(pollInterval);
//       setIsPolling(false);
//     };
//   };

//   // Helper function to check for actual deployment failures
//   const checkForActualFailures = (logs: string[]): boolean => {
//     const failurePatterns = [
//       /FAILED - RETRYING:/i,
//       /fatal:/i,
//       /^error:/i, // Only lines that start with "error:", not containing "error"
//       /deployment failed/i,
//       /step \d+ failed/i,
//       /unreachable=[1-9]/i, // Unreachable hosts (not unreachable=0)
//       /failed=[1-9]/i, // Actual failed tasks (not failed=0)
//       /ansible.*failed.*[^=][1-9]/i // Ansible failures that are not "failed=0"
//     ];

//     // Check last 20 lines for failure patterns, excluding PLAY RECAP success lines
//     const recentLogs = logs.slice(-20);
    
//     return recentLogs.some(line => {
//       // Skip PLAY RECAP lines with failed=0 and unreachable=0 (these indicate success)
//       if (line.includes('PLAY RECAP') && (line.includes('failed=0') || line.includes('unreachable=0'))) {
//         return false;
//       }
      
//       // Skip SUCCESS messages
//       if (line.includes('SUCCESS:') || line.includes('completed successfully')) {
//         return false;
//       }
      
//       return failurePatterns.some(pattern => pattern.test(line));
//     });
//   };

//   // Helper function to count completed steps more accurately
//   const countCompletedSteps = (logs: string[]): number => {
//     const processedSteps = new Set<number>();
    
//     // Only count explicit step completion messages, not intermediate success messages
//     logs.forEach(line => {
//       // Match exact patterns for step completion
//       const stepCompletionPatterns = [
//         /^Step (\d+) completed successfully$/i,
//         /^=== .* Step (\d+) Completed Successfully ===$/i,
//         /^--- Step (\d+) succeeded ---$/i
//       ];
      
//       stepCompletionPatterns.forEach(pattern => {
//         const match = line.match(pattern);
//         if (match) {
//           const stepNum = parseInt(match[1]);
//           if (stepNum && stepNum > 0) {
//             processedSteps.add(stepNum);
//           }
//         }
//       });
//     });

//     return processedSteps.size;
//   };

//   // Helper function to check if the final deployment is successful
//   const checkFinalSuccess = (logs: string[]): boolean => {
//     const successPatterns = [
//       /All files deployed successfully/i,
//       /Template deployment completed successfully/i,
//       /All steps completed successfully/i,
//       /Deployment finished successfully/i,
//       /SUCCESS: .* completed successfully/i
//     ];

//     // Check the last 30 lines for final success indicators
//     const recentLogs = logs.slice(-30);
    
//     return recentLogs.some(line => 
//       successPatterns.some(pattern => pattern.test(line))
//     );
//   };

//   // Helper function to check if a step was recently completed
//   const checkRecentStepCompletion = (logs: string[]): boolean => {
//     const recentLogs = logs.slice(-20); // Check last 20 lines
    
//     const recentCompletionPatterns = [
//       /Step \d+ completed successfully/i,
//       /=== .* Step \d+ Completed Successfully ===/i,
//       /SUCCESS: .* completed successfully/i,
//       /PLAY RECAP.*failed=0/i // Ansible success recap
//     ];
    
//     return recentLogs.some(line => 
//       recentCompletionPatterns.some(pattern => pattern.test(line))
//     );
//   };

//   // Helper function to check if deployment is actively running
//   const checkIfActivelyRunning = (logs: string[]): boolean => {
//     const recentLogs = logs.slice(-15); // Check last 15 lines
    
//     const activePatterns = [
//       /=== Starting Step \d+:/i,
//       /=== Executing File Deployment Step \d+ ===/i,
//       /PLAY \[/i,
//       /TASK \[/i,
//       /changed:/i,
//       /ok:/i,
//       /Executing: ansible-playbook/i,
//       /Using .* as config file/i,
//       /PLAY RECAP \*+/i, // Ansible is running a playbook
//       /ansible-playbook -i/i,
//       /Created inventory file/i
//     ];
    
//     const isActive = recentLogs.some(line => 
//       activePatterns.some(pattern => pattern.test(line))
//     );
    
//     // Additional check: if we see step completion but not the final step, it's still active
//     const hasRecentStepCompletion = recentLogs.some(line => 
//       /Step \d+ completed successfully/i.test(line)
//     );
    
//     const hasFinalSuccess = recentLogs.some(line => 
//       /=== Template Deployment SUCCESS ===/i.test(line) ||
//       /All steps completed successfully/i.test(line)
//     );
    
//     return isActive || (hasRecentStepCompletion && !hasFinalSuccess);
//   };

//   // Additional helper to get current deployment status for UI display
//   const getCurrentDeploymentStatus = (logs: string[], completedSteps: number, totalSteps: number): string => {
//     if (logs.length === 0) return "Initializing deployment...";
    
//     const lastFewLines = logs.slice(-10);
    
//     // Look for current step indicators
//     for (const line of lastFewLines.reverse()) {
//       if (line.includes("=== Starting Step")) {
//         const stepMatch = line.match(/Step (\d+)/);
//         if (stepMatch) {
//           return `Executing Step ${stepMatch[1]} of ${totalSteps}...`;
//         }
//       }
//       if (line.includes("=== Executing")) {
//         return "Executing deployment step...";
//       }
//     }
    
//     return `Progress: ${completedSteps}/${totalSteps} steps completed`;
//   };

//   const handleLoadTemplate = () => {
//     if (selectedTemplate) {
//       loadTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   const handleDeployTemplate = () => {
//     if (selectedTemplate && loadedTemplate) {
//       setDeploymentLogs([]);
//       deployTemplateMutation.mutate(selectedTemplate); 
//     }
//   };

//   return (
//     <div className="space-y-6">
//       <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>

//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//         {/* Left Column - Template Selection and Deployment Flow */}
//         <div className="space-y-4">
//           <Card className="bg-[#1a2b42]">
//             <CardHeader>
//               <CardTitle className="text-[#EEEEEE] text-lg">Template Selection</CardTitle>
//             </CardHeader>
//             <CardContent className="space-y-4">
//               <div className="flex items-center space-x-2">
//                 <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
//                   <SelectTrigger className="flex-1 bg-[#1a2b42] border-[#EEEEEE] text-[#EEEEEE]">
//                     <SelectValue placeholder="Select a template" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     {templates.map((template) => (
//                       <SelectItem key={template} value={template}>
//                         {template}
//                       </SelectItem>
//                     ))}
//                   </SelectContent>
//                 </Select>
//                 <Button
//                   type="button"
//                   onClick={() => refetchTemplates()}
//                   className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/80 h-10 w-10 p-0"
//                   title="Refresh Templates"
//                   disabled={isLoadingTemplates}
//                 >
//                   {isLoadingTemplates ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
//                 </Button>
//               </div>

//               <div className="flex space-x-2">
//                 <Button
//                   onClick={handleLoadTemplate}
//                   disabled={!selectedTemplate || loadTemplateMutation.isPending}
//                   className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 flex-1"
//                 >
//                   {loadTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Loading...
//                     </>
//                   ) : (
//                     "Load Template"
//                   )}
//                 </Button>

//                 <Button
//                   onClick={handleDeployTemplate}
//                   disabled={!loadedTemplate || deployTemplateMutation.isPending || logStatus === 'running'}
//                   className="bg-green-600 text-white hover:bg-green-600/80 flex-1"
//                 >
//                   {deployTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Starting...
//                     </>
//                   ) : (
//                     <>
//                       <Play className="mr-2 h-4 w-4" />
//                       Deploy
//                     </>
//                   )}
//                 </Button>
//               </div>

//               {loadedTemplate && (
//                 <div className="text-sm text-[#EEEEEE] bg-[#2A4759] p-3 rounded">
//                   <p><strong>FT Number:</strong> {loadedTemplate.metadata.ft_number}</p>
//                   <p><strong>Description:</strong> {loadedTemplate.metadata.description}</p>
//                   <p><strong>Total Steps:</strong> {loadedTemplate.metadata.total_steps}</p>
//                 </div>
//               )}

//               {/* Progress Bar Section */}
//               {loadedTemplate && (logStatus === 'running' || logStatus === 'success' || logStatus === 'failed') && (
//                 <div className="bg-[#2A4759] p-4 rounded-lg">
//                   <div className="flex items-center justify-between mb-2">
//                     <span className="text-sm font-medium text-[#EEEEEE]">
//                       Deployment Progress
//                     </span>
//                     <span className="text-xs text-gray-400">
//                       {getCurrentDeploymentStatus(deploymentLogs, Math.round((progress / 100) * (loadedTemplate?.metadata.total_steps || 0)), loadedTemplate?.metadata.total_steps || 0)}
//                     </span>
//                   </div>
//                   <ProgressBar
//                     progress={progress}
//                     status={logStatus}
//                     className="mt-2"
//                   />
//                 </div>
//               )}
//             </CardContent>
//           </Card>

//           {/* Deployment Flow moved to left column */}
//           {loadedTemplate && (
//             <Card className="bg-[#1a2b42]">
//               <CardHeader>
//                 <CardTitle className="text-[#EEEEEE] text-lg">Deployment Flow</CardTitle>
//               </CardHeader>
//               <CardContent>
//                 <TemplateFlowchart template={loadedTemplate} />
//               </CardContent>
//             </Card>
//           )}
//         </div>

//         {/* Right Column - Logs (Full Height) */}
//         <div className="space-y-4">
//           <div className={`${loadedTemplate ? 'h-full' : ''}`}>
//             <LogDisplay
//               logs={deploymentLogs}
//               height={loadedTemplate ? "calc(100vh - 250px)" : "400px"}
//               title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
//               status={logStatus}
//             />
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default DeployTemplate;

//   return (
//     <div className="space-y-6">
//       <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>

//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//         <div className="space-y-4">
//           <Card className="bg-[#1a2b42]">
//             <CardHeader>
//               <CardTitle className="text-[#EEEEEE] text-lg">Template Selection</CardTitle>
//             </CardHeader>
//             <CardContent className="space-y-4">
//               <div className="flex items-center space-x-2">
//                 <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
//                   <SelectTrigger className="flex-1 bg-[#1a2b42] border-[#EEEEEE] text-[#EEEEEE]">
//                     <SelectValue placeholder="Select a template" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     {templates.map((template) => (
//                       <SelectItem key={template} value={template}>
//                         {template}
//                       </SelectItem>
//                     ))}
//                   </SelectContent>
//                 </Select>
//                 <Button
//                   type="button"
//                   onClick={() => refetchTemplates()}
//                   className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/80 h-10 w-10 p-0"
//                   title="Refresh Templates"
//                   disabled={isLoadingTemplates}
//                 >
//                   {isLoadingTemplates ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
//                 </Button>
//               </div>

//               <div className="flex space-x-2">
//                 <Button
//                   onClick={handleLoadTemplate}
//                   disabled={!selectedTemplate || loadTemplateMutation.isPending}
//                   className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 flex-1"
//                 >
//                   {loadTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Loading...
//                     </>
//                   ) : (
//                     "Load Template"
//                   )}
//                 </Button>

//                 <Button
//                   onClick={handleDeployTemplate}
//                   disabled={!loadedTemplate || deployTemplateMutation.isPending || logStatus === 'running'}
//                   className="bg-green-600 text-white hover:bg-green-600/80 flex-1"
//                 >
//                   {deployTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Starting...
//                     </>
//                   ) : (
//                     <>
//                       <Play className="mr-2 h-4 w-4" />
//                       Deploy
//                     </>
//                   )}
//                 </Button>
//               </div>

//               {loadedTemplate && (
//                 <div className="text-sm text-[#EEEEEE] bg-[#2A4759] p-3 rounded">
//                   <p><strong>FT Number:</strong> {loadedTemplate.metadata.ft_number}</p>
//                   <p><strong>Description:</strong> {loadedTemplate.metadata.description}</p>
//                   <p><strong>Total Steps:</strong> {loadedTemplate.metadata.total_steps}</p>
//                 </div>
//               )}

//               {/* Progress Bar Section */}
//               {loadedTemplate && (logStatus === 'running' || logStatus === 'success' || logStatus === 'failed') && (
//                 <div className="bg-[#2A4759] p-4 rounded-lg">
//                   <div className="flex items-center justify-between mb-2">
//                     <span className="text-sm font-medium text-[#EEEEEE]">
//                       Deployment Progress
//                     </span>
//                     <span className="text-xs text-gray-400">
//                       {getCurrentDeploymentStatus(deploymentLogs, Math.round((progress / 100) * (loadedTemplate?.metadata.total_steps || 0)), loadedTemplate?.metadata.total_steps || 0)}
//                     </span>
//                   </div>
//                   <ProgressBar
//                     progress={progress}
//                     status={logStatus}
//                     className="mt-2"
//                   />
//                 </div>
//               )}
//             </CardContent>
//           </Card>
//         </div>

//         <div className="space-y-4">
//           <LogDisplay
//             logs={deploymentLogs}
//             height="400px"
//             title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
//             status={logStatus}
//           />
//         </div>
//       </div>

//       {loadedTemplate && (
//         <Card className="bg-[#1a2b42]">
//           <CardHeader>
//             <CardTitle className="text-[#EEEEEE] text-lg">Deployment Flow</CardTitle>
//           </CardHeader>
//           <CardContent>
//             <TemplateFlowchart template={loadedTemplate} />
//           </CardContent>
//         </Card>
//       )}
//     </div>
//   );
// };

// export default DeployTemplate;

// import React, { useState, useEffect } from 'react';
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// import { useToast } from "@/hooks/use-toast";
// import { RefreshCw, Play, Loader2 } from 'lucide-react';
// import LogDisplay from '@/components/LogDisplay';
// import TemplateFlowchart from '@/components/TemplateFlowchart';



// interface DeploymentTemplate {
//   metadata: {
//     ft_number: string;
//     generated_at: string;
//     description: string;
//     total_steps?: number;
//   };
//   steps: Array<{
//     type: string;
//     description: string;
//     order: number;
//     ftNumber?: string;
//     files?: string[];
//     targetVMs?: string[];
//     targetUser?: string;
//     targetPath?: string;
//     service?: string;
//     operation?: string;
//     playbook?: string;
//     helmDeploymentType?: string;
//     dbConnection?: string;
//     dbUser?: string;
//     dbPassword?: string;
//     [key: string]: any;
//   }>;
//   dependencies: Array<{
//     step: number;
//     depends_on: number[];
//     parallel: boolean;
//   }>;
// }

// const DeployTemplate: React.FC = () => {
//   const { toast } = useToast();
//   const queryClient = useQueryClient();
//   const [selectedTemplate, setSelectedTemplate] = useState<string>('');
//   const [loadedTemplate, setLoadedTemplate] = useState<DeploymentTemplate | null>(null);
//   const [deploymentLogs, setDeploymentLogs] = useState<string[]>([]);
//   const [deploymentId, setDeploymentId] = useState<string | null>(null);
//   const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
//   const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);
//   const [isPolling, setIsPolling] = useState<boolean>(false);
//   const [progress, setProgress] = useState<number>(0);

//   useEffect(() => {
//   if (!deploymentId || !loadedTemplate) return;

//   const totalSteps = loadedTemplate.metadata.total_steps || 0;

//   const cleanup = pollLogs(
//     deploymentId,
//     setDeploymentLogs,
//     setLogStatus,
//     totalSteps
//   );

//   return () => {
//     if (cleanup) cleanup();
//   };
// }, [deploymentId, loadedTemplate]);

//   const {
//     data: templates = [],
//     refetch: refetchTemplates,
//     isLoading: isLoadingTemplates
//   } = useQuery({
//     queryKey: ['deploy-templates'],
//     queryFn: async () => {
//       const response = await fetch('/api/deploy/templates');
//       if (!response.ok) throw new Error('Failed to fetch templates');
//       const data = await response.json();
//       return data.templates as string[];
//     },
//     staleTime: 300000,
//     refetchOnWindowFocus: false,
//   });

//   const loadTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log("Loading template:", templateName);
//       const response = await fetch(`/api/deploy/templates/${templateName}`);
//       if (!response.ok) throw new Error('Failed to load template');
//       const data = await response.json();
//       return data.template as DeploymentTemplate;
//     },
//     onSuccess: (template) => {
//       setLoadedTemplate(template);
//       toast({
//         title: "Template Loaded",
//         description: `Template ${template.metadata.ft_number} loaded successfully`,
//       });
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to load template",
//         variant: "destructive",
//       });
//     },
//   });

//   const deployTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Deploying template: ${templateName}`);
//       const response = await fetch('/api/deploy/templates/execute', {
//         method: 'POST',
//         headers: { 
//           'Content-Type': 'application/json',
//          },
//         body: JSON.stringify({ template_name: templateName }),
//       });
      
//       if (!response.ok) throw new Error('Failed to start template deployment');
//       const data = await response.json();
//       console.log("Template deployment started:", data);
//       return data;
//     },
//     onSuccess: (data) => {
//       setCurrentDeploymentId(data.deployment_id);
//       setLogStatus('running');
//       setDeploymentLogs([]);
//       setProgress(0);
//       toast({
//         title: "Deployment Started",
//         description: `Template deployment started with ID: ${data.deployment_id}`,
//       });
//       pollLogs(data.deployment_id, setDeploymentLogs, setLogStatus, loadedTemplate?.metadata.total_steps || 0);
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to start template deployment",
//         variant: "destructive",
//       });
//     },
//   });

//   const pollLogs = (
//   id: string,
//   logSetter: React.Dispatch<React.SetStateAction<string[]>>,
//   statusSetter: React.Dispatch<React.SetStateAction<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>>,
//   totalSteps: number
// ) => {
//   if (!id || !totalSteps) return;
//   logSetter([]);
//   statusSetter("running");
//   setIsPolling(true);
//   let pollCount = 0;
//   let lastLogLength = 0;
//   let completedSteps = 0;
//   let hasActualFailure = false;
//   let isDeploymentComplete = false;
  
//   const pollInterval = setInterval(async () => {
//     try {
//       const response = await fetch(`/api/deploy/${id}/logs`);
//       if (!response.ok) {
//         throw new Error("Failed to fetch logs");
//       }
//       const data = await response.json();
//       if (data.logs) {
//         logSetter(data.logs);
        
//         // Track failures but don't immediately set status
//         hasActualFailure = checkForActualFailures(data.logs);
        
//         // Update completed steps
//         completedSteps = countCompletedSteps(data.logs);
        
//         // Check if deployment has completed (either success or failure)
//         if (completedSteps >= totalSteps || hasActualFailure) {
//           isDeploymentComplete = true;
          
//           // If all steps completed successfully
//           if (completedSteps >= totalSteps && checkFinalSuccess(data.logs)) {
//             console.log("All steps completed successfully");
//             statusSetter("success");
//             clearInterval(pollInterval);
//             setIsPolling(false);
//             return;
//           }
          
//           // If we have a failure and deployment has stopped
//           if (hasActualFailure && !checkIfActivelyRunning(data.logs)) {
//             console.log("Deployment failed due to step failure");
//             statusSetter("failed");
//             clearInterval(pollInterval);
//             setIsPolling(false);
//             return;
//           }
//         }
        
//         // Check for active execution
//         const isActivelyRunning = checkIfActivelyRunning(data.logs);
//         if (isActivelyRunning) {
//           console.log("Deployment is actively running");
//           return; // Keep status as "running"
//         }
        
//         // Check for unchanged logs (potential stall)
//         if (data.logs.length === lastLogLength) {
//           pollCount++;
          
//           // Be more patient during step transitions
//           const waitThreshold = completedSteps < totalSteps ? 30 : 10;
          
//           if (pollCount >= waitThreshold) {
//             console.log(`Logs unchanged for ${waitThreshold} seconds. Completed: ${completedSteps}/${totalSteps}`);
            
//             if (isDeploymentComplete) {
//               // If we thought it was complete but no success indicators
//               if (completedSteps >= totalSteps) {
//                 statusSetter("failed");
//               } else {
//                 statusSetter("failed");
//               }
//             } else {
//               // Not all steps completed - continue waiting unless stalled too long
//               if (pollCount >= 60) {
//                 console.log("Deployment appears genuinely stalled");
//                 statusSetter("failed");
//               }
//             }
            
//             clearInterval(pollInterval);
//             setIsPolling(false);
//             return;
//           }
//         } else {
//           pollCount = 0;
//           lastLogLength = data.logs.length;
//         }
//       }
      
//       // Timeout after 10 minutes
//       if (pollCount > 600) {
//         console.log("Operation timed out after 10 minutes");
//         const finalCheck = completedSteps >= totalSteps && 
//                           (checkFinalSuccess(data.logs) || checkRecentStepCompletion(data.logs));
//         statusSetter(finalCheck ? "success" : "failed");
//         clearInterval(pollInterval);
//         setIsPolling(false);
//       }
//     } catch (error) {
//       console.error("Error fetching logs:", error);
//       pollCount += 5;
//       if (pollCount > 30) {
//         console.log("Too many polling errors - marking as failed");
//         statusSetter("failed");
//         clearInterval(pollInterval);
//         setIsPolling(false);
//       }
//     }
//   }, 1000);
  
//   return () => {
//     clearInterval(pollInterval);
//     setIsPolling(false);
//   };
// };


// // Helper function to check for actual deployment failures
// const checkForActualFailures = (logs: string[]): boolean => {
//   const failurePatterns = [
//     /FAILED - RETRYING:/i,
//     /fatal:/i,
//     /^error:/i, // Only lines that start with "error:", not containing "error"
//     /deployment failed/i,
//     /step \d+ failed/i,
//     /unreachable=[1-9]/i, // Unreachable hosts (not unreachable=0)
//     /failed=[1-9]/i, // Actual failed tasks (not failed=0)
//     /ansible.*failed.*[^=][1-9]/i // Ansible failures that are not "failed=0"
//   ];

//   // Check last 20 lines for failure patterns, excluding PLAY RECAP success lines
//   const recentLogs = logs.slice(-20);
  
//   return recentLogs.some(line => {
//     // Skip PLAY RECAP lines with failed=0 and unreachable=0 (these indicate success)
//     if (line.includes('PLAY RECAP') && (line.includes('failed=0') || line.includes('unreachable=0'))) {
//       return false;
//     }
    
//     // Skip SUCCESS messages
//     if (line.includes('SUCCESS:') || line.includes('completed successfully')) {
//       return false;
//     }
    
//     return failurePatterns.some(pattern => pattern.test(line));
//   });
// };

// // Helper function to count completed steps more accurately
// const countCompletedSteps = (logs: string[]): number => {
//   const processedSteps = new Set<number>();
  
//   // Only count explicit step completion messages, not intermediate success messages
//   logs.forEach(line => {
//     // Match exact patterns for step completion
//     const stepCompletionPatterns = [
//       /^Step (\d+) completed successfully$/i,
//       /^=== .* Step (\d+) Completed Successfully ===$/i,
//       /^--- Step (\d+) succeeded ---$/i
//     ];
    
//     stepCompletionPatterns.forEach(pattern => {
//       const match = line.match(pattern);
//       if (match) {
//         const stepNum = parseInt(match[1]);
//         if (stepNum && stepNum > 0) {
//           processedSteps.add(stepNum);
//         }
//       }
//     });
//   });

//   return processedSteps.size;
// };

// // Helper function to check if the final deployment is successful
// const checkFinalSuccess = (logs: string[]): boolean => {
//   const successPatterns = [
//     /All files deployed successfully/i,
//     /Template deployment completed successfully/i,
//     /All steps completed successfully/i,
//     /Deployment finished successfully/i,
//     /SUCCESS: .* completed successfully/i
//   ];

//   // Check the last 30 lines for final success indicators
//   const recentLogs = logs.slice(-30);
  
//   return recentLogs.some(line => 
//     successPatterns.some(pattern => pattern.test(line))
//   );
// };

// // Helper function to check if a step was recently completed
// const checkRecentStepCompletion = (logs: string[]): boolean => {
//   const recentLogs = logs.slice(-20); // Check last 20 lines
  
//   const recentCompletionPatterns = [
//     /Step \d+ completed successfully/i,
//     /=== .* Step \d+ Completed Successfully ===/i,
//     /SUCCESS: .* completed successfully/i,
//     /PLAY RECAP.*failed=0/i // Ansible success recap
//   ];
  
//   return recentLogs.some(line => 
//     recentCompletionPatterns.some(pattern => pattern.test(line))
//   );
// };

// // Helper function to check if deployment is actively running
// const checkIfActivelyRunning = (logs: string[]): boolean => {
//   const recentLogs = logs.slice(-15); // Check last 15 lines
  
//   const activePatterns = [
//     /=== Starting Step \d+:/i,
//     /=== Executing File Deployment Step \d+ ===/i,
//     /PLAY \[/i,
//     /TASK \[/i,
//     /changed:/i,
//     /ok:/i,
//     /Executing: ansible-playbook/i,
//     /Using .* as config file/i,
//     /PLAY RECAP \*+/i, // Ansible is running a playbook
//     /ansible-playbook -i/i,
//     /Created inventory file/i
//   ];
  
//   const isActive = recentLogs.some(line => 
//     activePatterns.some(pattern => pattern.test(line))
//   );
  
//   // Additional check: if we see step completion but not the final step, it's still active
//   const hasRecentStepCompletion = recentLogs.some(line => 
//     /Step \d+ completed successfully/i.test(line)
//   );
  
//   const hasFinalSuccess = recentLogs.some(line => 
//     /=== Template Deployment SUCCESS ===/i.test(line) ||
//     /All steps completed successfully/i.test(line)
//   );
  
//   return isActive || (hasRecentStepCompletion && !hasFinalSuccess);
// };

// // Additional helper to get current deployment status for UI display
// const getCurrentDeploymentStatus = (logs: string[], completedSteps: number, totalSteps: number): string => {
//   if (logs.length === 0) return "Initializing deployment...";
  
//   const lastFewLines = logs.slice(-10);
  
//   // Look for current step indicators
//   for (const line of lastFewLines.reverse()) {
//     if (line.includes("=== Starting Step")) {
//       const stepMatch = line.match(/Step (\d+)/);
//       if (stepMatch) {
//         return `Executing Step ${stepMatch[1]} of ${totalSteps}...`;
//       }
//     }
//     if (line.includes("=== Executing")) {
//       return "Executing deployment step...";
//     }
//   }
  
//   return `Progress: ${completedSteps}/${totalSteps} steps completed`;
// };


//   const handleLoadTemplate = () => {
//     if (selectedTemplate) {
//       loadTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   const handleDeployTemplate = () => {
//   if (selectedTemplate && loadedTemplate) {
//     setDeploymentLogs([]);
//     deployTemplateMutation.mutate(selectedTemplate); 
//   }
// };


//   return (
//     <div className="space-y-6">
//       <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>

//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//         <div className="space-y-4">
//           <Card className="bg-[#1a2b42]">
//             <CardHeader>
//               <CardTitle className="text-[#EEEEEE] text-lg">Template Selection</CardTitle>
//             </CardHeader>
//             <CardContent className="space-y-4">
//               <div className="flex items-center space-x-2">
//                 <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
//                   <SelectTrigger className="flex-1 bg-[#1a2b42] border-[#EEEEEE] text-[#EEEEEE]">
//                     <SelectValue placeholder="Select a template" />
//                   </SelectTrigger>
//                   <SelectContent>
//                     {templates.map((template) => (
//                       <SelectItem key={template} value={template}>
//                         {template}
//                       </SelectItem>
//                     ))}
//                   </SelectContent>
//                 </Select>
//                 <Button
//                   type="button"
//                   onClick={() => refetchTemplates()}
//                   className="bg-[#00a7e1] text-white hover:bg-[#00a7e1]/80 h-10 w-10 p-0"
//                   title="Refresh Templates"
//                   disabled={isLoadingTemplates}
//                 >
//                   {isLoadingTemplates ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
//                 </Button>
//               </div>

//               <div className="flex space-x-2">
//                 <Button
//                   onClick={handleLoadTemplate}
//                   disabled={!selectedTemplate || loadTemplateMutation.isPending}
//                   className="bg-[#00a7e1] text-[#EEEEEE] hover:bg-[#00a7e1]/80 flex-1"
//                 >
//                   {loadTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Loading...
//                     </>
//                   ) : (
//                     "Load Template"
//                   )}
//                 </Button>

//                 <Button
//                   onClick={handleDeployTemplate}
//                   disabled={!loadedTemplate || deployTemplateMutation.isPending || logStatus === 'running'}
//                   className="bg-green-600 text-white hover:bg-green-600/80 flex-1"
//                 >
//                   {deployTemplateMutation.isPending ? (
//                     <>
//                       <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                       Starting...
//                     </>
//                   ) : (
//                     <>
//                       <Play className="mr-2 h-4 w-4" />
//                       Deploy
//                     </>
//                   )}
//                 </Button>
//               </div>

//               {loadedTemplate && (
//                 <div className="text-sm text-[#EEEEEE] bg-[#2A4759] p-3 rounded">
//                   <p><strong>FT Number:</strong> {loadedTemplate.metadata.ft_number}</p>
//                   <p><strong>Description:</strong> {loadedTemplate.metadata.description}</p>
//                   <p><strong>Total Steps:</strong> {loadedTemplate.metadata.total_steps}</p>
//                 </div>
//               )}
//             </CardContent>
//           </Card>
//         </div>

//         <div className="space-y-4">
//           <LogDisplay
//             logs={deploymentLogs}
//             height="400px"
//             title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
//             status={logStatus}
//           />
//         </div>
//       </div>

//       {loadedTemplate && (
//         <Card className="bg-[#1a2b42]">
//           <CardHeader>
//             <CardTitle className="text-[#EEEEEE] text-lg">Deployment Flow</CardTitle>
//           </CardHeader>
//           <CardContent>
//             <TemplateFlowchart template={loadedTemplate} />
//           </CardContent>
//         </Card>
//       )}
//     </div>
//   );
// };

// export default DeployTemplate;