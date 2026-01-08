import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        // HomeIQ status badges
        healthy:
          "border-transparent bg-status-healthy-light text-status-healthy dark:bg-status-healthy/20 dark:text-status-healthy",
        warning:
          "border-transparent bg-status-warning-light text-status-warning dark:bg-status-warning/20 dark:text-status-warning",
        critical:
          "border-transparent bg-status-critical-light text-status-critical dark:bg-status-critical/20 dark:text-status-critical",
        offline:
          "border-transparent bg-status-offline-light text-status-offline dark:bg-status-offline/20 dark:text-status-offline",
        // Service category badges
        weather:
          "border-transparent bg-[hsl(199,89%,94%)] text-accent-weather dark:bg-[hsl(199,89%,48%,0.2)] dark:text-accent-weather",
        sports:
          "border-transparent bg-[hsl(262,83%,94%)] text-accent-sports dark:bg-[hsl(262,83%,58%,0.2)] dark:text-accent-sports",
        automation:
          "border-transparent bg-[hsl(25,95%,94%)] text-accent-automation dark:bg-[hsl(25,95%,53%,0.2)] dark:text-accent-automation",
        energy:
          "border-transparent bg-[hsl(142,71%,94%)] text-accent-energy dark:bg-[hsl(142,71%,45%,0.2)] dark:text-accent-energy",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-px text-[10px]",
        lg: "px-3 py-1 text-sm",
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
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
      )}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };
