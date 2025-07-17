
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
    return <div className="text-[#00171f]">Loading VM list...</div>;
  }

  return (
    <div className="space-y-3">
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <DropdownMenuTrigger asChild>
          <Button 
            variant="outline" 
            className="w-full justify-between bg-white border-[#00171f]/30 text-[#00171f] hover:bg-[#00a7e1]/10"
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
          className="w-80 max-h-80 overflow-hidden bg-white border border-[#00171f]/20 shadow-lg"
          align="start"
        >
          {/* Select All / Deselect All buttons */}
          <div className="flex gap-2 p-2 border-b border-[#00171f]/20">
            <Button
              type="button"
              onClick={handleSelectAll}
              size="sm"
              className="flex-1 bg-[#00a7e1] text-white hover:bg-[#00a7e1]/90 text-xs"
            >
              Select All
            </Button>
            <Button
              type="button"
              onClick={handleDeselectAll}
              size="sm"
              variant="outline"
              className="flex-1 border-[#00171f]/30 text-[#00171f] hover:bg-[#00171f]/10 text-xs"
            >
              Deselect All
            </Button>
          </div>

          {/* Scrollable VM list */}
          <div className="max-h-60 overflow-y-auto p-2">
            {vmsData.length === 0 ? (
              <p className="text-sm text-[#00171f]/60 p-2">No VMs available in inventory.</p>
            ) : (
              <div className="space-y-2">
                {vmsData.map((vm: any) => (
                  <div 
                    key={vm.name} 
                    className="flex items-center space-x-3 p-2 rounded hover:bg-[#00a7e1]/10 cursor-pointer"
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
                      className="text-[#00171f] cursor-pointer flex-1 pointer-events-none"
                    >
                      {vm.name}
                      {vm.type && <span className="text-xs text-[#00171f]/60 ml-2">({vm.type})</span>}
                    </Label>
                    {selectedVMList.includes(vm.name) && (
                      <Check className="h-4 w-4 text-[#00a7e1]" />
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
        <div className="bg-[#003459]/20 rounded-md p-3 border border-[#00a7e1]/30">
          <div className="text-sm font-medium text-[#00171f] mb-2">
            Selected VMs ({selectedVMList.length}):
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedVMList.map((vmName) => (
              <span 
                key={vmName}
                className="inline-flex items-center gap-1 px-2 py-1 bg-[#00a7e1] text-white text-xs rounded-md"
              >
                {vmName}
                <button
                  onClick={() => handleVMChange(vmName, false)}
                  className="hover:bg-[#00171f]/20 rounded-full p-0.5"
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
