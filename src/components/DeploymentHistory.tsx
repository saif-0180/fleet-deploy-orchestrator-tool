import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, Clock, CheckCircle, XCircle } from 'lucide-react';
import { formatInTimeZone } from 'date-fns-tz';

const DeploymentHistory: React.FC = () => {
  const { data: deployments, refetch, isLoading, error } = useQuery({
    queryKey: ['deployment-history'],
    queryFn: async () => {
      const response = await fetch('/api/deployments');
      if (!response.ok) {
        throw new Error('Failed to fetch deployment history');
      }
      const data = await response.json();
      return data;
    },
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });

  const formatDate = (dateStr: string) => {
    try {
      return formatInTimeZone(dateStr, 'America/New_York', 'yyyy-MM-dd HH:mm:ss zzz');
    } catch (error) {
      console.error("Error formatting date:", error);
      return 'Invalid Date';
    }
  };

  const calculateDuration = (start: string | number | Date, end: string | number | Date) => {
    const startDate = new Date(start).getTime();
    const endDate = new Date(end).getTime();
    const duration = endDate - startDate;

    if (isNaN(duration) || duration < 0) {
      return 'N/A';
    }

    const seconds = Math.floor((duration / 1000) % 60);
    const minutes = Math.floor((duration / (1000 * 60)) % 60);
    const hours = Math.floor((duration / (1000 * 60 * 60)) % 24);

    let formattedDuration = '';
    if (hours > 0) {
      formattedDuration += `${hours}h `;
    }
    if (minutes > 0) {
      formattedDuration += `${minutes}m `;
    }
    formattedDuration += `${seconds}s`;

    return formattedDuration;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <Badge className="bg-green-500 hover:bg-green-600 text-white">
            <CheckCircle className="h-3 w-3 mr-1" />
            Success
          </Badge>
        );
      case 'failed':
        return (
          <Badge className="bg-red-500 hover:bg-red-600 text-white">
            <XCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        );
      case 'running':
        return (
          <Badge className="bg-yellow-500 hover:bg-yellow-600 text-white">
            <Clock className="h-3 w-3 mr-1" />
            Running
          </Badge>
        );
      default:
        return (
          <Badge className="bg-muted hover:bg-muted/80 text-muted-foreground">
            {status}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold gradient-heading">Deployment History</h2>
        <Button
          onClick={() => refetch()}
          className="bg-secondary text-secondary-foreground hover:bg-secondary/80"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
      
      <Card className="bg-card border-border shadow-lg">
        <CardHeader className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-t-lg">
          <CardTitle className="text-primary text-lg font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Recent Deployments
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-medium text-foreground">ID</th>
                  <th className="text-left py-3 px-4 font-medium text-foreground">Type</th>
                  <th className="text-left py-3 px-4 font-medium text-foreground">VMs</th>
                  <th className="text-left py-3 px-4 font-medium text-foreground">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-foreground">Started</th>
                  <th className="text-left py-3 px-4 font-medium text-foreground">Duration</th>
                </tr>
              </thead>
              <tbody>
                {deployments?.deployments?.map((deployment: any) => (
                  <tr key={deployment.deployment_id} className="border-b border-border hover:bg-muted/20 transition-colors">
                    <td className="py-3 px-4 text-foreground font-mono text-sm">{deployment.deployment_id}</td>
                    <td className="py-3 px-4 text-foregroup">{deployment.type}</td>
                    <td className="py-3 px-4 text-foreground">{deployment.vms.join(', ')}</td>
                    <td className="py-3 px-4">{getStatusBadge(deployment.status)}</td>
                    <td className="py-3 px-4 text-foreground text-sm">{formatDate(deployment.start_time)}</td>
                    <td className="py-3 px-4 text-foreground text-sm">{calculateDuration(deployment.start_time, deployment.end_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DeploymentHistory;
