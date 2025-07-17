import * as React fromreact";
import { cn } from "../../lib/utils";
import { X, CheckCircle, AlertCircle } fromlucide-react";

interface ToastProps {
  message: string;
  type: success" | error";
  onClose: () => void;
  duration?: number;
}

export const Toast: React.FC<ToastProps> = ({ 
  message, 
  type, 
  onClose, 
  duration = 4000) => {
  React.useEffect(() =>[object Object]
    const timer = setTimeout(() => {
      onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const icon = type === success" ? <CheckCircle className="h-4 /> : <AlertCircle className="h-4-4>;
  const bgColor = type === "success" ? "bg-green-50 border-green-200bg-red-50 border-red-200
  const textColor = type ===success" ? text-green-800:text-red-800
  const iconColor = type ===success" ? text-green-600 text-red-600;

  return (
    <div className={cn(
      fixed top-4 right-4 flex items-center gap-3 p-4 rounded-lg border shadow-lg max-w-sm",
      bgColor
    )}>
      <div className={cn("flex-shrink0onColor)}>
        {icon}
      </div>
      <div className={cn("flex-1 text-sm font-medium", textColor)}>
        {message}
      </div>
      <button
        onClick={onClose}
        className={cn(flex-shrink-0 p-1ded hover:bg-black/5", textColor)}
      >
        <X className=h-4 />
      </button>
    </div>
  );
};

// Toast context for managing multiple toasts
interface ToastContextType {
  showToast: (message: string, type: success" | error") => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => [object Object]const toasts, setToasts] = React.useState<Array<{ id: number; message: string; type: success | error}>>();
  const nextId, setNextId] = React.useState(1);

  const showToast = React.useCallback((message: string, type: success |error") => {
    const id = nextId;
    setNextId(prev => prev + 1    setToasts(prev => [...prev, { id, message, type }]);
  }, [nextId]);

  const removeToast = React.useCallback((id: number) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  },);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className=fixed top-4 right-4 z-50 space-y-2>       {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () =>[object Object]
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}; 