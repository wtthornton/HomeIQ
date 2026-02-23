import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground",
        outline: "text-foreground border-border",
        // HomeIQ status badges - Subtle, functional
        healthy:
          "border-transparent bg-status-healthy/15 text-status-healthy",
        warning:
          "border-transparent bg-status-warning/15 text-status-warning",
        critical:
          "border-transparent bg-status-critical/15 text-status-critical",
        offline:
          "border-transparent bg-status-offline/15 text-status-offline",
        // Service category badges
        weather:
          "border-transparent bg-accent-weather/15 text-accent-weather",
        sports:
          "border-transparent bg-primary/15 text-primary",
        automation:
          "border-transparent bg-accent/15 text-accent",
        energy:
          "border-transparent bg-accent-energy/15 text-accent-energy",
      },
      size: {
        default: "px-1.5 py-0.5 text-xs",
        sm: "px-1 py-px text-[10px]",
        lg: "px-2 py-0.5 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

function Badge({ className, variant, size, dot, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span className="mr-1 h-1.5 w-1.5 rounded-full bg-current" />
      )}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };
