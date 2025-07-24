import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, Play, Loader2 } from 'lucide-react';
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
      const response = await fetch(`/api/deploy/templates/${templateName}`);
      if (!response.ok) throw new Error('Failed to load template');
      const data = await response.json();
      return data.template as DeploymentTemplate;
    },
    onSuccess: (template) => {
      setLoadedTemplate(template);
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
      const response = await fetch('/api/deploy/templates/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_name: templateName }),
      });
      if (!response.ok) throw new Error('Failed to start template deployment');
      const data = await response.json();
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
  totalSteps: number ) => {
    if (!id || !totalSteps) return;

    logSetter([]);
    statusSetter("running");

    setIsPolling(true);
    let pollCount = 0;
    let lastLogLength = 0;
    let completedSteps = 0;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/deploy/${id}/logs`);
        if (!response.ok) {
          throw new Error("Failed to fetch logs");
        }

        const data = await response.json();
        if (data.logs) {
          logSetter(data.logs);

          const failedLog = data.logs.find((line: string) => /failed/i.test(line));
          if (failedLog) {
            statusSetter("failed");
            clearInterval(pollInterval);
            return;
          }

          completedSteps = data.logs.filter((line: string) =>
            /step\s+\d+\/\d+\s+completed/i.test(line)
          ).length;

          if (completedSteps >= totalSteps) {
            statusSetter("success");
            clearInterval(pollInterval);
            return;
          }

          if (data.logs.length === lastLogLength) {
            pollCount++;
            if (pollCount >= 5) {
              console.log("Logs unchanged — assuming success if steps match total.");
              if (completedSteps >= totalSteps) {
                statusSetter("success");
              } else {
                statusSetter("failed");
              }
              clearInterval(pollInterval);
              return;
            }
          } else {
            pollCount = 0;
            lastLogLength = data.logs.length;
          }
        }

        if (pollCount > 120) {
          console.log("Operation timed out after 2 minutes.");
          statusSetter(completedSteps >= totalSteps ? "success" : "failed");
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error("Error fetching logs:", error);
        pollCount += 5;
        if (pollCount > 20) {
          statusSetter("failed");
          clearInterval(pollInterval);
        }
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  };


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

//   const pollInterval = setInterval(async () => {
//     try {
//       const response = await fetch(`/api/deploy/${id}/logs`);
//       if (!response.ok) {
//         throw new Error("Failed to fetch logs");
//       }

//       const data = await response.json();
//       if (data.logs) {
//         logSetter(data.logs);

//         const failedLog = data.logs.find((line) => /failed/i.test(line));
//         if (failedLog) {
//           statusSetter("failed");
//           clearInterval(pollInterval);
//           return;
//         }

//         const completedSteps = data.logs.filter((line) =>
//           /step\s+\d+\/\d+\s+completed/i.test(line)
//         ).length;

//         if (completedSteps >= totalSteps) {
//           statusSetter("success");
//           clearInterval(pollInterval);
//           return;
//         }

//         if (data.logs.length === lastLogLength) {
//           pollCount++;
//           if (pollCount >= 5) {
//             console.log("Logs unchanged — assuming success if steps match total.");
//             if (completedSteps >= totalSteps) {
//               statusSetter("success");
//             } else {
//               statusSetter("failed");
//             }
//             clearInterval(pollInterval);
//             return;
//           }
//         } else {
//           pollCount = 0;
//           lastLogLength = data.logs.length;
//         }
//       }

//       if (pollCount > 120) {
//         console.log("Operation timed out after 2 minutes.");
//         statusSetter(completedSteps >= totalSteps ? "success" : "failed");
//         clearInterval(pollInterval);
//       }
//     } catch (error) {
//       console.error("Error fetching logs:", error);
//       pollCount += 5;
//       if (pollCount > 20) {
//         statusSetter("failed");
//         clearInterval(pollInterval);
//       }
//     }
//   }, 1000);

//   return () => clearInterval(pollInterval);
// };


  // const startLogPolling = (id: string) => {
  //   setIsPolling(true);
  //   let polling = true;

  //   const poll = async () => {
  //     try {
  //       const response = await fetch(`/api/deploy/${id}/logs?ts=${Date.now()}`);
  //       if (response.ok) {
  //         const data = await response.json();

  //         if (data.logs) {
  //           setDeploymentLogs((prev) => {
  //             const newLogs = data.logs.filter((log: string) => !prev.includes(log));
  //             const combined = [...prev, ...newLogs];

  //             if (loadedTemplate?.metadata.total_steps) {
  //               const totalSteps = loadedTemplate.metadata.total_steps;
  //               const completedSteps = combined.filter((line) =>
  //                 /step\s+\d+.*(completed|done|finished)/i.test(line)
  //               ).length;
  //               const percent = Math.min(Math.round((completedSteps / totalSteps) * 100), 100);
  //               setProgress(percent);
  //             }

  //             return combined;
  //           });
  //         }

  //         if (data.status) {
  //           setLogStatus(data.status);
  //           if (['success', 'failed'].includes(data.status)) {
  //             polling = true;
  //             setIsPolling(true);
  //             queryClient.invalidateQueries({ queryKey: ['deployment-history'] });
  //             return;
  //           }
  //         }
  //       }
  //     } catch (err) {
  //       console.error("Polling error:", err);
  //     }

  //     if (polling) {
  //       setTimeout(poll, 2000);
  //     }
  //   };

  //   poll();
  // };

  const handleLoadTemplate = () => {
    if (selectedTemplate) {
      loadTemplateMutation.mutate(selectedTemplate);
    }
  };

  const handleDeployTemplate = () => {
    if (selectedTemplate && loadedTemplate) {
      deployTemplateMutation.mutate(selectedTemplate);
    }
    setDeploymentLogs([]);
    deployTemplateMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <LogDisplay
            logs={deploymentLogs}
            height="400px"
            title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
            status={logStatus}
          />

          {loadedTemplate && (
            <div className="w-full bg-[#2A4759] rounded h-4 overflow-hidden">
              <div
                className="h-4 bg-[#00a7e1] transition-all duration-300 ease-in-out"
                style={{ width: `${progress}%` }}
              />
              <div className="text-sm text-right text-[#EEEEEE] mt-1">
                {progress}% Complete
              </div>
            </div>
          )}
        </div>
      </div>

      {loadedTemplate && (
        <Card className="bg-[#1a2b42]">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE] text-lg">Deployment Flow</CardTitle>
          </CardHeader>
          <CardContent>
            <TemplateFlowchart template={loadedTemplate} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DeployTemplate;



// &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
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
//   const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
//   const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);
//   const [eventSource, setEventSource] = useState<EventSource | null>(null);

//   // Fetch available templates
//   const { 
//     data: templates = [], 
//     refetch: refetchTemplates, 
//     isLoading: isLoadingTemplates 
//   } = useQuery({
//     queryKey: ['deploy-templates'],
//     queryFn: async () => {
//       console.log("Fetching available templates");
//       const response = await fetch('/api/deploy/templates');
//       if (!response.ok) {
//         throw new Error('Failed to fetch templates');
//       }
//       const data = await response.json();
//       console.log("Available templates:", data);
//       return data.templates as string[];
//     },
//     staleTime: 300000,
//     refetchOnWindowFocus: false,
//   });

//   // Load template mutation
//   const loadTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Loading template: ${templateName}`);
//       const response = await fetch(`/api/deploy/templates/${templateName}`);
//       if (!response.ok) {
//         throw new Error('Failed to load template');
//       }
//       const data = await response.json();
//       console.log("Loaded template data:", data);
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

