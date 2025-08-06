import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { GitBranch, GitPull, GitPush, GitCommit, Plus, Trash2, RefreshCw } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const GitOperations = ({ currentBranch, setCurrentBranch, repoStatus, setRepoStatus }) => {
  const [branches, setBranches] = useState(['main', 'develop', 'feature/test']);
  const [repoUrl, setRepoUrl] = useState('');
  const [commitMessage, setCommitMessage] = useState('');
  const [newBranchName, setNewBranchName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [repositories, setRepositories] = useState([]);
  const { toast } = useToast();

  useEffect(() => {
    const fetchRepositories = async () => {
      try {
        const response = await fetch('/app/inventory/inventory.json');
        const data = await response.json();
        setRepositories(data.git_repositories);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to fetch repositories",
          variant: "destructive"
        });
      }
    };

    fetchRepositories();
  }, []);

  const handleCloneRepo = async () => {
    if (!repoUrl) {
      toast({
        title: "Error",
        description: "Please select a repository",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repoUrl })
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Repository cloned successfully"
        });
        setRepoStatus(prev => ({ ...prev, initialized: true }));
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to clone repository",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheckoutBranch = async (branch) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/git/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch })
      });

      if (response.ok) {
        setCurrentBranch(branch);
        toast({
          title: "Success",
          description: `Switched to branch: ${branch}`
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to checkout branch",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePull = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/git/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch: currentBranch })
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Pulled latest changes"
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to pull changes",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCommitAndPush = async () => {
    if (!commitMessage) {
      toast({
        title: "Error",
        description: "Please enter a commit message",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/commit-push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: commitMessage,
          branch: currentBranch
        })
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: "Changes committed and pushed"
        });
        setCommitMessage('');
        setRepoStatus(prev => ({ ...prev, hasChanges: false, ahead: 0 }));
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to commit and push",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBranch = async () => {
    if (!newBranchName) {
      toast({
        title: "Error",
        description: "Please enter a branch name",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/create-branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branchName: newBranchName })
      });

      if (response.ok) {
        setBranches(prev => [...prev, newBranchName]);
        setNewBranchName('');
        toast({
          title: "Success",
          description: `Branch '${newBranchName}' created`
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create branch",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteBranch = async (branchToDelete) => {
    if (branchToDelete === currentBranch) {
      toast({
        title: "Error",
        description: "Cannot delete current branch",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/delete-branch', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branchName: branchToDelete })
      });

      if (response.ok) {
        setBranches(prev => prev.filter(b => b !== branchToDelete));
        toast({
          title: "Success",
          description: `Branch '${branchToDelete}' deleted`
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete branch",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
        <CardHeader>
          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Repository Setup
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
              Repository URL
            </label>
            <Select onValueChange={setRepoUrl}>
              <SelectTrigger className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]">
                <SelectValue placeholder="Select a repository" />
              </SelectTrigger>
              <SelectContent className="bg-[#2A4759] border-[#007ea7]/30">
                {repositories.map(repo => (
                  <SelectItem key={repo.url} value={repo.url} className="text-[#EEEEEE]">
                    {repo.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button 
            onClick={handleCloneRepo} 
            disabled={isLoading || repoStatus.initialized}
            className="w-full bg-[#007ea7] hover:bg-[#005f82]"
          >
            {repoStatus.initialized ? 'Repository Initialized' : 'Clone Repository'}
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
        <CardHeader>
          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Branch Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
              Current Branch
            </label>
            <Select value={currentBranch} onValueChange={handleCheckoutBranch}>
              <SelectTrigger className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#2A4759] border-[#007ea7]/30">
                {branches.map(branch => (
                  <SelectItem key={branch} value={branch} className="text-[#EEEEEE]">
                    {branch}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex gap-2">
            <Input
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              placeholder="new-branch-name"
              className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
            />
            <Button onClick={handleCreateBranch} disabled={isLoading} size="sm">
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-[#EEEEEE]">
              Available Branches
            </label>
            <div className="flex flex-wrap gap-2">
              {branches.map(branch => (
                <div key={branch} className="flex items-center gap-1">
                  <Badge 
                    variant={branch === currentBranch ? "default" : "secondary"}
                    className={branch === currentBranch ? "bg-[#007ea7]" : ""}
                  >
                    {branch}
                  </Badge>
                  {branch !== currentBranch && branch !== 'main' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteBranch(branch)}
                      className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
        <CardHeader>
          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
            <GitPull className="h-5 w-5" />
            Pull Changes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Button 
            onClick={handlePull} 
            disabled={isLoading || !repoStatus.initialized}
            className="w-full bg-[#007ea7] hover:bg-[#005f82]"
          >
            <GitPull className="h-4 w-4 mr-2" />
            Pull Latest Changes
          </Button>
          {repoStatus.behind > 0 && (
            <p className="text-sm text-yellow-400 mt-2">
              Your branch is {repoStatus.behind} commits behind
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
        <CardHeader>
          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
            <GitCommit className="h-5 w-5" />
            Commit & Push
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
              Commit Message
            </label>
            <Textarea
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="Enter your commit message..."
              className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
            />
          </div>
          <Button 
            onClick={handleCommitAndPush} 
            disabled={isLoading || !repoStatus.initialized || !commitMessage}
            className="w-full bg-[#007ea7] hover:bg-[#005f82]"
          >
            <GitPush className="h-4 w-4 mr-2" />
            Commit & Push
          </Button>
          {repoStatus.hasChanges && (
            <p className="text-sm text-yellow-400">
              You have uncommitted changes
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default GitOperations;
// import React, { useState, useEffect } from 'react';
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Textarea } from "@/components/ui/textarea";
// import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// import { Badge } from "@/components/ui/badge";
// import { GitBranch, GitPull, GitPush, GitCommit, Plus, Trash2, RefreshCw } from "lucide-react";
// import { useToast } from "@/components/ui/use-toast";

// const GitOperations = ({ currentBranch, setCurrentBranch, repoStatus, setRepoStatus }) => {
//   const [branches, setBranches] = useState(['main', 'develop', 'feature/test']);
//   const [repoUrl, setRepoUrl] = useState('');
//   const [commitMessage, setCommitMessage] = useState('');
//   const [newBranchName, setNewBranchName] = useState('');
//   const [isLoading, setIsLoading] = useState(false);
//   const { toast } = useToast();

//   const handleCloneRepo = async () => {
//     if (!repoUrl) {
//       toast({
//         title: "Error",
//         description: "Please enter a repository URL",
//         variant: "destructive"
//       });
//       return;
//     }

//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/clone', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ repoUrl })
//       });

//       if (response.ok) {
//         toast({
//           title: "Success",
//           description: "Repository cloned successfully"
//         });
//         setRepoStatus(prev => ({ ...prev, initialized: true }));
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to clone repository",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleCheckoutBranch = async (branch) => {
//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/checkout', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ branch })
//       });

//       if (response.ok) {
//         setCurrentBranch(branch);
//         toast({
//           title: "Success",
//           description: `Switched to branch: ${branch}`
//         });
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to checkout branch",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handlePull = async () => {
//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/pull', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ branch: currentBranch })
//       });

//       if (response.ok) {
//         toast({
//           title: "Success",
//           description: "Pulled latest changes"
//         });
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to pull changes",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleCommitAndPush = async () => {
//     if (!commitMessage) {
//       toast({
//         title: "Error",
//         description: "Please enter a commit message",
//         variant: "destructive"
//       });
//       return;
//     }

//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/commit-push', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ 
//           message: commitMessage,
//           branch: currentBranch
//         })
//       });

//       if (response.ok) {
//         toast({
//           title: "Success",
//           description: "Changes committed and pushed"
//         });
//         setCommitMessage('');
//         setRepoStatus(prev => ({ ...prev, hasChanges: false, ahead: 0 }));
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to commit and push",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleCreateBranch = async () => {
//     if (!newBranchName) {
//       toast({
//         title: "Error",
//         description: "Please enter a branch name",
//         variant: "destructive"
//       });
//       return;
//     }

//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/create-branch', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ branchName: newBranchName })
//       });

//       if (response.ok) {
//         setBranches(prev => [...prev, newBranchName]);
//         setNewBranchName('');
//         toast({
//           title: "Success",
//           description: `Branch '${newBranchName}' created`
//         });
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to create branch",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const handleDeleteBranch = async (branchToDelete) => {
//     if (branchToDelete === currentBranch) {
//       toast({
//         title: "Error",
//         description: "Cannot delete current branch",
//         variant: "destructive"
//       });
//       return;
//     }

//     setIsLoading(true);
//     try {
//       const response = await fetch('/api/git/delete-branch', {
//         method: 'DELETE',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ branchName: branchToDelete })
//       });

//       if (response.ok) {
//         setBranches(prev => prev.filter(b => b !== branchToDelete));
//         toast({
//           title: "Success",
//           description: `Branch '${branchToDelete}' deleted`
//         });
//       }
//     } catch (error) {
//       toast({
//         title: "Error",
//         description: "Failed to delete branch",
//         variant: "destructive"
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   return (
//     <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
//       <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
//         <CardHeader>
//           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//             <GitBranch className="h-5 w-5" />
//             Repository Setup
//           </CardTitle>
//         </CardHeader>
//         <CardContent className="space-y-4">
//           <div>
//             <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
//               Repository URL
//             </label>
//             <Input
//               value={repoUrl}
//               onChange={(e) => setRepoUrl(e.target.value)}
//               placeholder="https://github.com/user/repo.git"
//               className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
//             />
//           </div>
//           <Button 
//             onClick={handleCloneRepo} 
//             disabled={isLoading || repoStatus.initialized}
//             className="w-full bg-[#007ea7] hover:bg-[#005f82]"
//           >
//             {repoStatus.initialized ? 'Repository Initialized' : 'Clone Repository'}
//           </Button>
//         </CardContent>
//       </Card>

//       <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
//         <CardHeader>
//           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//             <GitBranch className="h-5 w-5" />
//             Branch Management
//           </CardTitle>
//         </CardHeader>
//         <CardContent className="space-y-4">
//           <div>
//             <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
//               Current Branch
//             </label>
//             <Select value={currentBranch} onValueChange={handleCheckoutBranch}>
//               <SelectTrigger className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]">
//                 <SelectValue />
//               </SelectTrigger>
//               <SelectContent className="bg-[#2A4759] border-[#007ea7]/30">
//                 {branches.map(branch => (
//                   <SelectItem key={branch} value={branch} className="text-[#EEEEEE]">
//                     {branch}
//                   </SelectItem>
//                 ))}
//               </SelectContent>
//             </Select>
//           </div>
          
//           <div className="flex gap-2">
//             <Input
//               value={newBranchName}
//               onChange={(e) => setNewBranchName(e.target.value)}
//               placeholder="new-branch-name"
//               className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
//             />
//             <Button onClick={handleCreateBranch} disabled={isLoading} size="sm">
//               <Plus className="h-4 w-4" />
//             </Button>
//           </div>

//           <div className="space-y-2">
//             <label className="block text-sm font-medium text-[#EEEEEE]">
//               Available Branches
//             </label>
//             <div className="flex flex-wrap gap-2">
//               {branches.map(branch => (
//                 <div key={branch} className="flex items-center gap-1">
//                   <Badge 
//                     variant={branch === currentBranch ? "default" : "secondary"}
//                     className={branch === currentBranch ? "bg-[#007ea7]" : ""}
//                   >
//                     {branch}
//                   </Badge>
//                   {branch !== currentBranch && branch !== 'main' && (
//                     <Button
//                       size="sm"
//                       variant="ghost"
//                       onClick={() => handleDeleteBranch(branch)}
//                       className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
//                     >
//                       <Trash2 className="h-3 w-3" />
//                     </Button>
//                   )}
//                 </div>
//               ))}
//             </div>
//           </div>
//         </CardContent>
//       </Card>

//       <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
//         <CardHeader>
//           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//             <GitPull className="h-5 w-5" />
//             Pull Changes
//           </CardTitle>
//         </CardHeader>
//         <CardContent>
//           <Button 
//             onClick={handlePull} 
//             disabled={isLoading || !repoStatus.initialized}
//             className="w-full bg-[#007ea7] hover:bg-[#005f82]"
//           >
//             <GitPull className="h-4 w-4 mr-2" />
//             Pull Latest Changes
//           </Button>
//           {repoStatus.behind > 0 && (
//             <p className="text-sm text-yellow-400 mt-2">
//               Your branch is {repoStatus.behind} commits behind
//             </p>
//           )}
//         </CardContent>
//       </Card>

//       <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
//         <CardHeader>
//           <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
//             <GitCommit className="h-5 w-5" />
//             Commit & Push
//           </CardTitle>
//         </CardHeader>
//         <CardContent className="space-y-4">
//           <div>
//             <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
//               Commit Message
//             </label>
//             <Textarea
//               value={commitMessage}
//               onChange={(e) => setCommitMessage(e.target.value)}
//               placeholder="Enter your commit message..."
//               className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
//             />
//           </div>
//           <Button 
//             onClick={handleCommitAndPush} 
//             disabled={isLoading || !repoStatus.initialized || !commitMessage}
//             className="w-full bg-[#007ea7] hover:bg-[#005f82]"
//           >
//             <GitPush className="h-4 w-4 mr-2" />
//             Commit & Push
//           </Button>
//           {repoStatus.hasChanges && (
//             <p className="text-sm text-yellow-400">
//               You have uncommitted changes
//             </p>
//           )}
//         </CardContent>
//       </Card>
//     </div>
//   );
// };

// export default GitOperations;
