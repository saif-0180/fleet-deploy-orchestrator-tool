import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import LogDisplay from './LogDisplay';
import { useAuth } from '@/contexts/AuthContext';

const SqlOperations = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const [selectedFT, setSelectedFT] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [selectedDbConnection, setSelectedDbConnection] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [deploymentId, setDeploymentId] = useState<string | null>(null);
  const [logStatus, setLogStatus] = useState<'idle' | 'loading' | 'running' | 'success' | 'failed'>('idle');
  
  // Auto-populated fields based on selected connection
  const [hostname, setHostname] = useState<string>('');
  const [port, setPort] = useState<string>('');
  const [dbName, setDbName] = useState<string>('');

  // Fetch FTs
  const { data: fts = [], isLoading: isLoadingFTs } = useQuery({
    queryKey: ['fts', 'sql'],
    queryFn: async () => {
      const response = await fetch('/api/fts?type=sql');
      if (!response.ok) {
        throw new Error('Failed to fetch FTs');
      }
      return response.json();
    },
    refetchOnWindowFocus: false,
  });

  // Fetch Files for selected FT
  const { data: files = [], isLoading: isLoadingFiles } = useQuery({
    queryKey: ['ft-files', selectedFT],
    queryFn: async () => {
      if (!selectedFT) return [];
      const response = await fetch(`/api/fts/${selectedFT}/files?type=sql`);
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      return response.json();
    },
    enabled: !!selectedFT,
    refetchOnWindowFocus: false,
  });

  // Fetch database connections
  const { data: dbConnections = [], isLoading: isLoadingConnections } = useQuery({
    queryKey: ['db-connections'],
    queryFn: async () => {
      const response = await fetch('/api/db/connections');
      if (!response.ok) {
        throw new Error('Failed to fetch database connections');
      }
      return response.json();
    },
    refetchOnWindowFocus: false,
  });

  // Fetch database users
  const { data: dbUsers = [], isLoading: isLoadingUsers } = useQuery({
    queryKey: ['db-users'],
    queryFn: async () => {
      const response = await fetch('/api/db/users');
      if (!response.ok) {
        throw new Error('Failed to fetch database users');
      }
      return response.json();
    },
    refetchOnWindowFocus: false,
  });

  // Handle database connection selection
  const handleDbConnectionChange = (connectionName: string) => {
    setSelectedDbConnection(connectionName);
    
    // Find the selected connection and populate fields
    const selectedConnection = dbConnections.find(
      (conn: any) => conn.db_connection === connectionName
    );
    
    if (selectedConnection) {
      setHostname(selectedConnection.hostname);
      setPort(selectedConnection.port);
      setDbName(selectedConnection.db_name);
    } else {
      // Clear fields if no connection found
      setHostname('');
      setPort('');
      setDbName('');
    }
  };

  // Execute SQL mutation
  const executeSqlMutation = useMutation({
    mutationFn: async () => {
      // Get the token from localStorage
      const token = localStorage.getItem('authToken');
      
      if (!token) {
        throw new Error('No authentication token found. Please log in.');
      }
      if (!selectedFT || !selectedFile || !hostname || !port || !selectedUser || !dbName) {
        throw new Error('Missing required fields');
      }

      const response = await fetch('/api/deploy/sql', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ft: selectedFT,
          file: selectedFile,
          hostname: hostname,
          port: port,
          dbName,
          user: selectedUser,
          password,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to execute SQL');
      }

      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "SQL Execution Started",
        description: `Deployment ID: ${data.deploymentId}`,
      });
      setDeploymentId(data.deploymentId);
      setLogStatus('running');
      pollLogs(data.deploymentId);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : 'Failed to execute SQL',
        variant: "destructive",
      });
    },
  });

  // Poll logs when deployment starts
  const pollLogs = async (id: string) => {
    try {
      setLogStatus('loading');
      
      // Set up SSE for real-time logs
      const evtSource = new EventSource(`/api/deploy/${id}/logs`);
      
      evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.message) {
          setLogs(prev => [...prev, data.message]);
        }
        
        if (data.status && data.status !== 'running') {
          setLogStatus(data.status);
          evtSource.close();
        }
      };
      
      evtSource.onerror = () => {
        evtSource.close();
        // Fallback to normal polling if SSE fails
        fetchLogs(id);
      };
      
      return () => {
        evtSource.close();
      };
    } catch (error) {
      console.error('Error setting up log polling:', error);
      // Fallback to regular polling
      fetchLogs(id);
    }
  };
  
  const fetchLogs = async (id: string) => {
    try {
      const response = await fetch(`/api/deploy/${id}/logs`);
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
      
      if (data.status) {
        setLogStatus(data.status);
      }
      
      // Continue polling if still running
      if (data.status === 'running') {
        setTimeout(() => fetchLogs(id), 2000);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
      setLogStatus('failed');
    }
  };

  // Handle button click
  const handleSubmit = () => {
    setLogs([]);
    executeSqlMutation.mutate();
  };

  // Update selected file when files change or selected FT changes
  useEffect(() => {
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
    } else {
      setSelectedFile('');
    }
  }, [files, selectedFT]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card className="bg-[#1a2b42] text-[#EEEEEE]">
        <CardHeader>
          <CardTitle>SQL Execution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="ft">FT</Label>
              <Select 
                onValueChange={setSelectedFT}
                disabled={isLoadingFTs || fts.length === 0}
              >
                <SelectTrigger id="ft" className="bg-[#2a3f5f] border-[#3a4f6f] text-[#EEEEEE]">
                  <SelectValue placeholder="Select FT" />
                </SelectTrigger>
                <SelectContent>
                  {fts.map((ft: string) => (
                    <SelectItem key={ft} value={ft}>{ft}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="file">SQL File</Label>
              <Select 
                onValueChange={setSelectedFile}
                disabled={isLoadingFiles || files.length === 0 || !selectedFT}
                value={selectedFile}
              >
                <SelectTrigger id="file" className="bg-[#2a3f5f] border-[#3a4f6f] text-[#EEEEEE]">
                  <SelectValue placeholder="Select SQL File" />
                </SelectTrigger>
                <SelectContent>
                  {files.map((file: string) => (
                    <SelectItem key={file} value={file}>{file}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Database Connection Dropdown */}
            <div>
              <Label htmlFor="db-connection">Database Connection</Label>
              <Select 
                value={selectedDbConnection} 
                onValueChange={handleDbConnectionChange}
                disabled={isLoadingConnections}
              >
                <SelectTrigger id="db-connection" className="bg-[#2a3f5f] border-[#3a4f6f] text-[#EEEEEE]">
                  <SelectValue placeholder="Select database connection..." />
                </SelectTrigger>
                <SelectContent>
                  {dbConnections.map((conn: any) => (
                    <SelectItem key={conn.db_connection} value={conn.db_connection}>
                      <div className="flex flex-col">
                        <span className="font-medium">{conn.db_connection}</span>
                        <span className="text-xs text-gray-400">
                          {conn.hostname}:{conn.port} - {conn.db_name}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Auto-populated connection details */}
            {selectedDbConnection && (
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <Label htmlFor="hostname" className="text-xs">Hostname</Label>
                  <Input 
                    id="hostname"
                    value={hostname}
                    readOnly
                    className="bg-gray-700/50 text-xs border-[#3a4f6f] text-[#EEEEEE]"
                    placeholder="Auto-populated"
                  />
                </div>
                <div>
                  <Label htmlFor="port" className="text-xs">Port</Label>
                  <Input 
                    id="port"
                    value={port}
                    readOnly
                    className="bg-gray-700/50 text-xs border-[#3a4f6f] text-[#EEEEEE]"
                    placeholder="Auto-populated"
                  />
                </div>
                <div>
                  <Label htmlFor="db-name-display" className="text-xs">DB Name</Label>
                  <Input 
                    id="db-name-display"
                    value={dbName}
                    readOnly
                    className="bg-gray-700/50 text-xs border-[#3a4f6f] text-[#EEEEEE]"
                    placeholder="Auto-populated"
                  />
                </div>
              </div>
            )}
            
            <div>
              <Label htmlFor="user">Database User</Label>
              <Select 
                value={selectedUser} 
                onValueChange={setSelectedUser} 
                disabled={isLoadingUsers}
              >
                <SelectTrigger id="user" className="bg-[#2a3f5f] border-[#3a4f6f] text-[#EEEEEE]">
                  <SelectValue placeholder="Select user..." />
                </SelectTrigger>
                <SelectContent>
                  {dbUsers.map((user: string) => (
                    <SelectItem key={user} value={user}>{user}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="bg-[#2a3f5f] border-[#3a4f6f] text-[#EEEEEE] placeholder:text-gray-400"
              />
            </div>
            
            <Button 
              onClick={handleSubmit}
              disabled={!selectedFT || !selectedFile || !selectedDbConnection || !selectedUser || !dbName || executeSqlMutation.isPending}
              className="w-full"
            >
              {executeSqlMutation.isPending ? 'Executing...' : 'Execute SQL'}
            </Button>

            {/* Selected Configuration Summary */}
            {selectedDbConnection && (
              <div className="mt-4 p-3 bg-gray-700/30 rounded text-xs">
                <div className="font-medium mb-1">Selected Configuration:</div>
                <div>Connection: {selectedDbConnection}</div>
                <div>Target: {hostname}:{port}/{dbName}</div>
                <div>User: {selectedUser}</div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
      
      <LogDisplay 
        logs={logs} 
        title={`SQL Execution Logs${user?.username ? ` - User: ${user.username}` : ''}`}
        height="400px"
        status={logStatus}
      />
    </div>
  );
};

export default SqlOperations;