import { useNavigate } from 'react-router-dom';
import Wordmark from './Wordmark';
import Icon from './Icon';
import { focusProps } from '@/lib/focus/FocusProvider';
import { useProfile } from '@/stores/profile';

export function NavButton({ icon, label, onClick }: { icon: string; label: string; onClick: () => void }) {
  return (
    <button {...focusProps} onClick={onClick} className="btn btn-ghost group !px-[1.2rem] !py-[0.75rem] text-[1rem]">
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );
}

export default function TopBar({ right }: { right?: React.ReactNode }) {
  const nav = useNavigate();
  const profile = useProfile((s) => s.profile);
  return (
    <header className="relative z-10 flex items-center justify-between">
      <button {...focusProps} onClick={() => nav('/')} aria-label="Home" className="focusable focus-ring -mx-[0.8rem] rounded-full px-[0.8rem] py-[0.2rem]">
        <Wordmark className="text-[2.6rem] text-paper" />
      </button>
      <div className="flex items-center gap-[0.8rem]">
        {right}
        <NavButton icon="users" label="Couch Mode" onClick={() => nav('/couch')} />
        <NavButton icon="history" label="History" onClick={() => nav('/history')} />
        <button {...focusProps} onClick={() => nav('/settings')} className="btn btn-ghost !px-[1.2rem] !py-[0.75rem] text-[1rem]">
          <span className="flex h-[1.7rem] w-[1.7rem] items-center justify-center rounded-full bg-amber/20 text-[0.85rem] font-bold text-amber-soft">
            {(profile?.name || 'M').slice(0, 1).toUpperCase()}
          </span>
          <span>{profile?.name || 'Me'}</span>
          {profile?.is_kids && <span className="rounded-full bg-role-opener/20 px-[0.6rem] py-[0.1rem] text-[0.75rem] text-role-opener">Kids</span>}
        </button>
      </div>
    </header>
  );
}
