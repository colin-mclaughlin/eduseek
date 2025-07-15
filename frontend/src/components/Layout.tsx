import { ReactNode, useState } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import Sidebar from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar for desktop */}
      <div className="hidden md:flex md:w-64">
        <Sidebar />
      </div>
      {/* Sidebar for mobile */}
      <div className="md:hidden">
        <Button
          variant="ghost"
          size="icon"
          className="m-2"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu className="w-6 h-6" />
        </Button>
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 flex">
            <div className="relative w-64">
              <Sidebar onClose={() => setSidebarOpen(false)} />
            </div>
            <div
              className="fixed inset-0 bg-black/40"
              onClick={() => setSidebarOpen(false)}
            />
          </div>
        )}
      </div>
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white dark:bg-gray-900 border-b border-border flex items-center px-4 shadow-sm">
          <h1 className="text-xl font-semibold tracking-tight">EduSeek</h1>
        </header>
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          {children}
        </main>
      </div>
    </div>
  );
} 