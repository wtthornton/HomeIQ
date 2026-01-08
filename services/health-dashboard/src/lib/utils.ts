import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility function for merging Tailwind CSS classes with proper conflict resolution.
 * Combines clsx for conditional classes and tailwind-merge for deduplication.
 * 
 * @example
 * cn('px-4 py-2', 'px-8') // returns 'py-2 px-8'
 * cn('text-red-500', isError && 'text-red-700')
 * cn(buttonVariants({ variant }), className)
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
