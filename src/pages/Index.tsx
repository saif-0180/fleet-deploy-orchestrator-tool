
import React from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Toaster } from "@/components/ui/toaster";
import FileOperations from "@/components/FileOperations";
import SqlOperations from "@/components/SqlOperations";
import SystemctlOperations from "@/components/SystemctlOperations";
import DeploymentHistory from "@/components/DeploymentHistory";
import UserManagement from "@/components/UserManagement";
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
        className="min-h-screen text-foreground bg-cover bg-center bg-no-repeat bg-fixed"
        style={{ 
          backgroundImage: 'url(/lovable-uploads/39178b56-1e02-4fba-9e7c-2e33e2570914.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          backgroundAttachment: 'fixed'
        }}
      >
        <div className="min-h-screen bg-background/40 backdrop-blur-sm">
          <Header />
          
          <main className="container mx-auto px-4 py-6">
            <Tabs defaultValue="file" className="w-full">
              <TabsList className={`grid w-full ${isAdmin ? 'grid-cols-8' : 'grid-cols-7'} bg-card/90 backdrop-blur-sm mb-6 border border-border`}>
                <TabsTrigger value="file" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  File Operations
                </TabsTrigger>
                <TabsTrigger value="sql" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  SQL Operations
                </TabsTrigger>
                <TabsTrigger value="systemctl" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  Systemctl Operations
                </TabsTrigger>
                <TabsTrigger value="deploy-template" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  Deploy Template
                </TabsTrigger>
                <TabsTrigger value="template-generator" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  Template Generator
                </TabsTrigger>
                <TabsTrigger value="history" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                  Deployment History
                </TabsTrigger>
                {isAdmin && (
                  <TabsTrigger value="users" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-muted-foreground hover:text-foreground transition-colors">
                    User Management
                  </TabsTrigger>
                )}
              </TabsList>
              
              <TabsContent value="file" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <FileOperations />
              </TabsContent>
              
              <TabsContent value="sql" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <SqlOperations />
              </TabsContent>
              
              <TabsContent value="systemctl" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <SystemctlOperations />
              </TabsContent>
              
              <TabsContent value="deploy-template" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <DeployTemplate />
              </TabsContent>
              
              <TabsContent value="template-generator" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <TemplateGenerator />
              </TabsContent>
                        
              <TabsContent value="history" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
                <DeploymentHistory />
              </TabsContent>
              
              {isAdmin && (
                <TabsContent value="users" className="p-6 bg-card/95 backdrop-blur-sm rounded-lg shadow-lg border border-border">
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
