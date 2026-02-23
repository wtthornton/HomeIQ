import React from 'react';

interface SkeletonListProps {
  count?: number;
  itemHeight?: string;
  spacing?: string;
  className?: string;
}

export const SkeletonList: React.FC<SkeletonListProps> = ({
  count = 3,
  itemHeight = 'h-16',
  spacing = 'space-y-3',
  className = ''
}) => {
  return (
    <div className={`${spacing} ${className}`}>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`${itemHeight} bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse shimmer`}
        />
      ))}
    </div>
  );
};

