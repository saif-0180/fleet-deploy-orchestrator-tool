
import { useState } from "react";
import { Check, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { 
  Select, 
  SelectContent, 
  SelectGroup, 
  SelectItem, 
  SelectLabel, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

// Mock data for Feature Teams
const mockFeatureTeams = [
  { id: "ft-001", name: "FT Alpha", description: "Core platform services" },
  { id: "ft-002", name: "FT Beta", description: "User authentication and identity" },
  { id: "ft-003", name: "FT Gamma", description: "API services and integrations" },
  { id: "ft-004", name: "FT Delta", description: "Frontend applications" },
  { id: "ft-005", name: "FT Epsilon", description: "Data pipeline and analytics" }
];

interface FTSelectorProps {
  selectedFT: string | null;
  onSelectFT: (ftId: string) => void;
}

export const FTSelector = ({ selectedFT, onSelectFT }: FTSelectorProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  
  // Filter feature teams based on search term
  const filteredFTs = mockFeatureTeams.filter(ft => 
    ft.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    ft.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <Select value={selectedFT || undefined} onValueChange={onSelectFT}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select Feature Team" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Feature Teams</SelectLabel>
            {mockFeatureTeams.map(ft => (
              <SelectItem key={ft.id} value={ft.id}>
                {ft.name}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>

      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search Feature Teams..."
          className="pl-8"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="space-y-2 mt-2">
        {filteredFTs.map(ft => (
          <Card 
            key={ft.id}
            className={`cursor-pointer transition-all ${
              selectedFT === ft.id ? "border-primary" : ""
            }`}
            onClick={() => onSelectFT(ft.id)}
          >
            <CardContent className="p-4 flex items-start justify-between">
              <div>
                <h4 className="font-medium">{ft.name}</h4>
                <p className="text-sm text-muted-foreground">{ft.description}</p>
              </div>
              {selectedFT === ft.id && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
