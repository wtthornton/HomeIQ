/**
 * Enhanced Search Bar Component
 * Search and filter suggestions with improved UX
 */

import React from 'react';
import { FilterPills, type FilterOption } from './FilterPills';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onCategoryFilter: (category: string | null) => void;
  onConfidenceFilter: (levels: string[]) => void;
  selectedCategory: string | null;
  selectedConfidenceLevels: string[];
  darkMode?: boolean;
  suggestionCounts?: {
    categories: Record<string, number>;
    confidence: Record<string, number>;
  };
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  onCategoryFilter,
  onConfidenceFilter,
  selectedCategory,
  selectedConfidenceLevels,
  darkMode = false,
  suggestionCounts
}) => {
  // Category filter options
  const categoryOptions: FilterOption[] = [
    { value: 'energy', label: 'Energy', icon: '🌱' },
    { value: 'comfort', label: 'Comfort', icon: '💙' },
    { value: 'security', label: 'Security', icon: '🔐' },
    { value: 'convenience', label: 'Convenience', icon: '✨' }
  ];

  // Confidence filter options
  const confidenceOptions: FilterOption[] = [
    { value: 'high', label: 'High', icon: '🟢' },
    { value: 'medium', label: 'Medium', icon: '🟡' },
    { value: 'low', label: 'Low', icon: '🔴' }
  ];

  // Add counts if available
  const categoryOptionsWithCounts = suggestionCounts?.categories 
    ? categoryOptions.map(opt => ({
        ...opt,
        count: suggestionCounts.categories[opt.value] || 0
      }))
    : categoryOptions;

  const confidenceOptionsWithCounts = suggestionCounts?.confidence
    ? confidenceOptions.map(opt => ({
        ...opt,
        count: suggestionCounts.confidence[opt.value] || 0
      }))
    : confidenceOptions;

  const handleCategorySelection = (selected: string[]) => {
    if (selected.length === 0) {
      onCategoryFilter(null);
    } else {
      // For now, only allow single category selection
      onCategoryFilter(selected[selected.length - 1]);
    }
  };

  return (
    <div className="space-y-3">
      {/* Search Input */}
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search by device, title, or description..."
          className={`w-full px-3 py-2 pl-10 border rounded-xl focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all ${
            darkMode
              ? 'bg-slate-800/60 border-gray-700/50 text-white placeholder-gray-500 backdrop-blur-sm'
              : 'bg-white/80 border-gray-300/50 text-gray-900 placeholder-gray-400 backdrop-blur-sm'
          }`}
        />
        <div className="absolute left-3 top-2.5 text-gray-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        {value && (
          <button
            onClick={() => onChange('')}
            className={`absolute right-3 top-2.5 ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-400 hover:text-gray-900'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Enhanced Filters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Category Filter Pills */}
        <FilterPills
          type="category"
          options={categoryOptionsWithCounts}
          selected={selectedCategory ? [selectedCategory] : []}
          onSelectionChange={handleCategorySelection}
          darkMode={darkMode}
          showCounts={!!suggestionCounts}
        />

        {/* Confidence Filter Pills */}
        <FilterPills
          type="confidence"
          options={confidenceOptionsWithCounts}
          selected={selectedConfidenceLevels}
          onSelectionChange={onConfidenceFilter}
          darkMode={darkMode}
          showCounts={!!suggestionCounts}
        />
      </div>
    </div>
  );
};

