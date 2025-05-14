
import { useState, useEffect } from "react";
import { Search, File, Folder, ChevronRight, ChevronDown, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { 
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from "@/components/ui/accordion";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

// Mock data structure for files
const mockFileStructure = {
  "ft-001": [
    { path: "config/app.config.json", type: "file" },
    { path: "config/db.config.json", type: "file" },
    { path: "src/modules/core/", type: "folder", children: [
      { path: "src/modules/core/main.py", type: "file" },
      { path: "src/modules/core/utils.py", type: "file" },
    ]},
    { path: "src/modules/api/", type: "folder", children: [
      { path: "src/modules/api/routes.py", type: "file" },
      { path: "src/modules/api/middleware.py", type: "file" }
    ]},
    { path: "tests/unit/", type: "folder", children: [
      { path: "tests/unit/test_core.py", type: "file" }
    ]}
  ],
  "ft-002": [
    { path: "auth/login.py", type: "file" },
    { path: "auth/register.py", type: "file" },
    { path: "auth/middleware.py", type: "file" },
    { path: "templates/", type: "folder", children: [
      { path: "templates/login.html", type: "file" },
      { path: "templates/register.html", type: "file" }
    ]}
  ],
  "ft-003": [
    { path: "api/v1/", type: "folder", children: [
      { path: "api/v1/users.py", type: "file" },
      { path: "api/v1/products.py", type: "file" }
    ]},
    { path: "api/v2/", type: "folder", children: [
      { path: "api/v2/users.py", type: "file" },
      { path: "api/v2/products.py", type: "file" }
    ]},
    { path: "api/docs/swagger.json", type: "file" }
  ],
  "ft-004": [
    { path: "frontend/components/", type: "folder", children: [
      { path: "frontend/components/Button.js", type: "file" },
      { path: "frontend/components/Form.js", type: "file" },
      { path: "frontend/components/Modal.js", type: "file" }
    ]},
    { path: "frontend/pages/", type: "folder", children: [
      { path: "frontend/pages/Home.js", type: "file" },
      { path: "frontend/pages/About.js", type: "file" },
      { path: "frontend/pages/Contact.js", type: "file" }
    ]},
    { path: "frontend/app.js", type: "file" },
    { path: "frontend/index.html", type: "file" }
  ],
  "ft-005": [
    { path: "data/pipelines/", type: "folder", children: [
      { path: "data/pipelines/extract.py", type: "file" },
      { path: "data/pipelines/transform.py", type: "file" },
      { path: "data/pipelines/load.py", type: "file" }
    ]},
    { path: "data/analysis/", type: "folder", children: [
      { path: "data/analysis/reports.py", type: "file" },
      { path: "data/analysis/visualization.py", type: "file" }
    ]},
    { path: "data/config.yaml", type: "file" }
  ]
};

interface FileSelectorProps {
  selectedFT: string | null;
  selectedFiles: string[];
  onSelectFiles: (files: string[]) => void;
}

export const FileSelector = ({ selectedFT, selectedFiles, onSelectFiles }: FileSelectorProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedFolders, setExpandedFolders] = useState<string[]>([]);
  const [availableFiles, setAvailableFiles] = useState<any[]>([]);
  
  // Set available files based on selected FT
  useEffect(() => {
    if (selectedFT && mockFileStructure[selectedFT as keyof typeof mockFileStructure]) {
      setAvailableFiles(mockFileStructure[selectedFT as keyof typeof mockFileStructure]);
    } else {
      setAvailableFiles([]);
    }
  }, [selectedFT]);

  // Toggle folder expansion
  const toggleFolder = (folderPath: string) => {
    setExpandedFolders(prev => 
      prev.includes(folderPath) 
        ? prev.filter(p => p !== folderPath)
        : [...prev, folderPath]
    );
  };

  // Handle file selection
  const toggleFile = (filePath: string) => {
    onSelectFiles(
      selectedFiles.includes(filePath)
        ? selectedFiles.filter(p => p !== filePath)
        : [...selectedFiles, filePath]
    );
  };

  // Select all files
  const selectAll = () => {
    const allFilePaths = getAllFilePaths(availableFiles);
    onSelectFiles(allFilePaths);
  };

  // Clear selection
  const clearSelection = () => {
    onSelectFiles([]);
  };

  // Helper to get all file paths from the structure
  const getAllFilePaths = (items: any[]): string[] => {
    return items.reduce((paths: string[], item) => {
      if (item.type === 'file') {
        paths.push(item.path);
      } else if (item.type === 'folder' && item.children) {
        paths = [...paths, ...getAllFilePaths(item.children)];
      }
      return paths;
    }, []);
  };

  // Filter files based on search term
  const filterFileStructure = (items: any[]): any[] => {
    if (!searchTerm) return items;
    
    return items.reduce((filtered: any[], item) => {
      if (item.type === 'file' && item.path.toLowerCase().includes(searchTerm.toLowerCase())) {
        filtered.push(item);
      } else if (item.type === 'folder' && item.children) {
        const filteredChildren = filterFileStructure(item.children);
        if (filteredChildren.length > 0) {
          filtered.push({
            ...item,
            children: filteredChildren
          });
        }
      }
      return filtered;
    }, []);
  };

  const filteredFiles = filterFileStructure(availableFiles);

  // Recursive component for file tree
  const renderFileTree = (items: any[], level = 0) => {
    return items.map(item => {
      if (item.type === 'file') {
        return (
          <div 
            key={item.path} 
            className={`flex items-center py-1 pl-${level * 4} hover:bg-secondary/30 rounded-sm cursor-pointer`}
            onClick={() => toggleFile(item.path)}
          >
            <Checkbox 
              checked={selectedFiles.includes(item.path)} 
              onCheckedChange={() => toggleFile(item.path)}
              className="mr-2"
            />
            <File className="h-4 w-4 mr-2 text-muted-foreground" />
            <span className="text-sm">{item.path.split('/').pop()}</span>
          </div>
        );
      } else if (item.type === 'folder') {
        const isExpanded = expandedFolders.includes(item.path);
        return (
          <div key={item.path} className="my-1">
            <div 
              className={`flex items-center py-1 pl-${level * 4} hover:bg-secondary/30 rounded-sm cursor-pointer`}
              onClick={() => toggleFolder(item.path)}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 mr-2" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2" />
              )}
              <Folder className="h-4 w-4 mr-2 text-muted-foreground" />
              <span className="text-sm">{item.path.split('/').pop() || item.path}</span>
            </div>
            {isExpanded && item.children && (
              <div className="ml-4">
                {renderFileTree(item.children, level + 1)}
              </div>
            )}
          </div>
        );
      }
      return null;
    });
  };

  if (!selectedFT) {
    return (
      <div className="flex items-center justify-center h-40 border rounded-md bg-muted/20">
        <p className="text-muted-foreground">Select a Feature Team first</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search files..."
            className="pl-8 w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex space-x-2 ml-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="whitespace-nowrap"
            onClick={selectAll}
          >
            Select All
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            className="whitespace-nowrap"
            onClick={clearSelection}
            disabled={selectedFiles.length === 0}
          >
            Clear
          </Button>
        </div>
      </div>

      <ScrollArea className="h-[300px] border rounded-md p-2">
        {availableFiles.length > 0 ? (
          <div className="space-y-1">
            {renderFileTree(filteredFiles)}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">No files available</p>
          </div>
        )}
      </ScrollArea>

      {selectedFiles.length > 0 && (
        <div className="p-3 bg-secondary/20 rounded-md">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">Selected Files ({selectedFiles.length})</h4>
            <Button variant="ghost" size="sm" onClick={clearSelection}>
              Clear
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
