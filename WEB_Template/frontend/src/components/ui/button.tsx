import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { Button as BaseButton } from '@/components/shadcn/button';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
}

/** Velikosti starého API na shadcn škálu (NAVRH_UI §3: jedno tlačítko v celé aplikaci). */
const SIZE = { default: 'lg', sm: 'default', lg: 'lg', icon: 'icon-lg' } as const;

/**
 * Tlačítko stávajících formulářů: vzhled je shadcn `Button` (jeden zdroj), navíc `isLoading`.
 * Nový kód může používat `@/components/shadcn/button` přímo.
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', isLoading = false, children, disabled, ...props }, ref) => (
    <BaseButton
      ref={ref}
      variant={variant}
      size={SIZE[size]}
      disabled={disabled || isLoading}
      className={cn(size === 'lg' && 'h-10 px-4', className)}
      {...props}
    >
      {isLoading && <Loader2 className="animate-spin motion-reduce:animate-none" aria-hidden />}
      {children}
    </BaseButton>
  ),
);
Button.displayName = 'Button';

export { Button };
