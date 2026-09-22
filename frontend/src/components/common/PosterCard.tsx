/* ── Movie / TV poster card with focus state ── */

import { clsx } from 'clsx';

const TMDB_IMG = 'https://image.tmdb.org/t/p';

interface Props {
  title: string;
  posterPath: string | null;
  role?: string;
  runtime?: number;
  reason?: string;
  confidence?: number;
  streamingProvider?: string | null;
  focused?: boolean;
  status?: string;
  onClick?: () => void;
}

export default function PosterCard({
  title,
  posterPath,
  role,
  runtime,
  reason,
  confidence,
  streamingProvider,
  focused,
  status,
  onClick,
}: Props) {
  const imgSrc = posterPath ? `${TMDB_IMG}/w342${posterPath}` : null;

  return (
    <div
      onClick={onClick}
      className={clsx(
        'relative flex flex-col rounded-tv overflow-hidden bg-vibe-card',
        'transition-all duration-300 cursor-pointer',
        'w-48 shrink-0',
        focused && 'ring-4 ring-vibe-accent scale-110 z-10',
        !focused && 'hover:ring-2 hover:ring-vibe-border',
      )}
    >
      {/* Poster image */}
      <div className="aspect-[2/3] bg-vibe-surface">
        {imgSrc ? (
          <img src={imgSrc} alt={title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-vibe-text-muted text-sm">
            No poster
          </div>
        )}
      </div>

      {/* Role badge */}
      {role && (
        <span
          className={clsx(
            'absolute top-2 left-2 px-2 py-0.5 rounded-full text-xs font-bold uppercase',
            role === 'opener' && 'bg-green-600/80 text-white',
            role === 'main_event' && 'bg-vibe-accent/80 text-white',
            role === 'bridge' && 'bg-yellow-600/80 text-white',
            role === 'nightcap' && 'bg-red-500/80 text-white',
          )}
        >
          {role}
        </span>
      )}

      {/* Status badge */}
      {status && status !== 'pending' && (
        <span
          className={clsx(
            'absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-bold',
            status === 'watching' && 'bg-blue-500/80 text-white',
            status === 'completed' && 'bg-vibe-success/80 text-white',
            status === 'skipped' && 'bg-vibe-text-muted/50 text-white',
          )}
        >
          {status === 'completed' ? 'watched' : status}
        </span>
      )}

      {/* Info */}
      <div className="p-3 space-y-1">
        <h3 className="text-sm font-semibold truncate">{title}</h3>
        {runtime && <p className="text-xs text-vibe-text-muted">{runtime} min</p>}
        {streamingProvider && (
          <p className="text-xs text-vibe-accent-light">{streamingProvider}</p>
        )}
      </div>

      {/* Expanded detail on focus */}
      {focused && reason && (
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-4">
          <p className="text-xs text-vibe-text leading-relaxed">{reason}</p>
          {confidence !== undefined && (
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-1 bg-vibe-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-vibe-accent rounded-full"
                  style={{ width: `${Math.round(confidence * 100)}%` }}
                />
              </div>
              <span className="text-xs text-vibe-text-muted">
                {Math.round(confidence * 100)}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
