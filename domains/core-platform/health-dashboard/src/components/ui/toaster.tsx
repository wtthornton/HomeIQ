import * as React from "react";
import { Toast, ToastProps } from "./toast";
import { cn } from "@/lib/utils";

interface ToasterContextValue {
  toasts: ToastData[];
  addToast: (toast: Omit<ToastData, "id">) => void;
  removeToast: (id: string) => void;
}

interface ToastData extends ToastProps {
  id: string;
  duration?: number;
}

const ToasterContext = React.createContext<ToasterContextValue | undefined>(undefined);

export function useToast() {
  const context = React.useContext(ToasterContext);
  if (!context) {
    throw new Error("useToast must be used within a ToasterProvider");
  }
  return context;
}

// Simple toast function for convenience
export function toast(props: Omit<ToastData, "id">) {
  // This will be implemented when we have a global toaster
  console.warn("Toast triggered:", props);
}

interface ToasterProviderProps {
  children: React.ReactNode;
}

export function ToasterProvider({ children }: ToasterProviderProps) {
  const [toasts, setToasts] = React.useState<ToastData[]>([]);

  const addToast = React.useCallback((toast: Omit<ToastData, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { ...toast, id };
    setToasts((prev) => [...prev, newToast]);

    // Auto dismiss
    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToasterContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <Toaster />
    </ToasterContext.Provider>
  );
}

function Toaster() {
  const context = React.useContext(ToasterContext);
  
  if (!context) return null;
  
  const { toasts, removeToast } = context;

  return (
    <div
      className={cn(
        "fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]"
      )}
    >
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          {...toast}
          onOpenChange={(open) => {
            if (!open) removeToast(toast.id);
          }}
          className="mb-2"
        />
      ))}
    </div>
  );
}

export { Toaster };
