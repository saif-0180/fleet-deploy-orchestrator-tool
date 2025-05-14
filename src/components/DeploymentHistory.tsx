
import { useState } from "react";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { DeploymentLogs } from "./DeploymentLogs";

// Mock deployment history data
const mockDeployments = [
  {
    id: "dep-001",
    ftId: "ft-001",
    ftName: "FT Alpha",
    timestamp: "2025-05-14T10:30:00Z",
    status: "success",
    files: ["config/app.config.json", "src/modules/core/main.py"],
    targets: ["web-server-01", "app-server-01"],
    user: "admin",
    logs: [
      "[2025-05-14T10:30:00Z] Deployment started for FT: ft-001",
      "[2025-05-14T10:30:15Z] Connecting to target VMs...",
      "[2025-05-14T10:30:30Z] Preparing files for deployment...",
      "[2025-05-14T10:30:45Z] Running ansible playbook...",
      "[2025-05-14T10:31:00Z] Copying files to target VMs...",
      "<span class=\"ansi-green-fg\">[2025-05-14T10:31:15Z] ✓ Successfully deployed to web-server-01</span>",
      "<span class=\"ansi-green-fg\">[2025-05-14T10:31:30Z] ✓ Successfully deployed to app-server-01</span>",
      "<span class=\"ansi-bright-green-fg\">[2025-05-14T10:31:45Z] ✓ Deployment completed successfully!</span>"
    ]
  },
  {
    id: "dep-002",
    ftId: "ft-002",
    ftName: "FT Beta",
    timestamp: "2025-05-13T15:45:00Z",
    status: "failed",
    files: ["auth/login.py", "auth/register.py"],
    targets: ["web-server-02"],
    user: "admin",
    logs: [
      "[2025-05-13T15:45:00Z] Deployment started for FT: ft-002",
      "[2025-05-13T15:45:15Z] Connecting to target VMs...",
      "[2025-05-13T15:45:30Z] Preparing files for deployment...",
      "<span class=\"ansi-red-fg\">[2025-05-13T15:45:45Z] ✕ Failed to connect to web-server-02: Connection timeout</span>",
      "<span class=\"ansi-red-fg\">[2025-05-13T15:46:00Z] ✕ Deployment failed</span>"
    ]
  },
  {
    id: "dep-003",
    ftId: "ft-004",
    ftName: "FT Delta",
    timestamp: "2025-05-12T09:15:00Z",
    status: "success",
    files: ["frontend/app.js", "frontend/index.html"],
    targets: ["web-server-01"],
    user: "developer",
    logs: [
      "[2025-05-12T09:15:00Z] Deployment started for FT: ft-004",
      "[2025-05-12T09:15:15Z] Connecting to target VMs...",
      "[2025-05-12T09:15:30Z] Preparing files for deployment...",
      "[2025-05-12T09:15:45Z] Running ansible playbook...",
      "[2025-05-12T09:16:00Z] Copying files to target VMs...",
      "<span class=\"ansi-green-fg\">[2025-05-12T09:16:15Z] ✓ Successfully deployed to web-server-01</span>",
      "<span class=\"ansi-bright-green-fg\">[2025-05-12T09:16:30Z] ✓ Deployment completed successfully!</span>"
    ]
  },
  {
    id: "dep-004",
    ftId: "ft-003",
    ftName: "FT Gamma",
    timestamp: "2025-05-11T14:20:00Z",
    status: "canceled",
    files: ["api/v1/users.py", "api/v1/products.py"],
    targets: ["app-server-01", "app-server-02"],
    user: "developer",
    logs: [
      "[2025-05-11T14:20:00Z] Deployment started for FT: ft-003",
      "[2025-05-11T14:20:15Z] Connecting to target VMs...",
      "<span class=\"ansi-yellow-fg\">[2025-05-11T14:20:30Z] ⚠ Warning: app-server-02 is offline</span>",
      "[2025-05-11T14:20:45Z] Preparing files for deployment...",
      "<span class=\"ansi-red-fg\">[2025-05-11T14:21:00Z] ✕ Deployment canceled by user</span>"
    ]
  }
];

const DeploymentHistory = () => {
  const [selectedDeployment, setSelectedDeployment] = useState<typeof mockDeployments[0] | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-deploy-success">Success</Badge>;
      case 'failed':
        return <Badge className="bg-deploy-error">Failed</Badge>;
      case 'canceled':
        return <Badge variant="outline" className="text-deploy-pending border-deploy-pending">Canceled</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };
  
  const viewDeploymentDetails = (deployment: typeof mockDeployments[0]) => {
    setSelectedDeployment(deployment);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Deployment History</CardTitle>
          <CardDescription>
            View previous deployments and their statuses
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Feature Team</TableHead>
                <TableHead>Targets</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockDeployments.map((deployment) => (
                <TableRow key={deployment.id}>
                  <TableCell>
                    {formatDate(deployment.timestamp)}
                  </TableCell>
                  <TableCell>{deployment.ftName}</TableCell>
                  <TableCell>{deployment.targets.length} VM(s)</TableCell>
                  <TableCell>{deployment.user}</TableCell>
                  <TableCell>{getStatusBadge(deployment.status)}</TableCell>
                  <TableCell className="text-right">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => viewDeploymentDetails(deployment)}
                    >
                      Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Deployment Details</DialogTitle>
            <DialogDescription>
              {selectedDeployment && (
                <span>
                  Deployment on {formatDate(selectedDeployment.timestamp)} by {selectedDeployment.user}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {selectedDeployment && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">Deployment Info</CardTitle>
                  </CardHeader>
                  <CardContent className="py-3">
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="font-medium">ID:</dt>
                        <dd className="text-right">{selectedDeployment.id}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="font-medium">Feature Team:</dt>
                        <dd className="text-right">{selectedDeployment.ftName}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="font-medium">Status:</dt>
                        <dd className="text-right">{getStatusBadge(selectedDeployment.status)}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="font-medium">User:</dt>
                        <dd className="text-right">{selectedDeployment.user}</dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">Deployment Targets</CardTitle>
                  </CardHeader>
                  <CardContent className="py-3">
                    <ul className="space-y-1">
                      {selectedDeployment.targets.map(target => (
                        <li key={target} className="flex items-center">
                          <span className="text-sm">{target}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </div>
              
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-base">Deployed Files</CardTitle>
                </CardHeader>
                <CardContent className="py-3">
                  <ul className="space-y-1">
                    {selectedDeployment.files.map(file => (
                      <li key={file} className="text-sm font-mono">{file}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              
              <DeploymentLogs logs={selectedDeployment.logs} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DeploymentHistory;
