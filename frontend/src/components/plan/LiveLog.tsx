import { clsx } from 'clsx';
import type { LogLine } from '@/lib/types';
import Icon from '@/components/ui/Icon';

/** The agent's working notes, streamed — the viewer always knows what is happening. */
export default function LiveLog({ lines, active }: { lines: LogLine[]; active: boolean }) {
  const shown = lines.slice(-6);
  return (
    <ol className="space-y-[0.7rem]">
      {shown.map((l, i) => {
        const current = active && i === shown.length - 1;
        return (
          <li key={l.id} className={clsx('flex items-center gap-[0.9rem] text-[1.3rem] animate-fade-up', current ? 'text-paper' : 'text-paper-muted')}>
            <span className="flex h-[1.6rem] w-[1.6rem] shrink-0 items-center justify-center">
              {current ? (
                <span className="h-[0.7rem] w-[0.7rem] rounded-full bg-amber animate-pulse-dot" />
              ) : l.kind === 'error' ? (
                <Icon name="x" className="text-[#e89a8f]" />
              ) : (
                <Icon name={l.kind === 'tool' ? 'sparkle' : 'check'} className={l.kind === 'pick' ? 'text-amber' : 'text-role-opener'} />
              )}
            </span>
            <span className={clsx(l.kind === 'pick' && 'font-semibold text-paper')}>{l.message}</span>
          </li>
        );
      })}
    </ol>
  );
}
