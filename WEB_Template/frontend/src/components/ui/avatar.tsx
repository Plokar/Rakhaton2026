import * as React from 'react';
import { cn } from '@/lib/utils';

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  alt?: string;
  fallback?: string;
  size?: 'sm' | 'default' | 'lg';
}

export function Avatar({ src, alt, fallback = 'U', size = 'default', className, ...props }: AvatarProps) {
  const [imageError, setImageError] = React.useState(false);

  const sizeClasses = {
    sm: 'h-7 w-7 text-xs',
    default: 'h-9 w-9 text-sm',
    lg: 'h-12 w-12 text-base font-semibold',
  };

  return (
    <div
      className={cn(
        'relative flex shrink-0 overflow-hidden rounded-full border border-border/80 bg-muted/60 text-muted-foreground items-center justify-center font-medium select-none',
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {src && !imageError ? (
        <img
          src={src}
          alt={alt || 'Avatar'}
          onError={() => setImageError(true)}
          className="aspect-square h-full w-full object-cover"
        />
      ) : (
        <span className="uppercase text-foreground/80 font-bold">{fallback.slice(0, 2)}</span>
      )}
    </div>
  );
}