//   // Deploy template mutation
//   const deployTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Deploying template: ${templateName}`);
//       const response = await fetch('/api/deploy/templates/execute', {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({ template_name: templateName }),
//       });
//       if (!response.ok) {
//         throw new Error('Failed to start template deployment');
//       }
//       const data = await response.json();
//       console.log("Template deployment started:", data);
//       return data;
//     },
//     onSuccess: (data) => {
//       setCurrentDeploymentId(data.deployment_id);
//       setLogStatus('running');
//       setDeploymentLogs([]);
//       toast({
//         title: "Deployment Started",
//         description: `Template deployment started with ID: ${data.deployment_id}`,
//       });
//       // Start EventSource for real-time logs
//       startLogStream(data.deployment_id);
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to start template deployment",
//         variant: "destructive",
//       });
//     },
//   });

//   // Function to start EventSource log streaming
//   const startLogStream = (id: string) => {
//     // Close existing EventSource if any
//     if (eventSource) {
//       eventSource.close();
//     }

//     console.log(`Starting EventSource for deployment: ${id}`);
    
//     // First, check if the logs endpoint exists and is ready
//     const checkEndpoint = async () => {
//       try {
//         // Try to get initial logs first
//         const response = await fetch(`/api/deploy/${id}/logs`);
        
