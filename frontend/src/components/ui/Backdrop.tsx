import { useEffect, useState } from 'react';
import { img } from '@/lib/images';

/** Full-bleed cross-fading backdrop. Uses gradients (not blur) — cheap on Fire TV GPUs. */
export default function Backdrop({ path, fallbackColor = '#101014' }: { path: string | null | undefined; fallbackColor?: string }) {
  const [layers, setLayers] = useState<{ src: string | null; key: number }[]>([{ src: img(path, 'w1280'), key: 0 }]);
  useEffect(() => {
    const src = img(path, 'w1280');
    setLayers((prev) => (prev[prev.length - 1]?.src === src ? prev : [...prev.slice(-1), { src, key: Date.now() }]));
  }, [path]);
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" style={{ background: fallbackColor }}>
      {layers.map((l, i) =>
        l.src ? (
          <img
            key={l.key}
            src={l.src}
            alt=""
            className="kenburns absolute inset-0 h-full w-full object-cover animate-fade-in"
            style={{ opacity: i === layers.length - 1 ? 0.55 : 0.0, transition: 'opacity 700ms ease' }}
          />
        ) : null,
      )}
      <div className="scrim-left absolute inset-0" />
      <div className="scrim-bottom absolute inset-0" />
      <div className="scrim-top absolute inset-x-0 top-0 h-[12rem]" />
    </div>
  );
}
