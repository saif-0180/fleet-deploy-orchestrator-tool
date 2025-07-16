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
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      {/* Dark overlay for better text readability */}
      <div className="absolute inset-0 bg-black bg-opacity-20"></div>
      
      {/* Content */}
      <div className="relative z-10 flex justify-between items-center">
        {/* Left side - empty for spacing */}
        <div className="flex-1"></div>
        
        {/* Center - Title */}
        <div className="flex-1 flex justify-center">
          <h1 className="text-2xl font-bold text-white drop-shadow-lg">
            Private-Fix-Deployment-Tool
          </h1>
        </div>
        
        {/* Right side - User info */}
        <div className="flex-1 flex justify-end">
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-white" />
                <span className="font-medium text-white">{user.username}</span>
                <span className="px-2 py-1 bg-white bg-opacity-20 text-white text-xs rounded backdrop-blur-sm">
                  {user.role}
                </span>
              </div>
              <Button
                onClick={logout}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white hover:bg-opacity-20 hover:text-white backdrop-blur-sm"
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

// import React from 'react';
// import { Button } from "@/components/ui/button";
// import { useAuth } from '@/contexts/AuthContext';
// import { LogOut, User } from 'lucide-react';

// const Header: React.FC = () => {
//   const { user, logout } = useAuth();

//   return (
//     <header className="bg-[#F79B72] text-[#2A4759] px-6 py-4 shadow-md">
//       <div className="flex justify-between items-center">
//         <h1 className="text-2xl font-bold">Private-Fix-Deployment-Tool</h1>
        
//         {user && (
//           <div className="flex items-center gap-4">
//             <div className="flex items-center gap-2">
//               <User className="h-4 w-4" />
//               <span className="font-medium">{user.username}</span>
//               <span className="px-2 py-1 bg-[#2A4759] text-[#F79B72] text-xs rounded">
//                 {user.role}
//               </span>
//             </div>
//             <Button
//               onClick={logout}
//               variant="ghost"
//               size="sm"
//               className="text-[#2A4759] hover:bg-[#2A4759] hover:text-[#F79B72]"
//             >
//               <LogOut className="h-4 w-4 mr-2" />
//               Logout
//             </Button>
//           </div>
//         )}
//       </div>
//     </header>
//   );
// };

// export default Header;
