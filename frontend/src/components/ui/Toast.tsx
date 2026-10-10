import { create } from 'zustand';

interface ToastState {
  message: string | null;
  show: (m: string) => void;
}

let timer: ReturnType<typeof setTimeout> | undefined;

export const useToast = create<ToastState>((set) => ({
  message: null,
  show: (message) => {
    set({ message });
    clearTimeout(timer);
    timer = setTimeout(() => set({ message: null }), 3200);
  },
}));

export function Toaster() {
  const message = useToast((s) => s.message);
  if (!message) return null;
  return (
    <div className="pointer-events-none fixed bottom-[3rem] left-1/2 z-[60] -translate-x-1/2 animate-fade-up rounded-full bg-paper px-[1.8rem] py-[0.9rem] text-[1.1rem] font-semibold text-ink-950 shadow-2xl">
      {message}
    </div>
  );
}
