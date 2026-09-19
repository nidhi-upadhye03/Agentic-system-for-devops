import React from 'react';
import { cn } from '../../lib/utils';
import { cva } from 'class-variance-authority';

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-white/10 text-white backdrop-blur-sm",
        secondary: "border-transparent bg-white/5 text-white/80 backdrop-blur-sm",
        destructive: "border-transparent bg-red-500/20 text-red-400 backdrop-blur-sm",
        success: "border-transparent bg-green-500/20 text-green-400 backdrop-blur-sm",
        warning: "border-transparent bg-yellow-500/20 text-yellow-400 backdrop-blur-sm",
        outline: "text-white border-white/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

const Badge = React.forwardRef(({ className, variant, ...props }, ref) => {
  return (
    <div ref={ref} className={cn(badgeVariants({ variant }), className)} {...props} />
  );
});
Badge.displayName = "Badge";

export { Badge, badgeVariants };
