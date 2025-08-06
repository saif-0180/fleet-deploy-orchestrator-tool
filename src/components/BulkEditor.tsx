
import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Replace, FileText, Save, Eye } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const BulkEditor = ({ currentBranch }) => {
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [searchKey, setSearchKey] = useState('');
  const [replaceValue, setReplaceValue] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [operation, setOperation] = useState('replace'); // replace, add, delete
  const [isLoading, setIsLoading] = useState(false);
  const [previewResults, setPreviewResults] = useState([]);
  const [showPreview, setShowPreview] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/git/files?extensions=yaml,yml,json');
      if (response.ok) {
        const data = await response.json();
        setFiles(data.files || []);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load files",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const searchInFiles = async () => {
    if (!searchKey) {
      toast({
        title: "Error",
        description: "Please enter a search key",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/bulk-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          searchKey,
          files: Array.from(selectedFiles)
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to search files",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const previewChanges = async () => {
    if (!searchKey) {
      toast({
        title: "Error",
        description: "Please enter a search key",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/bulk-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation,
          searchKey,
          replaceValue,
          files: Array.from(selectedFiles)
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPreviewResults(data.preview || []);
        setShowPreview(true);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to preview changes",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const applyBulkChanges = async () => {
    if (!searchKey) {
      toast({
        title: "Error",
        description: "Please enter a search key",
        variant: "destructive"
      });
      return;
    }

    if (selectedFiles.size === 0) {
      toast({
        title: "Error",
        description: "Please select files to modify",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/bulk-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation,
          searchKey,
          replaceValue,
          files: Array.from(selectedFiles),
          branch: currentBranch
        })
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: "Success",
          description: `Modified ${data.modifiedFiles} files successfully`
        });
        setSearchResults([]);
        setPreviewResults([]);
        setShowPreview(false);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to apply bulk changes",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFileSelection = (filePath) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filePath)) {
      newSelected.delete(filePath);
    } else {
      newSelected.add(filePath);
    }
    setSelectedFiles(newSelected);
  };

  const selectAllFiles = () => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map(f => f.path)));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Replace className="h-5 w-5 text-[#007ea7]" />
          <h3 className="text-lg font-semibold text-[#EEEEEE]">Bulk YAML Editor</h3>
        </div>
        
        <Badge variant="outline" className="text-[#EEEEEE]">
          {selectedFiles.size} files selected
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
              <FileText className="h-5 w-5" />
              File Selection
              <Button
                size="sm"
                variant="outline"
                onClick={selectAllFiles}
                className="ml-auto border-[#007ea7]/30"
              >
                {selectedFiles.size === files.length ? 'Deselect All' : 'Select All'}
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px] w-full">
              <div className="space-y-2">
                {files.map(file => {
                  const isSelected = selectedFiles.has(file.path);
                  const extension = file.name.split('.').pop().toLowerCase();
                  
                  return (
                    <div
                      key={file.path}
                      className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#007ea7]/20 border border-[#007ea7]' : 'hover:bg-[#2A4759]/30'
                      }`}
                      onClick={() => toggleFileSelection(file.path)}
                    >
                      <Checkbox checked={isSelected} />
                      <span className="text-lg">
                        {extension === 'yaml' || extension === 'yml' ? '📄' : 
                         extension === 'json' ? '🔧' : '📄'}
                      </span>
                      <span className="text-sm text-[#EEEEEE] flex-1">{file.name}</span>
                      <Badge className={`text-xs ${
                        extension === 'yaml' || extension === 'yml' ? 'bg-blue-500' :
                        extension === 'json' ? 'bg-green-500' : 'bg-gray-500'
                      }`}>
                        {extension.toUpperCase()}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
              <Replace className="h-5 w-5" />
              Bulk Operations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
                Operation Type
              </label>
              <Select value={operation} onValueChange={setOperation}>
                <SelectTrigger className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#2A4759] border-[#007ea7]/30">
                  <SelectItem value="replace" className="text-[#EEEEEE]">Replace Value</SelectItem>
                  <SelectItem value="add" className="text-[#EEEEEE]">Add New Key</SelectItem>
                  <SelectItem value="delete" className="text-[#EEEEEE]">Delete Key</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
                {operation === 'add' ? 'New Key Name' : 'Search Key/Path'}
              </label>
              <Input
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                placeholder={operation === 'add' ? 'new.key.path' : 'existing.key.path'}
                className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
              />
            </div>

            {operation !== 'delete' && (
              <div>
                <label className="block text-sm font-medium text-[#EEEEEE] mb-2">
                  {operation === 'replace' ? 'Replace With' : 'Value'}
                </label>
                <Input
                  value={replaceValue}
                  onChange={(e) => setReplaceValue(e.target.value)}
                  placeholder="Enter new value..."
                  className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
                />
              </div>
            )}

            <div className="flex gap-2">
              <Button
                onClick={searchInFiles}
                disabled={isLoading}
                variant="outline"
                className="flex-1 border-[#007ea7]/30"
              >
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
              <Button
                onClick={previewChanges}
                disabled={isLoading}
                variant="outline"
                className="flex-1 border-[#007ea7]/30"
              >
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </Button>
            </div>

            <Button
              onClick={applyBulkChanges}
              disabled={isLoading || selectedFiles.size === 0}
              className="w-full bg-[#007ea7] hover:bg-[#005f82]"
            >
              <Save className="h-4 w-4 mr-2" />
              Apply Changes
            </Button>
          </CardContent>
        </Card>
      </div>

      {(searchResults.length > 0 || showPreview) && (
        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE]">
              {showPreview ? 'Preview Changes' : 'Search Results'}
              <Badge variant="outline" className="ml-2">
                {showPreview ? previewResults.length : searchResults.length} matches
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] w-full">
              <div className="space-y-3">
                {(showPreview ? previewResults : searchResults).map((result, index) => (
                  <div key={index} className="border border-[#007ea7]/20 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-[#EEEEEE]">{result.file}</span>
                      <Badge variant="outline" className="text-xs">
                        {result.matches || 1} match{(result.matches || 1) > 1 ? 'es' : ''}
                      </Badge>
                    </div>
                    
                    <div className="space-y-2">
                      {result.changes ? (
                        // Preview mode
                        result.changes.map((change, changeIndex) => (
                          <div key={changeIndex} className="bg-[#2A4759]/20 p-2 rounded font-mono text-sm">
                            <div className="text-red-400">- {change.old}</div>
                            <div className="text-green-400">+ {change.new}</div>
                          </div>
                        ))
                      ) : (
                        // Search results mode
                        result.lines && result.lines.map((line, lineIndex) => (
                          <div key={lineIndex} className="bg-[#2A4759]/20 p-2 rounded">
                            <div className="text-xs text-[#EEEEEE]/70 mb-1">
                              Line {line.number}:
                            </div>
                            <div className="font-mono text-sm text-[#EEEEEE]">
                              {line.content}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default BulkEditor;
