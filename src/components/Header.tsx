
import React from 'react';
import { Button } from "@/components/ui/button";
import { useAuth } from '@/contexts/AuthContext';
import { LogOut, User } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header 
      className="relative px-6 py-4 shadow-md overflow-hidden"
      style={{
        backgroundImage: `url('/background/amdocs-header.png')`,
        backgroundSize: 'contain',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        minHeight: '100px'
      }}
    >
      
      {/* Content */}
      <div className="relative z-10 flex justify-between items-center h-full">
        {/* Left side - empty for spacing */}
        <div className="flex-1"></div>
        
        {/* Center - Title */}
        <div className="flex-1 flex justify-center">
          <h2 className="text-2xl font-bold text-white">
            Private-Fix-Deployment-Tool
          </h2>
        </div>
        
        {/* Right side - User info */}
        <div className="flex-1 flex justify-end">
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-white" />
                <span className="font-medium text-white">{user.username}</span>
                <span className="px-2 py-1 bg-[#007ea7] text-white text-xs rounded">
                  {user.role}
                </span>
              </div>
              <Button
                onClick={logout}
                variant="ghost"
                size="sm"
                className="text-white bg-[#007ea7] hover:bg-[#005f7a] hover:text-white"
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
