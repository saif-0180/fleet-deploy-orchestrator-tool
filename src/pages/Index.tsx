
import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import FileOperations from '@/components/FileOperations';
import SqlOperations from '@/components/SqlOperations';
import SystemctlOperations from '@/components/SystemctlOperations';
import ShellCommandOperations from '@/components/ShellCommandOperations';
import DeploymentHistory from '@/components/DeploymentHistory';
import UserManagement from '@/components/UserManagement';
import DeployTemplate from '@/components/DeployTemplate';
import TemplateGenerator from '@/components/TemplateGenerator';
import { useAuth } from '@/contexts/AuthContext';

const Index = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-[#F2F0EF]">
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <h1 
            className="text-4xl font-bold mb-2 bg-gradient-to-r from-[#00171f] to-[#00a7e1] bg-clip-text text-transparent"
          >
            Operations Dashboard
          </h1>
          <p className="text-[#00171f]/70 text-lg">
            Manage deployments, execute commands, and monitor operations
          </p>
        </div>

        <Tabs defaultValue="file-operations" className="w-full">
          <TabsList 
            className="grid w-full grid-cols-4 lg:grid-cols-8 mb-6 bg-white border border-[#00171f]/20 shadow-sm"
          >
            <TabsTrigger 
              value="file-operations" 
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              Files
            </TabsTrigger>
            <TabsTrigger 
              value="sql-operations"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              SQL
            </TabsTrigger>
            <TabsTrigger 
              value="systemctl-operations"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              Services
            </TabsTrigger>
            <TabsTrigger 
              value="shell-operations"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              Shell
            </TabsTrigger>
            <TabsTrigger 
              value="template-generator"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              Templates
            </TabsTrigger>
            <TabsTrigger 
              value="deploy-template"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              Deploy
            </TabsTrigger>
            <TabsTrigger 
              value="deployment-history"
              className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
            >
              History
            </TabsTrigger>
            {user?.role === 'admin' && (
              <TabsTrigger 
                value="user-management"
                className="data-[state=active]:bg-[#00a7e1] data-[state=active]:text-white text-[#00171f] hover:bg-[#00a7e1]/10"
              >
                Users
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="file-operations">
            <FileOperations />
          </TabsContent>

          <TabsContent value="sql-operations">
            <SqlOperations />
          </TabsContent>

          <TabsContent value="systemctl-operations">
            <SystemctlOperations />
          </TabsContent>

          <TabsContent value="shell-operations">
            <ShellCommandOperations />
          </TabsContent>

          <TabsContent value="template-generator">
            <TemplateGenerator />
          </TabsContent>

          <TabsContent value="deploy-template">
            <DeployTemplate />
          </TabsContent>

          <TabsContent value="deployment-history">
            <DeploymentHistory />
          </TabsContent>

          {user?.role === 'admin' && (
            <TabsContent value="user-management">
              <UserManagement />
            </TabsContent>
          )}
        </Tabs>
      </div>
    </div>
  );
};

export default Index;
