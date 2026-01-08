import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "shimmer" | "pulse";
}

function Skeleton({ className, variant = "default", ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-md bg-muted",
        variant === "shimmer" && "animate-shimmer bg-gradient-to-r from-muted via-muted/50 to-muted bg-[length:200%_100%]",
        variant === "pulse" && "animate-pulse",
        variant === "default" && "animate-pulse",
        className
      )}
      {...props}
    />
  );
}

// Pre-built skeleton variants for common use cases
function SkeletonText({ className, lines = 3, ...props }: SkeletonProps & { lines?: number }) {
  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-4", i === lines - 1 && "w-4/5")}
        />
      ))}
    </div>
  );
}

function SkeletonCard({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn("rounded-lg border p-4 space-y-4", className)} {...props}>
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

function SkeletonAvatar({ className, size = "default", ...props }: SkeletonProps & { size?: "sm" | "default" | "lg" }) {
  const sizeClasses = {
    sm: "h-8 w-8",
    default: "h-10 w-10",
    lg: "h-14 w-14",
  };
  
  return (
    <Skeleton
      className={cn("rounded-full", sizeClasses[size], className)}
      {...props}
    />
  );
}

export { Skeleton, SkeletonText, SkeletonCard, SkeletonAvatar };
