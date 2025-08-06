
import React, { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import GitOperations from './GitOperations';
import YAMLFileManager from './YAMLFileManager';
import YAMLEditor from './YAMLEditor';
import GitHistory from './GitHistory';
import BulkEditor from './BulkEditor';

const GitManagement = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [currentBranch, setCurrentBranch] = useState('main');
  const [repoStatus, setRepoStatus] = useState({
    initialized: false,
    hasChanges: false,
    ahead: 0,
    behind: 0
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#EEEEEE]">Git & YAML Management</h1>
        <div className="text-sm text-[#EEEEEE]/70">
          Branch: <span className="font-mono text-[#007ea7]">{currentBranch}</span>
        </div>
      </div>

      <Tabs defaultValue="git-ops" className="w-full">
        <TabsList className="grid w-full grid-cols-5 bg-[#00171f]/90 backdrop-blur-sm">
          <TabsTrigger value="git-ops" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE]">
            Git Operations
          </TabsTrigger>
          <TabsTrigger value="yaml-files" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE]">
            YAML Files
          </TabsTrigger>
          <TabsTrigger value="yaml-editor" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE]">
            YAML Editor
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE]">
            History
          </TabsTrigger>
          <TabsTrigger value="bulk-editor" className="data-[state=active]:bg-[#007ea7] data-[state=active]:text-white text-[#EEEEEE]">
            Bulk Editor
          </TabsTrigger>
        </TabsList>

        <TabsContent value="git-ops" className="space-y-4">
          <GitOperations 
            currentBranch={currentBranch}
            setCurrentBranch={setCurrentBranch}
            repoStatus={repoStatus}
            setRepoStatus={setRepoStatus}
          />
        </TabsContent>

        <TabsContent value="yaml-files" className="space-y-4">
          <YAMLFileManager 
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
          />
        </TabsContent>

        <TabsContent value="yaml-editor" className="space-y-4">
          <YAMLEditor 
            selectedFile={selectedFile}
            currentBranch={currentBranch}
          />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <GitHistory 
            selectedFile={selectedFile}
          />
        </TabsContent>

        <TabsContent value="bulk-editor" className="space-y-4">
          <BulkEditor 
            currentBranch={currentBranch}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default GitManagement;
