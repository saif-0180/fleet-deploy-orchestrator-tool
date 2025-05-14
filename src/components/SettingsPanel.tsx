
import { useState } from "react";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardFooter, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Switch } from "@/components/ui/switch";

const SettingsPanel = () => {
  const { toast } = useToast();
  
  // General settings
  const [dockerSettings, setDockerSettings] = useState({
    registryUrl: "registry.example.com",
    username: "docker-user",
    registryEnabled: true
  });
  
  // Ansible settings
  const [ansibleSettings, setAnsibleSettings] = useState({
    ansiblePath: "/usr/bin/ansible",
    playbookPath: "/etc/ansible/playbooks",
    timeout: "300",
    useCustomInventory: false,
    inventoryPath: "/etc/ansible/hosts"
  });
  
  // Target settings
  const [sshSettings, setSSHSettings] = useState({
    defaultUser: "deploy",
    keyPath: "~/.ssh/id_rsa",
    port: "22",
    timeout: "30"
  });

  // Notification settings
  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    emailRecipients: "admin@example.com",
    slackNotifications: false,
    slackWebhook: "",
    notifyOnSuccess: true,
    notifyOnFailure: true
  });

  const handleSaveGeneralSettings = () => {
    toast({
      title: "Settings Saved",
      description: "Docker registry settings have been updated.",
    });
  };

  const handleSaveAnsibleSettings = () => {
    toast({
      title: "Settings Saved",
      description: "Ansible configuration has been updated.",
    });
  };

  const handleSaveTargetSettings = () => {
    toast({
      title: "Settings Saved",
      description: "Target SSH settings have been updated.",
    });
  };

  const handleSaveNotificationSettings = () => {
    toast({
      title: "Settings Saved",
      description: "Notification preferences have been updated.",
    });
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="ansible">Ansible</TabsTrigger>
          <TabsTrigger value="targets">Target SSH</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>
        
        {/* General Settings Tab */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>Docker Registry Settings</CardTitle>
              <CardDescription>
                Configure your Docker registry settings for container deployments
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="registry-url">Registry URL</Label>
                <Input 
                  id="registry-url" 
                  value={dockerSettings.registryUrl}
                  onChange={e => setDockerSettings({...dockerSettings, registryUrl: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="registry-username">Username</Label>
                <Input 
                  id="registry-username" 
                  value={dockerSettings.username}
                  onChange={e => setDockerSettings({...dockerSettings, username: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="registry-password">Password</Label>
                <Input 
                  id="registry-password" 
                  type="password" 
                  placeholder="••••••••"
                />
              </div>
              
              <div className="flex items-center space-x-2 pt-2">
                <Switch 
                  id="use-registry" 
                  checked={dockerSettings.registryEnabled}
                  onCheckedChange={checked => setDockerSettings({...dockerSettings, registryEnabled: checked})}
                />
                <Label htmlFor="use-registry">Enable Docker Registry</Label>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handleSaveGeneralSettings}>Save Changes</Button>
            </CardFooter>
          </Card>
        </TabsContent>
        
        {/* Ansible Settings Tab */}
        <TabsContent value="ansible">
          <Card>
            <CardHeader>
              <CardTitle>Ansible Configuration</CardTitle>
              <CardDescription>
                Configure Ansible settings for deployment automation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ansible-path">Ansible Path</Label>
                <Input 
                  id="ansible-path" 
                  value={ansibleSettings.ansiblePath}
                  onChange={e => setAnsibleSettings({...ansibleSettings, ansiblePath: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="playbook-path">Default Playbook Path</Label>
                <Input 
                  id="playbook-path" 
                  value={ansibleSettings.playbookPath}
                  onChange={e => setAnsibleSettings({...ansibleSettings, playbookPath: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="ansible-timeout">Timeout (seconds)</Label>
                <Input 
                  id="ansible-timeout" 
                  type="number" 
                  value={ansibleSettings.timeout}
                  onChange={e => setAnsibleSettings({...ansibleSettings, timeout: e.target.value})}
                />
              </div>
              
              <Separator className="my-2" />
              
              <div className="flex items-center space-x-2">
                <Switch 
                  id="use-custom-inventory" 
                  checked={ansibleSettings.useCustomInventory}
                  onCheckedChange={checked => setAnsibleSettings({...ansibleSettings, useCustomInventory: checked})}
                />
                <Label htmlFor="use-custom-inventory">Use Custom Inventory</Label>
              </div>
              
              {ansibleSettings.useCustomInventory && (
                <div className="space-y-2">
                  <Label htmlFor="inventory-path">Inventory Path</Label>
                  <Input 
                    id="inventory-path" 
                    value={ansibleSettings.inventoryPath}
                    onChange={e => setAnsibleSettings({...ansibleSettings, inventoryPath: e.target.value})}
                  />
                </div>
              )}
            </CardContent>
            <CardFooter>
              <Button onClick={handleSaveAnsibleSettings}>Save Changes</Button>
            </CardFooter>
          </Card>
        </TabsContent>
        
        {/* Target SSH Settings Tab */}
        <TabsContent value="targets">
          <Card>
            <CardHeader>
              <CardTitle>Target SSH Settings</CardTitle>
              <CardDescription>
                Configure default SSH settings for target VMs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="default-user">Default SSH User</Label>
                <Input 
                  id="default-user" 
                  value={sshSettings.defaultUser}
                  onChange={e => setSSHSettings({...sshSettings, defaultUser: e.target.value})}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="ssh-key-path">SSH Key Path</Label>
                <Input 
                  id="ssh-key-path" 
                  value={sshSettings.keyPath}
                  onChange={e => setSSHSettings({...sshSettings, keyPath: e.target.value})}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ssh-port">SSH Port</Label>
                  <Input 
                    id="ssh-port" 
                    type="number"
                    value={sshSettings.port}
                    onChange={e => setSSHSettings({...sshSettings, port: e.target.value})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="ssh-timeout">Connection Timeout (seconds)</Label>
                  <Input 
                    id="ssh-timeout" 
                    type="number"
                    value={sshSettings.timeout}
                    onChange={e => setSSHSettings({...sshSettings, timeout: e.target.value})}
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handleSaveTargetSettings}>Save Changes</Button>
            </CardFooter>
          </Card>
        </TabsContent>
        
        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you want to be notified about deployments
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch 
                  id="email-notifications" 
                  checked={notificationSettings.emailNotifications}
                  onCheckedChange={checked => setNotificationSettings({...notificationSettings, emailNotifications: checked})}
                />
                <Label htmlFor="email-notifications">Email Notifications</Label>
              </div>
              
              {notificationSettings.emailNotifications && (
                <div className="space-y-2 pl-6">
                  <Label htmlFor="email-recipients">Email Recipients</Label>
                  <Input 
                    id="email-recipients" 
                    placeholder="email@example.com"
                    value={notificationSettings.emailRecipients}
                    onChange={e => setNotificationSettings({...notificationSettings, emailRecipients: e.target.value})}
                  />
                  <p className="text-sm text-muted-foreground">Separate multiple emails with commas</p>
                </div>
              )}
              
              <div className="flex items-center space-x-2 pt-2">
                <Switch 
                  id="slack-notifications" 
                  checked={notificationSettings.slackNotifications}
                  onCheckedChange={checked => setNotificationSettings({...notificationSettings, slackNotifications: checked})}
                />
                <Label htmlFor="slack-notifications">Slack Notifications</Label>
              </div>
              
              {notificationSettings.slackNotifications && (
                <div className="space-y-2 pl-6">
                  <Label htmlFor="slack-webhook">Slack Webhook URL</Label>
                  <Input 
                    id="slack-webhook" 
                    placeholder="https://hooks.slack.com/services/..."
                    value={notificationSettings.slackWebhook}
                    onChange={e => setNotificationSettings({...notificationSettings, slackWebhook: e.target.value})}
                  />
                </div>
              )}
              
              <Separator className="my-2" />
              
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Notify On:</h3>
                <div className="flex items-center space-x-2 pl-6">
                  <Switch 
                    id="notify-success" 
                    checked={notificationSettings.notifyOnSuccess}
                    onCheckedChange={checked => setNotificationSettings({...notificationSettings, notifyOnSuccess: checked})}
                  />
                  <Label htmlFor="notify-success">Successful Deployments</Label>
                </div>
                <div className="flex items-center space-x-2 pl-6">
                  <Switch 
                    id="notify-failure" 
                    checked={notificationSettings.notifyOnFailure}
                    onCheckedChange={checked => setNotificationSettings({...notificationSettings, notifyOnFailure: checked})}
                  />
                  <Label htmlFor="notify-failure">Failed Deployments</Label>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handleSaveNotificationSettings}>Save Changes</Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SettingsPanel;
