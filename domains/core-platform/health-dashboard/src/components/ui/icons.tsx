/**
 * HomeIQ Icon System
 * 
 * Centralized icon library using Lucide icons.
 * Replaces emojis with clean, consistent SVG icons.
 */

import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Bell,
  Bot,
  Calendar,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  CircleDot,
  CircleMinus,
  Clock,
  Cloud,
  CloudRain,
  Cog,
  Database,
  Flame,
  Gauge,
  GitBranch,
  Globe,
  Heart,
  Home,
  Info,
  Laptop,
  LayoutDashboard,
  Lightbulb,
  Link,
  List,
  Loader2,
  Moon,
  Network,
  Octagon,
  Pause,
  Play,
  Power,
  RefreshCw,
  Router,
  Search,
  Server,
  Settings,
  Shield,
  Smartphone,
  Sparkles,
  Square,
  Sun,
  Terminal,
  Thermometer,
  Timer,
  Trophy,
  Tv,
  Unplug,
  Wifi,
  WifiOff,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Icon size variants
export type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

const sizeClasses: Record<IconSize, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
};

interface IconProps {
  icon: LucideIcon;
  size?: IconSize;
  className?: string;
  'aria-label'?: string;
}

// Generic Icon wrapper component
export const Icon: React.FC<IconProps> = ({
  icon: IconComponent,
  size = 'md',
  className,
  'aria-label': ariaLabel,
}) => (
  <IconComponent
    className={cn(sizeClasses[size], className)}
    aria-label={ariaLabel}
    aria-hidden={!ariaLabel}
  />
);

// Tab/Navigation icons mapping (replaces emojis)
export const TabIcons = {
  overview: LayoutDashboard,
  setup: Heart,
  services: Server,
  groups: Network,
  dependencies: GitBranch,
  devices: Smartphone,
  events: Activity,
  logs: Terminal,
  sports: Trophy,
  'data-sources': Database,
  energy: Zap,
  analytics: BarChart3,
  alerts: Bell,
  hygiene: Shield,
  validation: Search,
  synergies: Link,
  evaluation: Bot,
  configuration: Settings,
} as const;

// Status icons — 508 compliant: shape conveys meaning, not just color
// Checkmark circle = healthy, Triangle = warning, Octagon = error (stop sign), Minus circle = offline
export const StatusIcons = {
  healthy: CheckCircle,
  running: CheckCircle,
  warning: AlertTriangle,
  degraded: AlertTriangle,
  critical: Octagon,
  error: Octagon,
  offline: CircleMinus,
  stopped: CircleMinus,
  connected: Wifi,
  disconnected: WifiOff,
  unknown: CircleDot,
} as const;

// Action icons
export const ActionIcons = {
  start: Play,
  stop: Square,
  restart: RefreshCw,
  configure: Cog,
  view: ChevronRight,
  refresh: RefreshCw,
  close: X,
  expand: ChevronDown,
} as const;

// Theme icons
export const ThemeIcons = {
  light: Sun,
  dark: Moon,
} as const;

// Device/Category icons
export const DeviceIcons = {
  light: Lightbulb,
  switch: Power,
  sensor: Gauge,
  climate: Thermometer,
  weather: Cloud,
  media: Tv,
  network: Router,
  automation: Bot,
  default: Laptop,
} as const;

// Trend icons
export const TrendIcons = {
  up: ArrowUp,
  down: ArrowDown,
  stable: ArrowRight,
} as const;

// Helper function to get status icon
export const getStatusIcon = (status: string): LucideIcon => {
  return StatusIcons[status as keyof typeof StatusIcons] || StatusIcons.unknown;
};

// Status indicator component with dot
interface StatusIndicatorProps {
  status: 'healthy' | 'warning' | 'critical' | 'offline' | 'running' | 'stopped' | 'error' | 'degraded';
  size?: IconSize;
  showDot?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  size = 'sm',
  showDot: _showDot = true,
  className,
}) => {
  const StatusIcon = getStatusIcon(status);

  const colorClasses: Record<string, string> = {
    healthy: 'text-status-healthy',
    running: 'text-status-healthy',
    warning: 'text-status-warning',
    degraded: 'text-status-warning',
    critical: 'text-status-critical',
    error: 'text-status-critical',
    offline: 'text-status-offline',
    stopped: 'text-status-offline',
  };

  // 508 Compliance: descriptive labels for screen readers
  const statusLabels: Record<string, string> = {
    healthy: 'Healthy',
    running: 'Running',
    warning: 'Warning',
    degraded: 'Degraded',
    critical: 'Critical',
    error: 'Error',
    offline: 'Offline',
    stopped: 'Stopped',
  };

  // 508 Compliance: Always render a distinct icon shape — never a color-only dot.
  // Shape conveys meaning independently of color:
  //   CheckCircle = healthy/running
  //   AlertTriangle = warning/degraded
  //   Octagon (stop sign) = critical/error
  //   CircleMinus = offline/stopped
  return (
    <StatusIcon
      className={cn(sizeClasses[size], colorClasses[status], className)}
      role="img"
      aria-label={`Status: ${statusLabels[status] || status}`}
    />
  );
};

// Loading spinner component
interface SpinnerProps {
  size?: IconSize;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className }) => (
  <Loader2 className={cn(sizeClasses[size], 'animate-spin', className)} aria-label="Loading" />
);

// Live indicator (pulsing dot)
interface LiveIndicatorProps {
  size?: 'sm' | 'md';
  className?: string;
}

export const LiveIndicator: React.FC<LiveIndicatorProps> = ({ size = 'sm', className }) => {
  const sizeClass = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3';
  
  return (
    <span className={cn('relative flex', sizeClass, className)}>
      <span className={cn(
        'animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75'
      )} />
      <span className={cn(
        'relative inline-flex rounded-full bg-primary',
        sizeClass
      )} />
    </span>
  );
};

// Re-export commonly used icons for convenience
export {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Bell,
  Bot,
  Calendar,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  CircleDot,
  CircleMinus,
  Clock,
  Cloud,
  CloudRain,
  Cog,
  Database,
  Flame,
  Gauge,
  GitBranch,
  Globe,
  Heart,
  Home,
  Info,
  Laptop,
  LayoutDashboard,
  Lightbulb,
  Link,
  List,
  Loader2,
  Moon,
  Network,
  Octagon,
  Pause,
  Play,
  Power,
  RefreshCw,
  Router,
  Search,
  Server,
  Settings,
  Shield,
  Smartphone,
  Sparkles,
  Square,
  Sun,
  Terminal,
  Thermometer,
  Timer,
  Trophy,
  Tv,
  Unplug,
  Wifi,
  WifiOff,
  X,
  Zap,
};
