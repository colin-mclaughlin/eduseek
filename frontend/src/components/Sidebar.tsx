import { Button } from "@/components/ui/button";
import { Link, useLocation } from "react-router-dom";
import {
  Home,
  FileText,
  Bot,
  Settings,
  X
} from "lucide-react";
import { ReactNode } from "react";

const navItems: { label: string; to: string; icon: ReactNode }[] = [
  { label: "Dashboard", to: "/dashboard", icon: <Home className="w-5 h-5" /> },
  { label: "Files", to: "/files", icon: <FileText className="w-5 h-5" /> },
  { label: "Assistant", to: "/assistant", icon: <Bot className="w-5 h-5" /> },
  { label: "Settings", to: "/settings", icon: <Settings className="w-5 h-5" /> },
];

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const location = useLocation();
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
      </nav>
    </aside>
  );
} 