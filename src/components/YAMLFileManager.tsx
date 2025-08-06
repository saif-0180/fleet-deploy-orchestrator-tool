
import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { FileText, Search, Folder, FolderOpen } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const YAMLFileManager = ({ onFileSelect, selectedFile }) => {
  const [files, setFiles] = useState([]);
  const [filteredFiles, setFilteredFiles] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadFiles();
  }, []);

  useEffect(() => {
    filterFiles();
  }, [files, searchTerm]);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/git/files?extensions=yaml,yml,json,env,ini');
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

  const filterFiles = () => {
    if (!searchTerm) {
      setFilteredFiles(files);
      return;
    }

    const filtered = files.filter(file => 
      file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      file.path.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredFiles(filtered);
  };

  const getFileExtension = (filename) => {
    return filename.split('.').pop().toLowerCase();
  };

  const getFileIcon = (extension) => {
    const iconMap = {
      yaml: '📄',
      yml: '📄',
      json: '🔧',
      env: '🔐',
      ini: '⚙️'
    };
    return iconMap[extension] || '📄';
  };

  const getBadgeColor = (extension) => {
    const colorMap = {
      yaml: 'bg-blue-500',
      yml: 'bg-blue-500',
      json: 'bg-green-500',
      env: 'bg-orange-500',
      ini: 'bg-purple-500'
    };
    return colorMap[extension] || 'bg-gray-500';
  };

  const toggleFolder = (folderPath) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
    }
    setExpandedFolders(newExpanded);
  };

  const organizeFilesByFolder = (files) => {
    const folderStructure = {};
    
    files.forEach(file => {
      const pathParts = file.path.split('/');
      const fileName = pathParts.pop();
      const folderPath = pathParts.join('/') || 'root';
      
      if (!folderStructure[folderPath]) {
        folderStructure[folderPath] = [];
      }
      
      folderStructure[folderPath].push({
        ...file,
        name: fileName
      });
    });
    
    return folderStructure;
  };

  const handleFileSelect = (file) => {
    onFileSelect(file);
    toast({
      title: "File Selected",
      description: `Selected: ${file.path}`
    });
  };

  const folderStructure = organizeFilesByFolder(filteredFiles);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
              <Search className="h-5 w-5" />
              File Search
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search files..."
              className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
            />
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="text-[#EEEEEE]">
                YAML: {files.filter(f => ['yaml', 'yml'].includes(getFileExtension(f.name))).length}
              </Badge>
              <Badge variant="outline" className="text-[#EEEEEE]">
                JSON: {files.filter(f => getFileExtension(f.name) === 'json').length}
              </Badge>
              <Badge variant="outline" className="text-[#EEEEEE]">
                Other: {files.filter(f => !['yaml', 'yml', 'json'].includes(getFileExtension(f.name))).length}
              </Badge>
            </div>
            <Button 
              onClick={loadFiles} 
              disabled={isLoading}
              className="w-full bg-[#007ea7] hover:bg-[#005f82]"
            >
              Refresh Files
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="lg:col-span-2">
        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE] flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Repository Files
              {selectedFile && (
                <Badge className="ml-auto bg-[#007ea7]">
                  Selected: {selectedFile.name}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] w-full">
              {isLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-[#EEEEEE]">Loading files...</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(folderStructure).map(([folderPath, folderFiles]) => (
                    <div key={folderPath} className="border-l-2 border-[#007ea7]/30 pl-2">
                      <div 
                        className="flex items-center gap-2 cursor-pointer hover:bg-[#2A4759]/30 p-2 rounded"
                        onClick={() => toggleFolder(folderPath)}
                      >
                        {expandedFolders.has(folderPath) ? 
                          <FolderOpen className="h-4 w-4 text-[#007ea7]" /> : 
                          <Folder className="h-4 w-4 text-[#007ea7]" />
                        }
                        <span className="text-sm font-medium text-[#EEEEEE]">
                          {folderPath === 'root' ? 'Root Directory' : folderPath}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {folderFiles.length}
                        </Badge>
                      </div>
                      
                      {expandedFolders.has(folderPath) && (
                        <div className="ml-6 space-y-1">
                          {folderFiles.map(file => {
                            const extension = getFileExtension(file.name);
                            const isSelected = selectedFile && selectedFile.path === file.path;
                            
                            return (
                              <div
                                key={file.path}
                                className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                                  isSelected 
                                    ? 'bg-[#007ea7]/20 border border-[#007ea7]' 
                                    : 'hover:bg-[#2A4759]/30'
                                }`}
                                onClick={() => handleFileSelect(file)}
                              >
                                <span className="text-lg">{getFileIcon(extension)}</span>
                                <span className="text-sm text-[#EEEEEE] flex-1">{file.name}</span>
                                <Badge 
                                  className={`text-xs ${getBadgeColor(extension)}`}
                                >
                                  {extension.toUpperCase()}
                                </Badge>
                                <span className="text-xs text-[#EEEEEE]/50">
                                  {file.size ? `${Math.round(file.size / 1024)}KB` : ''}
                                </span>
                              </div>
                            );
                          })}
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
    </div>
  );
};

export default YAMLFileManager;
