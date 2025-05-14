
import { useState } from "react";
import { Check, Plus, Search, Server } from "lucide-react";
import { Input } from "@/components/ui/input";
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

// Mock data for Target VMs
const mockTargets = [
  { id: "vm-001", name: "web-server-01", ip: "192.168.1.101", environment: "dev", status: "online" },
  { id: "vm-002", name: "web-server-02", ip: "192.168.1.102", environment: "dev", status: "online" },
  { id: "vm-003", name: "app-server-01", ip: "192.168.1.103", environment: "staging", status: "online" },
  { id: "vm-004", name: "app-server-02", ip: "192.168.1.104", environment: "staging", status: "offline" },
  { id: "vm-005", name: "db-server-01", ip: "192.168.1.105", environment: "prod", status: "online" },
  { id: "vm-006", name: "db-server-02", ip: "192.168.1.106", environment: "prod", status: "online" },
  { id: "vm-007", name: "cache-server-01", ip: "192.168.1.107", environment: "dev", status: "online" },
  { id: "vm-008", name: "cache-server-02", ip: "192.168.1.108", environment: "prod", status: "maintenance" }
];

interface TargetSelectorProps {
  selectedTargets: string[];
  onSelectTargets: (targets: string[]) => void;
}

export const TargetSelector = ({ selectedTargets, onSelectTargets }: TargetSelectorProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [newTarget, setNewTarget] = useState({ name: "", ip: "", environment: "dev" });
  const [openDialog, setOpenDialog] = useState(false);
  const [environmentFilter, setEnvironmentFilter] = useState<string | null>(null);
  
  // Filter targets based on search term and environment filter
  const filteredTargets = mockTargets.filter(target => {
    const matchesSearch = 
      target.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
      target.ip.includes(searchTerm);
    
    const matchesEnvironment = environmentFilter ? target.environment === environmentFilter : true;
    
    return matchesSearch && matchesEnvironment;
  });

  // Toggle target selection
  const toggleTarget = (targetId: string) => {
    onSelectTargets(
      selectedTargets.includes(targetId)
        ? selectedTargets.filter(id => id !== targetId)
        : [...selectedTargets, targetId]
    );
  };

  // Toggle all targets
  const toggleAll = (checked: boolean) => {
    if (checked) {
      const allFilteredIds = filteredTargets.map(target => target.id);
      onSelectTargets(allFilteredIds);
    } else {
      onSelectTargets([]);
    }
  };

  // Add new target (mock functionality)
  const handleAddTarget = () => {
    // In a real application, this would send a request to the backend
    // For now, we'll just close the dialog
    setOpenDialog(false);
    setNewTarget({ name: "", ip: "", environment: "dev" });
  };

  // Get environments for filter
  const environments = Array.from(new Set(mockTargets.map(target => target.environment)));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search targets..."
            className="pl-8"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <Dialog open={openDialog} onOpenChange={setOpenDialog}>
          <DialogTrigger asChild>
            <Button size="sm" className="ml-2">
              <Plus className="h-4 w-4 mr-1" /> Add VM
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Target VM</DialogTitle>
              <DialogDescription>
                Enter the details of the target VM you want to add.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">VM Name</Label>
                <Input 
                  id="name"
                  value={newTarget.name}
                  onChange={(e) => setNewTarget({...newTarget, name: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="ip">IP Address</Label>
                <Input 
                  id="ip"
                  value={newTarget.ip}
                  onChange={(e) => setNewTarget({...newTarget, ip: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="env">Environment</Label>
                <select 
                  id="env"
                  className="w-full rounded-md border border-input bg-background px-3 py-2"
                  value={newTarget.environment}
                  onChange={(e) => setNewTarget({...newTarget, environment: e.target.value})}
                >
                  <option value="dev">Development</option>
                  <option value="staging">Staging</option>
                  <option value="prod">Production</option>
                </select>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpenDialog(false)}>Cancel</Button>
              <Button onClick={handleAddTarget}>Add VM</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <Badge 
          variant={environmentFilter === null ? "default" : "outline"}
          className="cursor-pointer"
          onClick={() => setEnvironmentFilter(null)}
        >
          All
        </Badge>
        {environments.map(env => (
          <Badge 
            key={env}
            variant={environmentFilter === env ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setEnvironmentFilter(env === environmentFilter ? null : env)}
          >
            {env.charAt(0).toUpperCase() + env.slice(1)}
          </Badge>
        ))}
      </div>

      <div className="flex items-center mb-2">
        <Checkbox 
          id="selectAll"
          checked={filteredTargets.length > 0 && selectedTargets.length === filteredTargets.length}
          onCheckedChange={toggleAll}
        />
        <label htmlFor="selectAll" className="ml-2 text-sm font-medium">
          Select All
        </label>
      </div>

      <ScrollArea className="h-[240px]">
        <div className="space-y-2">
          {filteredTargets.map(target => (
            <Card 
              key={target.id}
              className={`cursor-pointer transition-all ${
                selectedTargets.includes(target.id) ? "border-primary" : ""
              } ${target.status !== "online" ? "opacity-60" : ""}`}
              onClick={() => toggleTarget(target.id)}
            >
              <CardContent className="p-4 flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="mt-1">
                    <Server className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div>
                    <h4 className="font-medium">{target.name}</h4>
                    <p className="text-sm text-muted-foreground">{target.ip}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline">
                        {target.environment}
                      </Badge>
                      <Badge 
                        variant="outline" 
                        className={
                          target.status === "online" ? "text-deploy-success border-deploy-success" :
                          target.status === "offline" ? "text-deploy-error border-deploy-error" :
                          "text-deploy-pending border-deploy-pending"
                        }
                      >
                        {target.status}
                      </Badge>
                    </div>
                  </div>
                </div>
                <Checkbox 
                  checked={selectedTargets.includes(target.id)} 
                  onCheckedChange={() => toggleTarget(target.id)}
                  className="mt-1"
                />
              </CardContent>
            </Card>
          ))}
          
          {filteredTargets.length === 0 && (
            <div className="flex items-center justify-center h-20 border rounded-md">
              <p className="text-muted-foreground">No targets found</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
