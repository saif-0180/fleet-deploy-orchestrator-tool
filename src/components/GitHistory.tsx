
import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { History, GitCommit, User, Calendar, FileText, RotateCcw } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const GitHistory = ({ selectedFile }) => {
  const [commits, setCommits] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [diffContent, setDiffContent] = useState('');
  const { toast } = useToast();

  useEffect(() => {
    if (selectedFile) {
      loadFileHistory();
    }
  }, [selectedFile]);

  const loadFileHistory = async () => {
    if (!selectedFile) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/api/git/history?path=${encodeURIComponent(selectedFile.path)}`);
      if (response.ok) {
        const data = await response.json();
        setCommits(data.commits || []);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load file history",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadCommitDiff = async (commitHash) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/git/diff?commit=${commitHash}&path=${encodeURIComponent(selectedFile.path)}`);
      if (response.ok) {
        const data = await response.json();
        setDiffContent(data.diff || '');
        setSelectedCommit(commitHash);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load commit diff",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const revertToCommit = async (commitHash) => {
    if (!selectedFile) return;
    
    setIsLoading(true);
    try {
      const response = await fetch('/api/git/revert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedFile.path,
          commitHash: commitHash
        })
      });

      if (response.ok) {
        toast({
          title: "Success",
          description: `File reverted to commit ${commitHash.substring(0, 8)}`
        });
        loadFileHistory();
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to revert file",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDiff = (diff) => {
    return diff.split('\n').map((line, index) => {
      let className = 'text-[#EEEEEE]';
      if (line.startsWith('+')) className = 'text-green-400';
      else if (line.startsWith('-')) className = 'text-red-400';
      else if (line.startsWith('@@')) className = 'text-blue-400';
      
      return (
        <div key={index} className={`font-mono text-sm ${className}`}>
          {line}
        </div>
      );
    });
  };

  if (!selectedFile) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center text-[#EEEEEE]/70">
          <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select a file to view its history</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-[#007ea7]" />
          <h3 className="text-lg font-semibold text-[#EEEEEE]">
            History: {selectedFile.name}
          </h3>
        </div>
        
        <Button
          onClick={loadFileHistory}
          disabled={isLoading}
          variant="outline"
          className="border-[#007ea7]/30"
        >
          <History className="h-4 w-4 mr-2" />
          Refresh History
        </Button>
      </div>

      <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
        <CardHeader>
          <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
            <GitCommit className="h-5 w-5" />
            Commit History
            <Badge variant="outline" className="ml-auto">
              {commits.length} commits
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[500px] w-full">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-[#EEEEEE]">Loading history...</div>
              </div>
            ) : commits.length === 0 ? (
              <div className="text-center py-8 text-[#EEEEEE]/70">
                No commit history found for this file
              </div>
            ) : (
              <div className="space-y-4">
                {commits.map((commit, index) => (
                  <div key={commit.hash} className="border border-[#007ea7]/20 rounded-lg p-4 hover:bg-[#2A4759]/20 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge className="bg-[#007ea7] font-mono text-xs">
                            {commit.hash.substring(0, 8)}
                          </Badge>
                          {index === 0 && (
                            <Badge variant="outline" className="text-xs">
                              Latest
                            </Badge>
                          )}
                        </div>
                        
                        <h4 className="text-[#EEEEEE] font-medium mb-2">
                          {commit.message}
                        </h4>
                        
                        <div className="flex items-center gap-4 text-sm text-[#EEEEEE]/70">
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {commit.author}
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(commit.date)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => loadCommitDiff(commit.hash)}
                              className="border-[#007ea7]/30"
                            >
                              <FileText className="h-3 w-3 mr-1" />
                              Diff
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-4xl max-h-[80vh] bg-[#00171f] border-[#007ea7]/30">
                            <DialogHeader>
                              <DialogTitle className="text-[#EEEEEE]">
                                Commit Diff: {commit.hash.substring(0, 8)}
                              </DialogTitle>
                            </DialogHeader>
                            <ScrollArea className="h-[60vh] w-full">
                              <div className="bg-[#2A4759]/20 p-4 rounded font-mono text-sm">
                                {diffContent ? formatDiff(diffContent) : (
                                  <div className="text-[#EEEEEE]/70">Loading diff...</div>
                                )}
                              </div>
                            </ScrollArea>
                          </DialogContent>
                        </Dialog>
                        
                        {index !== 0 && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => revertToCommit(commit.hash)}
                            className="border-orange-500/30 text-orange-400 hover:bg-orange-500/10"
                          >
                            <RotateCcw className="h-3 w-3 mr-1" />
                            Revert
                          </Button>
                        )}
                      </div>
                    </div>
                    
                    {commit.changes && (
                      <div className="mt-3 flex gap-4 text-xs text-[#EEEEEE]/70">
                        <span className="text-green-400">+{commit.changes.additions || 0} additions</span>
                        <span className="text-red-400">-{commit.changes.deletions || 0} deletions</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};

export default GitHistory;
