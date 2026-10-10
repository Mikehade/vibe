import type { ReactNode } from 'react';
import { FocusScope, useBack } from '@/lib/focus/FocusProvider';

export default function Modal({ children, onClose, width = '52rem' }: { children: ReactNode; onClose: () => void; width?: string }) {
  useBack(() => {
    onClose();
    return true;
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 animate-fade-in">
      <FocusScope className="card animate-fade-up p-[2.6rem] shadow-2xl" style={{ width }}>
        {children}
      </FocusScope>
    </div>
  );
}
