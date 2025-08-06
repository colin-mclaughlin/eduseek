import { Button } from "./ui/button";
import { Link, useLocation } from "react-router-dom";
import {
  Home,
  FileText,
  Bot,
  Settings,
  X,
  Download
} from "lucide-react";
import { type ReactNode, useState } from "react";
import OnQSyncModal from "./OnQSyncModal";
import { useToast } from "./ui/toast";

const navItems: { label: string; to: string; icon: ReactNode }[] = [
  { label: "Dashboard", to: "/dashboard", icon: <Home className="w-5 h-5" /> },
  { label: "Files", to: "/files", icon: <FileText className="w-5 h-5" /> },
  { label: "Assistant", to: "/assistant", icon: <Bot className="w-5 h-5" /> },
  { label: "Settings", to: "/settings", icon: <Settings className="w-5 h-5" /> },
];

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const location = useLocation();
  const [showOnQModal, setShowOnQModal] = useState(false);
  const { showToast } = useToast();

  const handleSyncSuccess = (results: any) => {
    console.log("OnQ sync completed from sidebar:", results);
    showToast("Files and deadlines synced successfully from OnQ!", "success");
  };

  return (
    <aside className="h-full w-64 bg-gray-900 text-white flex flex-col border-r border-border">
      <div className="flex items-center justify-between h-16 px-4 border-b border-border">
        <span className="font-bold text-lg tracking-tight">EduSeek</span>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        )}
      </div>
      <nav className="flex-1 flex flex-col gap-1 p-4">
        {navItems.map((item) => (
          <Button
            key={item.to}
            asChild
            variant={location.pathname === item.to ? "secondary" : "ghost"}
            className="justify-start w-full gap-3"
          >
            <Link to={item.to} onClick={onClose}>
              {item.icon}
              {item.label}
            </Link>
          </Button>
        ))}
        
        {/* OnQ Sync Button */}
        <div className="mt-auto mb-4">
          <Button
            onClick={() => setShowOnQModal(true)}
            variant="outline"
            className="w-full gap-3 border-gray-600 text-gray-300 hover:bg-gray-800 hover:text-white"
          >
            <Download className="w-5 h-5" />
            Sync OnQ
          </Button>
        </div>
      </nav>

      {/* OnQ Sync Modal */}
      <OnQSyncModal
        isOpen={showOnQModal}
        onClose={() => setShowOnQModal(false)}
        onSuccess={handleSyncSuccess}
      />
    </aside>
  );
} 