import { img } from '@/lib/images';
import type { CandidateSample } from '@/lib/types';

/** Faded, slowly drifting wall of the shortlist behind the "building" state. */
export default function CandidateWall({ sample }: { sample: CandidateSample[] }) {
  if (!sample.length) return null;
  const items = [...sample, ...sample];
  return (
    <div
      className="pointer-events-none absolute right-0 top-0 h-[60%] w-[56%] overflow-hidden opacity-35 animate-fade-in"
      style={{
        maskImage: 'linear-gradient(90deg, transparent 0%, black 45%), linear-gradient(180deg, black 55%, transparent 100%)',
        WebkitMaskImage: 'linear-gradient(90deg, transparent 0%, black 45%), linear-gradient(180deg, black 55%, transparent 100%)',
        maskComposite: 'intersect',
        WebkitMaskComposite: 'source-in',
      }}
    >
      <div className="grid grid-cols-5 gap-[1rem] p-[1rem]" style={{ animation: 'drift 60s linear infinite' }}>
        {items.map((c, i) => {
          const src = img(c.poster_path, 'w185');
          return src ? (
            <img key={`${c.tmdb_id}-${i}`} src={src} alt="" className="aspect-[2/3] w-full rounded-[0.6rem] object-cover" style={{ transform: `translateY(${(i % 5) * 2}rem)` }} />
          ) : null;
        })}
      </div>
    </div>
  );
}
