
import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { FileEdit, Save, RefreshCw, Plus, Trash2, Eye, AlertTriangle, CheckCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const YAMLEditor = ({ selectedFile, currentBranch }) => {
  const [fileContent, setFileContent] = useState({});
  const [originalContent, setOriginalContent] = useState({});
  const [validationErrors, setValidationErrors] = useState([]);
  const [isValid, setIsValid] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [expandedPaths, setExpandedPaths] = useState(new Set());
  const { toast } = useToast();

  useEffect(() => {
    if (selectedFile) {
      loadFileContent();
    }
  }, [selectedFile]);

  useEffect(() => {
    validateContent();
    checkForChanges();
  }, [fileContent, originalContent]);

  const loadFileContent = async () => {
    if (!selectedFile) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/api/git/file-content?path=${encodeURIComponent(selectedFile.path)}`);
      if (response.ok) {
        const data = await response.json();
        setFileContent(data.content || {});
        setOriginalContent(data.content || {});
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load file content",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const validateContent = () => {
    try {
      // Simulate YAML validation
      const errors = [];
      const validateObject = (obj, path = '') => {
        for (const [key, value] of Object.entries(obj)) {
          const currentPath = path ? `${path}.${key}` : key;
          
          // Check for invalid characters in keys
          if (typeof key === 'string' && key.includes(' ') && !key.startsWith('"')) {
            errors.push({
              path: currentPath,
              message: `Key "${key}" contains spaces and should be quoted`
            });
          }
          
          // Recursively validate nested objects
          if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            validateObject(value, currentPath);
          }
        }
      };
      
      validateObject(fileContent);
      setValidationErrors(errors);
      setIsValid(errors.length === 0);
    } catch (error) {
      setValidationErrors([{ path: 'root', message: 'Invalid YAML structure' }]);
      setIsValid(false);
    }
  };

  const checkForChanges = () => {
    setHasChanges(JSON.stringify(fileContent) !== JSON.stringify(originalContent));
  };

  const updateValue = (path, newValue, dataType = 'string') => {
    const pathArray = path.split('.');
    const newContent = JSON.parse(JSON.stringify(fileContent));
    
    let current = newContent;
    for (let i = 0; i < pathArray.length - 1; i++) {
      current = current[pathArray[i]];
    }
    
    const finalKey = pathArray[pathArray.length - 1];
    
    // Convert value based on data type
    switch (dataType) {
      case 'number':
        current[finalKey] = Number(newValue);
        break;
      case 'boolean':
        current[finalKey] = Boolean(newValue);
        break;
      case 'array':
        current[finalKey] = newValue.split(',').map(item => item.trim());
        break;
      default:
        current[finalKey] = newValue;
    }
    
    setFileContent(newContent);
  };

  const addNewKey = (parentPath, keyName, value, dataType = 'string') => {
    if (!keyName) return;
    
    const newContent = JSON.parse(JSON.stringify(fileContent));
    
    if (parentPath === '') {
      newContent[keyName] = convertValue(value, dataType);
    } else {
      const pathArray = parentPath.split('.');
      let current = newContent;
      for (const segment of pathArray) {
        current = current[segment];
      }
      current[keyName] = convertValue(value, dataType);
    }
    
    setFileContent(newContent);
  };

  const deleteKey = (path) => {
    const pathArray = path.split('.');
    const newContent = JSON.parse(JSON.stringify(fileContent));
    
    let current = newContent;
    for (let i = 0; i < pathArray.length - 1; i++) {
      current = current[pathArray[i]];
    }
    
    delete current[pathArray[pathArray.length - 1]];
    setFileContent(newContent);
  };

  const convertValue = (value, dataType) => {
    switch (dataType) {
      case 'number':
        return Number(value) || 0;
      case 'boolean':
        return Boolean(value);
      case 'array':
        return typeof value === 'string' ? value.split(',').map(item => item.trim()) : value;
      case 'object':
        return {};
      default:
        return value;
    }
  };

  const getDataType = (value) => {
    if (typeof value === 'number') return 'number';
    if (typeof value === 'boolean') return 'boolean';
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object' && value !== null) return 'object';
    return 'string';
  };

  const toggleExpanded = (path) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedPaths(newExpanded);
  };

  const saveFile = async () => {
    if (!selectedFile || !isValid) {
      toast({
        title: "Cannot Save",
        description: "Please fix validation errors before saving",
        variant: "destructive"
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/git/save-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedFile.path,
          content: fileContent,
          branch: currentBranch
        })
      });

      if (response.ok) {
        setOriginalContent(JSON.parse(JSON.stringify(fileContent)));
        toast({
          title: "Success",
          description: "File saved successfully"
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save file",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderKeyValueEditor = (obj, parentPath = '', depth = 0) => {
    return Object.entries(obj).map(([key, value]) => {
      const currentPath = parentPath ? `${parentPath}.${key}` : key;
      const dataType = getDataType(value);
      const isExpanded = expandedPaths.has(currentPath);
      
      return (
        <div key={currentPath} className={`border-l-2 border-[#007ea7]/30 pl-${depth * 2 + 2} mb-2`}>
          <div className="flex items-center gap-2 p-2 bg-[#2A4759]/20 rounded">
            <span className="font-mono text-sm text-[#007ea7] min-w-[120px]">{key}:</span>
            
            {dataType === 'object' ? (
              <div className="flex items-center gap-2 flex-1">
                <Badge variant="outline" className="text-xs">Object</Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleExpanded(currentPath)}
                  className="h-6 px-2"
                >
                  {isExpanded ? '▼' : '▶'}
                </Button>
              </div>
            ) : (
              <>
                {dataType === 'boolean' ? (
                  <Switch
                    checked={value}
                    onCheckedChange={(checked) => updateValue(currentPath, checked, 'boolean')}
                  />
                ) : dataType === 'array' ? (
                  <Input
                    value={Array.isArray(value) ? value.join(', ') : ''}
                    onChange={(e) => updateValue(currentPath, e.target.value, 'array')}
                    placeholder="item1, item2, item3"
                    className="flex-1 bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
                  />
                ) : (
                  <Input
                    value={value || ''}
                    onChange={(e) => updateValue(currentPath, e.target.value, dataType)}
                    type={dataType === 'number' ? 'number' : 'text'}
                    className="flex-1 bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
                  />
                )}
                
                <Badge variant="outline" className="text-xs">
                  {dataType.toUpperCase()}
                </Badge>
                
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteKey(currentPath)}
                  className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
          
          {dataType === 'object' && isExpanded && (
            <div className="mt-2">
              {renderKeyValueEditor(value, currentPath, depth + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  if (!selectedFile) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center text-[#EEEEEE]/70">
          <FileEdit className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select a file to start editing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileEdit className="h-5 w-5 text-[#007ea7]" />
          <h3 className="text-lg font-semibold text-[#EEEEEE]">{selectedFile.name}</h3>
          {hasChanges && <Badge variant="outline" className="text-yellow-400">Modified</Badge>}
          {isValid ? (
            <CheckCircle className="h-4 w-4 text-green-400" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-red-400" />
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPreviewMode(!previewMode)}
            className="border-[#007ea7]/30"
          >
            <Eye className="h-4 w-4 mr-2" />
            {previewMode ? 'Edit' : 'Preview'}
          </Button>
          <Button
            size="sm"
            onClick={loadFileContent}
            disabled={isLoading}
            variant="outline"
            className="border-[#007ea7]/30"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            onClick={saveFile}
            disabled={!hasChanges || !isValid || isLoading}
            className="bg-[#007ea7] hover:bg-[#005f82]"
          >
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <Card className="bg-red-900/20 border-red-500/30">
          <CardHeader>
            <CardTitle className="text-red-400 text-sm">Validation Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {validationErrors.map((error, index) => (
                <div key={index} className="text-sm text-red-300">
                  <span className="font-mono">{error.path}:</span> {error.message}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6">
        <Card className="bg-[#00171f]/90 backdrop-blur-sm border-[#007ea7]/30">
          <CardHeader>
            <CardTitle className="text-[#EEEEEE]">
              {previewMode ? 'YAML Preview' : 'Key-Value Editor'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px] w-full">
              {isLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-[#EEEEEE]">Loading content...</div>
                </div>
              ) : previewMode ? (
                <pre className="text-sm text-[#EEEEEE] font-mono whitespace-pre-wrap">
                  {JSON.stringify(fileContent, null, 2)}
                </pre>
              ) : (
                <div className="space-y-2">
                  {renderKeyValueEditor(fileContent)}
                  
                  <div className="mt-6 p-4 border-2 border-dashed border-[#007ea7]/30 rounded">
                    <AddNewKeyForm onAdd={addNewKey} />
                  </div>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const AddNewKeyForm = ({ onAdd }) => {
  const [keyName, setKeyName] = useState('');
  const [value, setValue] = useState('');
  const [dataType, setDataType] = useState('string');
  const [parentPath, setParentPath] = useState('');

  const handleAdd = () => {
    if (keyName) {
      onAdd(parentPath, keyName, value, dataType);
      setKeyName('');
      setValue('');
      setParentPath('');
    }
  };

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-[#EEEEEE]">Add New Key</h4>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Input
          placeholder="Parent path (optional)"
          value={parentPath}
          onChange={(e) => setParentPath(e.target.value)}
          className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
        />
        <Input
          placeholder="Key name"
          value={keyName}
          onChange={(e) => setKeyName(e.target.value)}
          className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
        />
        <Input
          placeholder="Value"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]"
        />
        <div className="flex gap-1">
          <Select value={dataType} onValueChange={setDataType}>
            <SelectTrigger className="bg-[#2A4759]/50 border-[#007ea7]/30 text-[#EEEEEE]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#2A4759] border-[#007ea7]/30">
              <SelectItem value="string" className="text-[#EEEEEE]">String</SelectItem>
              <SelectItem value="number" className="text-[#EEEEEE]">Number</SelectItem>
              <SelectItem value="boolean" className="text-[#EEEEEE]">Boolean</SelectItem>
              <SelectItem value="array" className="text-[#EEEEEE]">Array</SelectItem>
              <SelectItem value="object" className="text-[#EEEEEE]">Object</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" onClick={handleAdd} className="bg-[#007ea7] hover:bg-[#005f82]">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default YAMLEditor;
