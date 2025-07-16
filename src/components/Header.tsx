
import React from 'react';
import { Button } from "@/components/ui/button";
import { useAuth } from '@/contexts/AuthContext';
import { LogOut, User } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header 
      className="relative px-6 py-4 shadow-lg overflow-hidden border-b border-border/50"
      style={{
        backgroundImage: `url('/lovable-uploads/aeb5042c-8233-4d69-b051-e4ac9c80427d.png')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        minHeight: '100px'
      }}
    >
      {/* Gradient overlay for better text readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-background/60 via-background/40 to-background/60"></div>
      
      {/* Content */}
      <div className="relative z-10 flex justify-between items-center h-full">
        {/* Left side - empty for spacing */}
        <div className="flex-1"></div>
        
        {/* Center - Title */}
        <div className="flex-1 flex justify-center">
          <h2 className="text-2xl font-bold gradient-text">
            Private-Fix-Deployment-Tool
          </h2>
        </div>
        
        {/* Right side - User info */}
        <div className="flex-1 flex justify-end">
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm px-3 py-2 rounded-lg border border-border/50">
                <User className="h-4 w-4 text-primary" />
                <span className="font-medium text-foreground">{user.username}</span>
                <span className="px-2 py-1 bg-primary text-primary-foreground text-xs rounded-md font-medium">
                  {user.role}
                </span>
              </div>
              <Button
                onClick={logout}
                variant="outline"
                size="sm"
                className="bg-card/80 backdrop-blur-sm border-border/50 text-foreground hover:bg-accent hover:text-accent-foreground transition-all duration-200"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
