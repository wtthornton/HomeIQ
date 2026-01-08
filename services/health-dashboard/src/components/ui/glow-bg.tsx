import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const glowBgVariants = cva(
  "relative overflow-hidden",
  {
    variants: {
      color: {
        primary: "",
        success: "",
        warning: "",
        error: "",
        weather: "",
        sports: "",
        automation: "",
        energy: "",
      },
      intensity: {
        low: "",
        medium: "",
        high: "",
      },
      animated: {
        true: "",
        false: "",
      },
    },
    defaultVariants: {
      color: "primary",
      intensity: "medium",
      animated: false,
    },
  }
);

const getGlowStyles = (
  color: string,
  intensity: string,
  animated: boolean
): React.CSSProperties => {
  const colorMap: Record<string, string> = {
    primary: "hsl(217, 91%, 50%)",
    success: "hsl(142, 76%, 36%)",
    warning: "hsl(38, 92%, 50%)",
    error: "hsl(0, 84%, 60%)",
    weather: "hsl(199, 89%, 48%)",
    sports: "hsl(262, 83%, 58%)",
    automation: "hsl(25, 95%, 53%)",
    energy: "hsl(142, 71%, 45%)",
  };

  const opacityMap: Record<string, number> = {
    low: 0.1,
    medium: 0.2,
    high: 0.3,
  };

  const glowColor = colorMap[color] || colorMap.primary;
  const opacity = opacityMap[intensity] || opacityMap.medium;

  return {
    background: `radial-gradient(ellipse at center, ${glowColor.replace(")", ` / ${opacity})`)} 0%, transparent 70%)`,
    animation: animated ? "glow 2s ease-in-out infinite" : undefined,
  };
};

export interface GlowBgProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof glowBgVariants> {
  blur?: number;
}

const GlowBg = React.forwardRef<HTMLDivElement, GlowBgProps>(
  ({ className, color = "primary", intensity = "medium", animated = false, blur = 40, children, style, ...props }, ref) => {
    const glowStyles = getGlowStyles(color, intensity, animated);

    return (
      <div
        ref={ref}
        className={cn(glowBgVariants({ color, intensity, animated }), className)}
        style={style}
        {...props}
      >
        {/* Glow layer */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            ...glowStyles,
            filter: `blur(${blur}px)`,
          }}
        />
        {/* Content layer */}
        <div className="relative z-10">{children}</div>
      </div>
    );
  }
);
GlowBg.displayName = "GlowBg";

// Gradient background component for cards
interface GradientBgProps extends React.HTMLAttributes<HTMLDivElement> {
  from?: string;
  to?: string;
  direction?: "to-t" | "to-tr" | "to-r" | "to-br" | "to-b" | "to-bl" | "to-l" | "to-tl";
}

const GradientBg = React.forwardRef<HTMLDivElement, GradientBgProps>(
  ({ className, from = "primary", to = "transparent", direction = "to-br", children, ...props }, ref) => {
    const fromMap: Record<string, string> = {
      primary: "from-primary/10",
      success: "from-status-healthy/10",
      warning: "from-status-warning/10",
      error: "from-status-critical/10",
    };

    return (
      <div
        ref={ref}
        className={cn(
          "relative overflow-hidden",
          `bg-gradient-${direction}`,
          fromMap[from] || fromMap.primary,
          "via-transparent to-transparent",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
GradientBg.displayName = "GradientBg";

// Ambient glow for dashboard sections
interface AmbientGlowProps extends React.HTMLAttributes<HTMLDivElement> {
  color?: "primary" | "success" | "warning" | "error";
  position?: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";
}

const AmbientGlow = React.forwardRef<HTMLDivElement, AmbientGlowProps>(
  ({ className, color = "primary", position = "top-right", children, ...props }, ref) => {
    const colorMap: Record<string, string> = {
      primary: "bg-primary/20",
      success: "bg-status-healthy/20",
      warning: "bg-status-warning/20",
      error: "bg-status-critical/20",
    };

    const positionMap: Record<string, string> = {
      "top-left": "-top-20 -left-20",
      "top-right": "-top-20 -right-20",
      "bottom-left": "-bottom-20 -left-20",
      "bottom-right": "-bottom-20 -right-20",
      center: "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
    };

    return (
      <div ref={ref} className={cn("relative overflow-hidden", className)} {...props}>
        <div
          className={cn(
            "absolute w-40 h-40 rounded-full blur-3xl opacity-50",
            colorMap[color],
            positionMap[position]
          )}
        />
        <div className="relative z-10">{children}</div>
      </div>
    );
  }
);
AmbientGlow.displayName = "AmbientGlow";

export { GlowBg, GradientBg, AmbientGlow };
