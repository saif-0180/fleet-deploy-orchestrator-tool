
import React from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Toaster } from "@/components/ui/toaster";
import FileOperations from "@/components/FileOperations";
import SqlOperations from "@/components/SqlOperations";
import SystemctlOperations from "@/components/SystemctlOperations";
import DeploymentHistory from "@/components/DeploymentHistory";
import UserManagement from "@/components/UserManagement";
import GitManagement from "@/components/GitManagement";
import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TemplateGenerator from "@/components/TemplateGenerator";
import DeployTemplate from "@/components/DeployTemplate";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000
    }
  }
});

const Index = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  return (
    <QueryClientProvider client={queryClient}>
      <div 
        className="min-h-screen text-[#EEEEEE] bg-cover bg-center bg-no-repeat bg-fixed"
        style={{ 
          backgroundImage: 'url(/background/amdocs-bg.png)',
          backgroundSize: 'contain',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'fixed',
          backgroundSize: '100% 100%'
        }}
      >
        <div className="min-h-screen bg-black/20">
          <Header />
          
          <main className="container mx-auto px-4 py-6">
            <Tabs defaultValue="file" className="w-full">
              <TabsList className="flex justify-center flex-wrap gap-1 bg-[#00171f]/90 backdrop-blur-sm mb-6 p-1">
                <TabsTrigger value="file" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  File Operations
                </TabsTrigger>
                <TabsTrigger value="sql" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  SQL Operations
                </TabsTrigger>
                <TabsTrigger value="systemctl" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  Systemctl Operations
                </TabsTrigger>
                <TabsTrigger value="deploy-template" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  Deploy Template
                </TabsTrigger>
                <TabsTrigger value="template-generator" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  Template Generator
                </TabsTrigger>
                <TabsTrigger value="git-management" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  Git & YAML
                </TabsTrigger>
                <TabsTrigger value="history" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                  Deployment History
                </TabsTrigger>
                {isAdmin && (
                  <TabsTrigger value="users" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE] px-4 py-2">
                    User Management
                  </TabsTrigger>
                )}
              </TabsList>
              
              <TabsContent value="file" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <FileOperations />
              </TabsContent>
              
              <TabsContent value="sql" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <SqlOperations />
              </TabsContent>
              
              <TabsContent value="systemctl" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <SystemctlOperations />
              </TabsContent>
              
              <TabsContent value="deploy-template" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <DeployTemplate />
              </TabsContent>
              
              <TabsContent value="template-generator" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <TemplateGenerator />
              </TabsContent>

              <TabsContent value="git-management" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <GitManagement />
              </TabsContent>
                        
              <TabsContent value="history" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                <DeploymentHistory />
              </TabsContent>
              
              {isAdmin && (
                <TabsContent value="users" className="p-6 bg-[#00171f]/90 backdrop-blur-sm rounded-md shadow-lg">
                  <UserManagement />
                </TabsContent>
              )}
            </Tabs>
          </main>
          
          <Toaster />
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default Index;
