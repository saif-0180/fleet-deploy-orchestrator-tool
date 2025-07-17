import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { UserPlus, Users, Trash2, Edit } from 'lucide-react';

const UserManagement: React.FC = () => {
  const { toast } = useToast();
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserRole, setNewUserRole] = useState('');

  // Placeholder for fetching users (replace with actual API call)
  const { data: users, isLoading, error } = useQuery('users', async () => {
    // Replace this with your actual API endpoint
    const response = await fetch('/api/users');
    if (!response.ok) {
      throw new Error('Failed to fetch users');
    }
    return response.json();
  });

  const handleAddUser = async () => {
    try {
      // Replace this with your actual API endpoint for adding users
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: newUserEmail, role: newUserRole }),
      });

      if (response.ok) {
        toast({
          title: "User Added",
          description: `User ${newUserEmail} added successfully with role ${newUserRole}.`,
        });
        // Clear the form
        setNewUserEmail('');
        setNewUserRole('');
        // Invalidate the query to refetch users
        // queryClient.invalidateQueries('users');
      } else {
        const errorData = await response.json();
        toast({
          title: "Error",
          description: errorData.message || 'Failed to add user',
          variant: "destructive",
        });
      }
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || 'Failed to add user',
        variant: "destructive",
      });
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      // Replace this with your actual API endpoint for deleting users
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast({
          title: "User Deleted",
          description: `User deleted successfully.`,
        });
        // Invalidate the query to refetch users
        // queryClient.invalidateQueries('users');
      } else {
        const errorData = await response.json();
        toast({
          title: "Error",
          description: errorData.message || 'Failed to delete user',
          variant: "destructive",
        });
      }
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || 'Failed to delete user',
        variant: "destructive",
      });
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return (
          <Badge className="bg-primary text-primary-foreground">
            Admin
          </Badge>
        );
      case 'user':
        return (
          <Badge className="bg-secondary text-secondary-foreground">
            User
          </Badge>
        );
      default:
        return (
          <Badge className="bg-muted text-muted-foreground">
            {role}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold gradient-heading mb-6">User Management</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-t-lg">
              <CardTitle className="text-primary text-lg font-semibold flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Add New User
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-6">
              <div className="space-y-2">
                <Label htmlFor="userEmail" className="text-foreground font-medium">Email</Label>
                <Input
                  id="userEmail"
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="Enter user email"
                  className="bg-input border-border text-foreground"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="userRole" className="text-foreground font-medium">Role</Label>
                <Select value={newUserRole} onValueChange={setNewUserRole}>
                  <SelectTrigger className="bg-input border-border text-foreground">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border">
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <Button
                onClick={handleAddUser}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-medium py-2"
              >
                <UserPlus className="mr-2 h-4 w-4" />
                Add User
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-card border-border shadow-lg">
            <CardHeader className="bg-gradient-to-r from-accent/10 to-primary/10 rounded-t-lg">
              <CardTitle className="text-primary text-lg font-semibold flex items-center gap-2">
                <Users className="h-5 w-5" />
                Existing Users
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-medium text-foreground">Email</th>
                      <th className="text-left py-3 px-4 font-medium text-foreground">Role</th>
                      <th className="text-left py-3 px-4 font-medium text-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Sample row - actual data would be mapped here */}
                    <tr className="border-b border-border hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 text-foreground">user@example.com</td>
                      <td className="py-3 px-4">{getRoleBadge('user')}</td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-border text-foreground hover:bg-accent hover:text-accent-foreground"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default UserManagement;