//         if (!response.ok) {
//           throw new Error(`Logs endpoint not available: ${response.status}`);
//         }
        
//         // Get initial logs from the JSON response
//         const initialData = await response.json();
//         if (initialData.logs) {
//           setDeploymentLogs(initialData.logs);
//         }
//         if (initialData.status) {
//           setLogStatus(initialData.status);
//         }
        
//         // If deployment is already completed, don't start EventSource
//         if (initialData.status === 'success' || initialData.status === 'failed') {
//           return;
//         }
        
//         // Start EventSource for real-time updates
//         const newEventSource = new EventSource(`/api/deploy/${id}/logs`);
        
//         newEventSource.onopen = () => {
//           console.log(`EventSource connection opened for deployment: ${id}`);
//           setLogStatus('running');
//         };
        
//         newEventSource.onmessage = (event) => {
//           try {
//             const data = JSON.parse(event.data);
//             console.log(`Received log data for ${id}:`, data);
            
//             // Handle individual log messages
//             if (data.message) {
//               setDeploymentLogs(prev => [...prev, data.message]);
//             }
            
//             // Handle status updates
//             if (data.status) {
//               setLogStatus(data.status);
//               if (data.status === 'success' || data.status === 'failed') {
//                 newEventSource.close();
//                 setEventSource(null);
//                 // Refresh deployment history
//                 queryClient.invalidateQueries({ queryKey: ['deployment-history'] });
//               }
//             }
            
//             // Handle errors
//             if (data.error) {
//               console.error('SSE error:', data.error);
//               setLogStatus('failed');
//               newEventSource.close();
//               setEventSource(null);
//               toast({
//                 title: "Stream Error",
//                 description: data.error,
//                 variant: "destructive",
//               });
//             }
//           } catch (error) {
//             console.error('Error parsing log data:', error);
//           }
//         };

//         newEventSource.onerror = (error) => {
//           console.error('EventSource error:', error);
//           console.error('EventSource readyState:', newEventSource.readyState);
//           console.error('EventSource url:', newEventSource.url);
          
//           // Check the readyState to understand the error better
//           switch (newEventSource.readyState) {
//             case EventSource.CONNECTING:
//               console.log('EventSource is connecting...');
//               break;
//             case EventSource.OPEN:
//               console.log('EventSource connection is open');
//               break;
//             case EventSource.CLOSED:
//               console.log('EventSource connection is closed');
//               break;
//           }
          
//           setLogStatus('failed');
//           newEventSource.close();
//           setEventSource(null);
          
//           toast({
//             title: "Connection Error",
//             description: "Failed to connect to log stream. The deployment may still be running.",
//             variant: "destructive",
//           });
//         };

//         setEventSource(newEventSource);
        
//       } catch (error) {
//         console.error('Error checking logs endpoint:', error);
//         setLogStatus('failed');
//         toast({
//           title: "Error",
//           description: "Logs endpoint is not available. Please check if the deployment is running.",
//           variant: "destructive",
//         });
        
//         // Fallback to polling
//         startLogPolling(id);
//       }
//     };

//     // Add a small delay to ensure backend is ready
//     setTimeout(checkEndpoint, 1000);
//   };

//   // Fallback polling method if EventSource fails
//   const startLogPolling = (id: string) => {
//     let polling = true;
    
//     const pollLogs = async () => {
//       try {
//         const response = await fetch(`/api/deploy/${id}/logs`);
//         if (response.ok) {
//           const data = await response.json();
          
