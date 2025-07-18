
import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { Eye, EyeOff, User, Lock } from 'lucide-react';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4"
      style={{ 
        backgroundImage: 'url(/background/amdocs-loginpage-bg.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      <div className="min-h-screen w-full flex items-center justify-center bg-black/40">
        <Card className="w-full max-w-md bg-[#00171f]/95 backdrop-blur-sm border-[#00a7e1]/20">
          <CardHeader className="space-y-1 text-center">
            <div className="mx-auto mb-4">
              <img 
                src="/background/amdocs-header.png" 
                alt="Amdocs" 
                className="h-12 mx-auto"
              />
            </div>
            <CardTitle className="text-2xl font-bold text-[#EEEEEE]">
              Welcome Back
            </CardTitle>
            <p className="text-[#BBBDBC]">
              Sign in to your deployment management account
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-[#BBBDBC]" />
                  <Input
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="pl-10 bg-[#003459] border-[#00a7e1]/30 text-[#EEEEEE] placeholder:text-[#BBBDBC] focus:border-[#00a7e1]"
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-[#BBBDBC]" />
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10 bg-[#003459] border-[#00a7e1]/30 text-[#EEEEEE] placeholder:text-[#BBBDBC] focus:border-[#00a7e1]"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-[#BBBDBC] hover:text-[#EEEEEE]"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              
              {error && (
                <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded p-3">
                  {error}
                </div>
              )}
              
              <Button 
                type="submit" 
                className="w-full bg-[#00a7e1] hover:bg-[#00a7e1]/80 text-[#EEEEEE]"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
