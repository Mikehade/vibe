export default function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-baseline gap-[0.15em] font-serif leading-none ${className}`}>
      <span>vibe</span>
      <span className="inline-block h-[0.2em] w-[0.2em] translate-y-[-0.05em] rounded-full bg-amber" />
    </span>
  );
}