//           if (data.logs) {
//             setDeploymentLogs(data.logs);
//           }
          
//           if (data.status) {
//             setLogStatus(data.status);
//             if (data.status === 'success' || data.status === 'failed') {
//               polling = false;
//               queryClient.invalidateQueries({ queryKey: ['deployment-history'] });
//             }
//           }
          
//           if (polling && data.status !== 'success' && data.status !== 'failed') {
//             setTimeout(pollLogs, 2000); // Poll every 2 seconds
//           }
//         }
//       } catch (error) {
//         console.error('Error polling logs:', error);
//         if (polling) {
//           setTimeout(pollLogs, 5000); // Retry after 5 seconds
//         }
//       }
//     };
    
//     pollLogs();
//   };

//   // Cleanup EventSource on component unmount
//   useEffect(() => {
//     return () => {
//       if (eventSource) {
//         eventSource.close();
//       }
//     };
//   }, [eventSource]);

//   const handleLoadTemplate = () => {
//     if (selectedTemplate) {
//       loadTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   const handleDeployTemplate = () => {
//     if (selectedTemplate && loadedTemplate) {
//       deployTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   return (
//     <div className="space-y-6">
//       <h2 className="text-2xl font-bold text-[#EEEEEE] mb-4">Deploy Template</h2>
      
//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//         {/* Template Selection and Loading */}
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
//                   {isLoadingTemplates ? 
//                     <Loader2 className="h-4 w-4 animate-spin" /> : 
//                     <RefreshCw className="h-4 w-4" />
//                   }
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

//         {/* Live Logs */}
//         <div className="space-y-4">
//           <LogDisplay 
//             logs={deploymentLogs} 
//             height="400px" 
//             title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
//             status={logStatus}
//           />
//         </div>
//       </div>

//       {/* Template Flowchart */}
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

// &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
// above is main 

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
//   const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed' | 'completed'>('idle');
//   const [currentDeploymentId, setCurrentDeploymentId] = useState<string | null>(null);
//   const [eventSource, setEventSource] = useState<EventSource | null>(null);

//   // Fetch available templates
//   const { 
//     data: templates = [], 
//     refetch: refetchTemplates, 
//     isLoading: isLoadingTemplates 
//   } = useQuery({
//     queryKey: ['deploy-templates'],
//     queryFn: async () => {
//       console.log("Fetching available templates");
//       const response = await fetch('/api/deploy/templates');
//       if (!response.ok) {
//         throw new Error('Failed to fetch templates');
//       }
//       const data = await response.json();
//       console.log("Available templates:", data);
//       return data.templates as string[];
//     },
//     staleTime: 300000,
//     refetchOnWindowFocus: false,
//   });

//   // Load template mutation
//   const loadTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Loading template: ${templateName}`);
//       const response = await fetch(`/api/deploy/templates/${templateName}`);
//       if (!response.ok) {
//         throw new Error('Failed to load template');
//       }
//       const data = await response.json();
//       console.log("Loaded template data:", data);
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

//   // Deploy template mutation
//   const deployTemplateMutation = useMutation({
//     mutationFn: async (templateName: string) => {
//       console.log(`Deploying template: ${templateName}`);
//       const response = await fetch('/api/deploy/templates/execute', {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({ template_name: templateName }),
//       });
//       if (!response.ok) {
//         throw new Error('Failed to start template deployment');
//       }
//       const data = await response.json();
//       console.log("Template deployment started:", data);
//       return data;
//     },
//     onSuccess: (data) => {
//       setCurrentDeploymentId(data.deployment_id);
//       setLogStatus('running');
//       setDeploymentLogs([]);
//       toast({
//         title: "Deployment Started",
//         description: `Template deployment started with ID: ${data.deployment_id}`,
//       });
//       // Start EventSource for real-time logs
//       startLogStream(data.deployment_id);
//     },
//     onError: (error) => {
//       toast({
//         title: "Error",
//         description: error instanceof Error ? error.message : "Failed to start template deployment",
//         variant: "destructive",
//       });
//     },
//   });

