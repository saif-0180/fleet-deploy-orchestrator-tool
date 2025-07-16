import React from 'react';
import { Button } from "@/components/ui/button";
import { useAuth } from '@/contexts/AuthContext';
import { LogOut, User } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header
      className="relative w-full h-28 bg-cover bg-center shadow-md flex items-center"
      style={{ backgroundImage: "url('/background/amdocs-header.png')" }}
    >
      {/* Title - centered absolutely */}
      <h1 className="absolute inset-0 flex items-center justify-center text-white text-2xl font-bold">
        Private-Fix-Deployment-Tool
      </h1>

      {/* User Info - aligned right */}
      {user && (
        <div className="ml-auto mr-6 flex items-center gap-4 bg-black/60 px-3 py-2 rounded text-white">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4" />
            <span className="font-medium">{user.username}</span>
            <span className="px-2 py-1 bg-white text-black text-xs rounded">
              {user.role}
            </span>
          </div>
          <Button
            onClick={logout}
            variant="ghost"
            size="sm"
            className="text-white hover:bg-white hover:text-black"
          >
            <LogOut className="h-4 w-4 mr-1" />
            Logout
          </Button>
        </div>
      )}
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
