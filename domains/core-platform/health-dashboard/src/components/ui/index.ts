/**
 * HomeIQ UI Component Library
 * 
 * Barrel export for all UI primitive components.
 * Based on shadcn/ui patterns with HomeIQ customizations.
 */

// Core Interactive Components
export { Button, buttonVariants, type ButtonProps } from './button';
export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  cardVariants,
  type CardProps,
} from './card';
export { Badge, badgeVariants, type BadgeProps } from './badge';
export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './dialog';
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
} from './dropdown-menu';
export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  SimpleTooltip,
} from './tooltip';
export {
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverAnchor,
} from './popover';
export {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type TabsListProps,
  type TabsTriggerProps,
} from './tabs';

// Form Components
export { Input, inputVariants, type InputProps } from './input';
export { Textarea, type TextareaProps } from './textarea';
export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
} from './select';
export { Checkbox, type CheckboxProps } from './checkbox';
export { Switch, type SwitchProps } from './switch';
export { Slider } from './slider';
export { Label } from './label';

// Feedback Components
export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonAvatar,
} from './skeleton';
export { Progress, CircularProgress, type ProgressProps } from './progress';
export {
  Toast,
  ToastAction,
  ToastClose,
  ToastTitle,
  ToastDescription,
  toastVariants,
  type ToastProps,
} from './toast';
export { Toaster, ToasterProvider, useToast, toast } from './toaster';
export {
  AlertDialog,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from './alert-dialog';

// Layout Components
export { Separator } from './separator';
export { ScrollArea, ScrollBar } from './scroll-area';
export { Avatar, AvatarImage, AvatarFallback, type AvatarProps } from './avatar';
export {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from './accordion';
export { GlowBg, GradientBg, AmbientGlow, type GlowBgProps } from './glow-bg';