//   // Function to start EventSource log streaming
//   const startLogStream = (deploymentId: string) => {
//     // Close existing EventSource if any
//     if (eventSource) {
//       eventSource.close();
//     }

//     console.log(`Starting EventSource for deployment: ${deploymentId}`);
//     const newEventSource = new EventSource(`/api/logs/${deploymentId}`);
    
//     newEventSource.onmessage = (event) => {
//       try {
//         const data = JSON.parse(event.data);
//         console.log(`Received log data for ${deploymentId}:`, data);
        
//         if (data.logs) {
//           setDeploymentLogs(data.logs);
//         }
        
//         if (data.status && (data.status === 'success' || data.status === 'failed')) {
//           setLogStatus(data.status);
//           newEventSource.close();
//           setEventSource(null);
//           // Refresh deployment history
//           queryClient.invalidateQueries({ queryKey: ['deployment-history'] });
//         }
//       } catch (error) {
//         console.error('Error parsing log data:', error);
//       }
//     };

//     newEventSource.onerror = (error) => {
//       console.error('EventSource error:', error);
//       setLogStatus('failed');
//       newEventSource.close();
//       setEventSource(null);
//     };

//     setEventSource(newEventSource);
//   };

//   // Cleanup EventSource on component unmount
//   useEffect(() => {
//     return () => {
//       if (eventSource) {
//         eventSource.close();
//       }
//     };
//   }, [eventSource]);

//   const handleLoadTemplate = () => {
//     if (selectedTemplate) {
//       loadTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   const handleDeployTemplate = () => {
//     if (selectedTemplate && loadedTemplate) {
//       deployTemplateMutation.mutate(selectedTemplate);
//     }
//   };

//   return (
//     <div className="space-y-6">
//       <h2 className="text-2xl font-bold text-[#F79B72] mb-4">Deploy Template</h2>
      
//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//         {/* Template Selection and Loading */}
//         <div className="space-y-4">
//           <Card className="bg-[#EEEEEE]">
//             <CardHeader>
//               <CardTitle className="text-[#F79B72] text-lg">Template Selection</CardTitle>
//             </CardHeader>
//             <CardContent className="space-y-4">
//               <div className="flex items-center space-x-2">
//                 <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
//                   <SelectTrigger className="flex-1 bg-[#EEEEEE] border-[#2A4759] text-[#2A4759]">
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
//                   className="bg-[#2A4759] text-white hover:bg-[#2A4759]/80 h-10 w-10 p-0"
//                   title="Refresh Templates"
//                   disabled={isLoadingTemplates}
//                 >
//                   {isLoadingTemplates ? 
//                     <Loader2 className="h-4 w-4 animate-spin" /> : 
//                     <RefreshCw className="h-4 w-4" />
//                   }
//                 </Button>
//               </div>
              
//               <div className="flex space-x-2">
//                 <Button
//                   onClick={handleLoadTemplate}
//                   disabled={!selectedTemplate || loadTemplateMutation.isPending}
//                   className="bg-[#F79B72] text-[#2A4759] hover:bg-[#F79B72]/80 flex-1"
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
//                 <div className="text-sm text-[#2A4759] bg-green-50 p-3 rounded">
//                   <p><strong>FT Number:</strong> {loadedTemplate.metadata.ft_number}</p>
//                   <p><strong>Description:</strong> {loadedTemplate.metadata.description}</p>
//                   <p><strong>Total Steps:</strong> {loadedTemplate.metadata.total_steps}</p>
//                 </div>
//               )}
//             </CardContent>
//           </Card>
//         </div>

//         {/* Live Logs */}
//         <div className="space-y-4">
//           <LogDisplay 
//             logs={deploymentLogs} 
//             height="400px" 
//             title={`Template Deployment Logs${currentDeploymentId ? ` - ${currentDeploymentId}` : ''}`}
//             status={logStatus}
//           />
//         </div>
//       </div>

//       {/* Template Flowchart */}
//       {loadedTemplate && (
//         <Card className="bg-[#EEEEEE]">
//           <CardHeader>
//             <CardTitle className="text-[#F79B72] text-lg">Deployment Flow</CardTitle>
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
