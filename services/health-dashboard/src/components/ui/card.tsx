import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded border bg-card text-card-foreground shadow-sm transition-colors duration-150",
  {
    variants: {
      variant: {
        default: "border-border",
        elevated: "border-border shadow-md",
        outline: "border-border bg-transparent shadow-none",
        ghost: "border-transparent bg-transparent shadow-none",
        // HomeIQ status variants - left border accent
        healthy: "border-l-2 border-l-status-healthy border-t-border border-r-border border-b-border",
        warning: "border-l-2 border-l-status-warning border-t-border border-r-border border-b-border",
        critical: "border-l-2 border-l-status-critical border-t-border border-r-border border-b-border",
        offline: "border-l-2 border-l-status-offline border-t-border border-r-border border-b-border",
      },
      hover: {
        true: "hover:border-border-hover hover:shadow-md cursor-pointer",
        false: "",
      },
      glow: {
        none: "",
        primary: "",
        success: "",
        warning: "",
        error: "",
      },
    },
    defaultVariants: {
      variant: "default",
      hover: false,
      glow: "none",
    },
  }
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, hover, glow, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, hover, glow, className }))}
      {...props}
    />
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1 p-3 pb-0", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-display font-semibold text-sm leading-none tracking-tight", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-xs text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-3", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center gap-2 p-3 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, cardVariants };
