/* ── Focusable button for D-pad / 10-foot UI ── */

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  focused?: boolean;
}

const FocusableButton = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', size = 'md', focused, className, children, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          'rounded-tv font-semibold transition-all duration-200 outline-none',
          'focus-visible:ring-4 focus-visible:ring-vibe-accent/60',
          {
            // variants
            'bg-vibe-accent text-white hover:bg-vibe-accent-light': variant === 'primary',
            'bg-vibe-card text-vibe-text border border-vibe-border hover:border-vibe-accent':
              variant === 'secondary',
            'bg-transparent text-vibe-text-muted hover:text-vibe-text': variant === 'ghost',
            // sizes — TV-friendly large targets
            'px-4 py-2 text-sm': size === 'sm',
            'px-6 py-3 text-tv-base': size === 'md',
            'px-8 py-4 text-tv-lg': size === 'lg',
            // D-pad focus ring
            'ring-4 ring-vibe-accent scale-105': focused,
          },
          className,
        )}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

FocusableButton.displayName = 'FocusableButton';
export default FocusableButton;
