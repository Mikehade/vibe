import { useState } from 'react';
import { clsx } from 'clsx';
import { img, type ImgSize } from '@/lib/images';

/** Poster with a typographic fallback — never shows a broken image or "No poster". */
export default function Poster({
  path,
  title,
  size = 'w342',
  className,
  rounded = 'rounded-[0.9rem]',
}: {
  path: string | null | undefined;
  title: string;
  size?: ImgSize;
  className?: string;
  rounded?: string;
}) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = img(path, size);
  return (
    <div className={clsx('relative overflow-hidden bg-ink-800', rounded, className)}>
      {src && !failed ? (
        <img
          src={src}
          alt={title}
          loading="lazy"
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={clsx('h-full w-full object-cover transition-opacity duration-500', loaded ? 'opacity-100' : 'opacity-0')}
        />
      ) : (
        <div className="flex h-full w-full flex-col justify-end bg-gradient-to-br from-ink-700 to-ink-850 p-[8%]">
          <span className="font-serif text-[1.6rem] leading-[1.05] text-paper/90">{title}</span>
        </div>
      )}
      {src && !failed && !loaded && <div className="skeleton absolute inset-0" />}
    </div>
  );
}
