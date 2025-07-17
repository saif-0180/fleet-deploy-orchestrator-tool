
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from "@/hooks/use-toast";
import { Eye, EyeOff } from 'lucide-react';

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await login(username, password);
      toast({
        title: "Success",
        description: "Logged in successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Login failed",
        variant: "destructive",
      });
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background: 'linear-gradient(135deg, #00171f 0%, #003459 50%, #00a7e1 100%)'
      }}
    >
      <Card className="w-full max-w-md bg-[#F2F0EF] border border-[#00171f]/20 shadow-2xl">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 w-20 h-20 rounded-full bg-gradient-to-br from-[#00a7e1] to-[#00171f] flex items-center justify-center shadow-lg">
            <div className="w-12 h-12 rounded-full bg-[#F2F0EF] flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#00a7e1] to-[#00171f]"></div>
            </div>
          </div>
          <CardTitle 
            className="text-2xl font-bold bg-gradient-to-r from-[#00171f] to-[#00a7e1] bg-clip-text text-transparent"
          >
            Login
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username" className="text-[#00171f] font-medium">Username</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="bg-white border-[#00171f]/30 text-[#00171f] focus:border-[#00a7e1] focus:ring-[#00a7e1]/20"
                placeholder="Enter your username"
                required
              />
            </div>
            
            <div>
              <Label htmlFor="password" className="text-[#00171f] font-medium">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-white border-[#00171f]/30 text-[#00171f] focus:border-[#00a7e1] focus:ring-[#00a7e1]/20 pr-10"
                  placeholder="Enter your password"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-[#00171f]" />
                  ) : (
                    <Eye className="h-4 w-4 text-[#00171f]" />
                  )}
                </Button>
              </div>
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-[#00a7e1] text-white hover:bg-[#00a7e1]/90 shadow-lg font-medium"
            >
              Sign In
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
