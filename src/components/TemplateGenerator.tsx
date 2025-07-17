import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Save, FileText } from 'lucide-react';

const TemplateGenerator: React.FC = () => {
  const { toast } = useToast();
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateContent, setTemplateContent] = useState('');

  const handleSaveTemplate = () => {
    if (!templateName || !templateDescription || !templateContent) {
      toast({
        title: "Error",
        description: "Please fill in all fields.",
        variant: "destructive",
      });
      return;
    }

    // Basic validation for YAML/JSON content
    try {
      JSON.parse(templateContent);
    } catch (e) {
      toast({
        title: "Error",
        description: "Invalid JSON content. Please ensure your template content is valid JSON.",
        variant: "destructive",
      });
      return;
    }

    // Here you would typically send the template data to your backend
    // For this example, we'll just show a success message
    toast({
      title: "Success",
      description: `Template "${templateName}" saved successfully!`,
    });

    // Clear the form
    setTemplateName('');
    setTemplateDescription('');
    setTemplateContent('');
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold gradient-heading mb-6">Template Generator</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-t-lg">
              <CardTitle className="text-primary text-lg font-semibold flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Template Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-6">
              <div className="space-y-2">
                <Label htmlFor="templateName" className="text-foreground font-medium">Template Name</Label>
                <Input
                  id="templateName"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="Enter template name"
                  className="bg-input border-border text-foreground"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="templateDescription" className="text-foreground font-medium">Description</Label>
                <Textarea
                  id="templateDescription"
                  value={templateDescription}
                  onChange={(e) => setTemplateDescription(e.target.value)}
                  placeholder="Enter template description"
                  className="bg-input border-border text-foreground min-h-[100px]"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="templateContent" className="text-foreground font-medium">Template Content</Label>
                <Textarea
                  id="templateContent"
                  value={templateContent}
                  onChange={(e) => setTemplateContent(e.target.value)}
                  placeholder="Enter template content (YAML/JSON)"
                  className="bg-input border-border text-foreground min-h-[200px] font-mono"
                />
              </div>
              
              <Button
                onClick={handleSaveTemplate}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-medium py-2"
              >
                <Save className="mr-2 h-4 w-4" />
                Save Template
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="bg-gradient-to-r from-accent/10 to-primary/10 rounded-t-lg">
              <CardTitle className="text-primary text-lg font-semibold">Template Preview</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="bg-slate-900 text-gray-200 p-4 rounded-md font-mono text-sm min-h-[300px] border border-border">
                {templateContent || 'Template content will appear here...'}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TemplateGenerator;
