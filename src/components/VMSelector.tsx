
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, Check } from "lucide-react";

export interface VMSelectorProps {
  onSelectionChange: (vms: string[]) => void;
  selectedVMs?: string[];
  selectedTypes?: string[];
}

const VMSelector: React.FC<VMSelectorProps> = ({ 
  onSelectionChange, 
  selectedVMs = [], 
  selectedTypes = [] 
}) => {
  const [selectedVMList, setSelectedVMList] = useState<string[]>(selectedVMs);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch VMs from API
  const { data: vmsData = [], isLoading } = useQuery({
    queryKey: ['vms'],
    queryFn: async () => {
      try {
        const response = await fetch('/api/vms');
        if (!response.ok) {
          console.error('Error fetching VMs:', await response.text());
          throw new Error('Failed to fetch VMs');
        }
        const data = await response.json();
        console.log('Loaded VMs from API:', data);
        return data || [];
      } catch (error) {
        console.error('Error fetching VMs:', error);
        return [];
      }
    },
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (JSON.stringify(selectedVMs) !== JSON.stringify(selectedVMList)) {
      setSelectedVMList(selectedVMs);
    }
  }, [selectedVMs]);

  const handleVMChange = (vmName: string, checked: boolean) => {
    const updatedSelection = checked
      ? [...selectedVMList, vmName]
      : selectedVMList.filter(vm => vm !== vmName);
    
    setSelectedVMList(updatedSelection);
    onSelectionChange(updatedSelection);
  };

  const handleSelectAll = () => {
    const allVMNames = vmsData.map((vm: any) => vm.name);
    setSelectedVMList(allVMNames);
    onSelectionChange(allVMNames);
  };

  const handleDeselectAll = () => {
    setSelectedVMList([]);
    onSelectionChange([]);
  };

  if (isLoading) {
    return <div className="text-foreground">Loading VM list...</div>;
  }

  return (
    <div className="space-y-3">
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="outline" 
            className="w-full justify-between bg-input border-primary text-foreground hover:bg-input/80"
          >
            <span>
              {selectedVMList.length === 0 
                ? "Select VMs" 
                : `${selectedVMList.length} VM${selectedVMList.length !== 1 ? 's' : ''} selected`
              }
            </span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        
        <DropdownMenuContent 
          className="w-80 max-h-80 overflow-hidden bg-slate-100 border border-slate-300 shadow-lg"
          align="start"
        >
          {/* Select All / Deselect All buttons */}
          <div className="flex gap-2 p-2 border-b border-slate-300">
            <Button
              type="button"
              onClick={handleSelectAll}
              size="sm"
              className="flex-1 text-xs"
              style={{ backgroundColor: '#d4c2a4', color: 'white' }}
            >
              Select All
            </Button>
            <Button
              type="button"
              onClick={handleDeselectAll}
              size="sm"
              variant="outline"
              className="flex-1 text-xs"
              style={{ borderColor: '#d4c2a4', color: '#d4c2a4' }}
            >
              Deselect All
            </Button>
          </div>

          {/* Scrollable VM list */}
          <div className="max-h-60 overflow-y-auto p-2">
            {vmsData.length === 0 ? (
              <p className="text-sm text-slate-600 p-2">No VMs available in inventory.</p>
            ) : (
              <div className="space-y-2">
                {vmsData.map((vm: any) => (
                  <div 
                    key={vm.name} 
                    className="flex items-center space-x-3 p-2 rounded hover:text-white cursor-pointer transition-colors"
                    style={{ 
                      ':hover': { backgroundColor: '#d4c2a4' }
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#d4c2a4';
                      e.currentTarget.style.color = 'white';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '';
                      e.currentTarget.style.color = '';
                    }}
                    onClick={() => handleVMChange(vm.name, !selectedVMList.includes(vm.name))}
                  >
                    <Checkbox 
                      id={`vm-${vm.name}`}
                      checked={selectedVMList.includes(vm.name)}
                      onCheckedChange={(checked) => handleVMChange(vm.name, checked === true)}
                      className="pointer-events-none"
                    />
                    <Label 
                      htmlFor={`vm-${vm.name}`} 
                      className="text-slate-900 cursor-pointer flex-1 pointer-events-none"
                    >
                      {vm.name}
                      {vm.type && <span className="text-xs text-slate-600 ml-2">({vm.type})</span>}
                    </Label>
                    {selectedVMList.includes(vm.name) && (
                      <Check className="h-4 w-4" style={{ color: '#d4c2a4' }} />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Selected VMs Display */}
      {selectedVMList.length > 0 && (
        <div className="bg-card/20 rounded-md p-3 border border-primary/30">
          <div className="text-sm font-medium text-foreground mb-2">
            Selected VMs ({selectedVMList.length}):
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedVMList.map((vmName) => (
              <span 
                key={vmName}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md"
                style={{ backgroundColor: '#d4c2a4', color: 'white' }}
              >
                {vmName}
                <button
                  onClick={() => handleVMChange(vmName, false)}
                  className="hover:bg-black/20 rounded-full p-0.5"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VMSelector;
