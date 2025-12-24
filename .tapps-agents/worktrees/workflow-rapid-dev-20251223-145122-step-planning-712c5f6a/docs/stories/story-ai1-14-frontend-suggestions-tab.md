# Story AI1.14: Frontend - Suggestions Tab

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.14  
**Priority:** Critical  
**Estimated Effort:** 12-14 hours  
**Dependencies:** Story AI1.13 (Frontend shell), Story AI1.10 (API endpoints)

---

## User Story

**As a** user  
**I want** to browse automation suggestions in a card grid  
**so that** I can review AI-generated automations

---

## Business Value

- Primary user interface for browsing suggestions
- Enables approve/reject workflow
- Provides confidence-based filtering
- Shows AI explanations for transparency

---

## Acceptance Criteria

1. ✅ Displays suggestions in responsive card grid (1/2/3 columns)
2. ✅ Search filters by title or device name
3. ✅ Filter by status (pending, approved, deployed, rejected)
4. ✅ Filter by confidence threshold (>70%, >80%, >90%)
5. ✅ Click card opens detail modal with pattern analysis
6. ✅ Modal shows editable YAML preview
7. ✅ Approve button deploys to HA (calls /api/deploy/{id})
8. ✅ Reject button updates status
9. ✅ Loading states show skeleton cards
10. ✅ Mobile responsive (44px touch targets)

---

## Technical Implementation Notes

### Suggestions Tab Component

**Create: src/components/tabs/SuggestionsTab.tsx**

**Reference: health-dashboard/src/components/tabs/OverviewTab.tsx (card grid pattern)**

```typescript
import React, { useState } from 'react';
import { useSuggestions } from '../../hooks/useSuggestions';
import { SuggestionCard } from '../SuggestionCard';
import { SuggestionDetailModal } from '../SuggestionDetailModal';
import { SkeletonCard } from '../skeletons';
import type { TabProps } from './types';
import type { Suggestion } from '../../types';

export const SuggestionsTab: React.FC<TabProps> = ({ darkMode }) => {
  const { suggestions, loading, error, refresh } = useSuggestions();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState(0.7);
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);
  
  // Filter suggestions
  const filteredSuggestions = suggestions.filter(s => {
    const matchesSearch = !searchTerm || 
      s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = !statusFilter || s.status === statusFilter;
    const matchesConfidence = s.confidence >= confidenceFilter;
    
    return matchesSearch && matchesStatus && matchesConfidence;
  });
  
  if (loading && suggestions.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`p-8 text-center ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
        <p>Failed to load suggestions: {error}</p>
        <button onClick={refresh} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg">
          Retry
        </button>
      </div>
    );
  }
  
  return (
    <div>
      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <input
          type="text"
          placeholder="Search suggestions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={`w-full px-4 py-2 rounded-lg border ${
            darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
          }`}
        />
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`px-4 py-2 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="deployed">Deployed</option>
            <option value="rejected">Rejected</option>
          </select>
          
          {/* Confidence Filter */}
          <select
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(parseFloat(e.target.value))}
            className={`px-4 py-2 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
          >
            <option value="0">All Confidence</option>
            <option value="0.7">70%+ Confidence</option>
            <option value="0.8">80%+ Confidence</option>
            <option value="0.9">90%+ Confidence</option>
          </select>
          
          {/* Results Count */}
          <div className={`flex items-center justify-end px-4 py-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {filteredSuggestions.length} suggestions
          </div>
        </div>
      </div>
      
      {/* Suggestion Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSuggestions.map(suggestion => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            darkMode={darkMode}
            onClick={() => setSelectedSuggestion(suggestion)}
          />
        ))}
      </div>
      
      {/* Empty State */}
      {filteredSuggestions.length === 0 && (
        <div className={`text-center py-12 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <p className="text-lg">No suggestions found</p>
          <p className="text-sm mt-2">Try adjusting your filters or wait for the next analysis run</p>
        </div>
      )}
      
      {/* Detail Modal */}
      {selectedSuggestion && (
        <SuggestionDetailModal
          suggestion={selectedSuggestion}
          onClose={() => setSelectedSuggestion(null)}
          onApprove={async (id) => {
            await approveSuggestion(id);
            setSelectedSuggestion(null);
            refresh();
          }}
          onReject={async (id) => {
            await rejectSuggestion(id);
            setSelectedSuggestion(null);
            refresh();
          }}
          darkMode={darkMode}
        />
      )}
    </div>
  );
};
```

### Suggestion Card Component

**Create: src/components/SuggestionCard.tsx**

**Reference: health-dashboard/src/components/CoreSystemCard.tsx**

```typescript
import React from 'react';
import type { Suggestion } from '../types';

interface Props {
  suggestion: Suggestion;
  darkMode: boolean;
  onClick: () => void;
}

const getStatusColors = (status: string, darkMode: boolean) => {
  const colors = {
    pending: {
      bg: darkMode ? 'bg-blue-900/30' : 'bg-blue-100',
      border: darkMode ? 'border-blue-700' : 'border-blue-300',
      text: darkMode ? 'text-blue-200' : 'text-blue-800',
      icon: '⏳'
    },
    approved: {
      bg: darkMode ? 'bg-green-900/30' : 'bg-green-100',
      border: darkMode ? 'border-green-700' : 'border-green-300',
      text: darkMode ? 'text-green-200' : 'text-green-800',
      icon: '✅'
    },
    deployed: {
      bg: darkMode ? 'bg-purple-900/30' : 'bg-purple-100',
      border: darkMode ? 'border-purple-700' : 'border-purple-300',
      text: darkMode ? 'text-purple-200' : 'text-purple-800',
      icon: '🚀'
    },
    rejected: {
      bg: darkMode ? 'bg-red-900/30' : 'bg-red-100',
      border: darkMode ? 'border-red-700' : 'border-red-300',
      text: darkMode ? 'text-red-200' : 'text-red-800',
      icon: '❌'
    }
  };
  return colors[status] || colors.pending;
};

export const SuggestionCard: React.FC<Props> = ({ suggestion, darkMode, onClick }) => {
  const statusColors = getStatusColors(suggestion.status, darkMode);
  
  return (
    <div
      onClick={onClick}
      className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition-shadow`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          💡 {suggestion.title}
        </h3>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors.bg} ${statusColors.text} ${statusColors.border} border`}>
          {statusColors.icon} {suggestion.status}
        </span>
      </div>
      
      {/* Description */}
      <p className={`text-sm mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
        {suggestion.description}
      </p>
      
      {/* Confidence */}
      <div className="flex items-center justify-between">
        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Confidence: {(suggestion.confidence * 100).toFixed(0)}%
        </div>
        <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">
          View Details →
        </div>
      </div>
    </div>
  );
};
```

### Custom Hook

**Create: src/hooks/useSuggestions.ts**

**Reference: health-dashboard/src/hooks/useHealth.ts**

```typescript
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { Suggestion } from '../types';

export function useSuggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchSuggestions = async () => {
    try {
      setLoading(true);
      const data = await apiService.getSuggestions();
      setSuggestions(data.suggestions);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchSuggestions();
    
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchSuggestions, 60000);
    return () => clearInterval(interval);
  }, []);
  
  return {
    suggestions,
    loading,
    error,
    refresh: fetchSuggestions
  };
}
```

---

## Definition of Done

- [ ] SuggestionsTab component implemented
- [ ] SuggestionCard component created
- [ ] SuggestionDetailModal created
- [ ] Search and filter controls working
- [ ] Status color coding functional
- [ ] Click card opens modal
- [ ] Approve/reject actions working
- [ ] Loading skeletons displayed
- [ ] useSuggestions hook implemented
- [ ] Mobile responsive (tested on phone)
- [ ] Matches health-dashboard design
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- `health-dashboard/src/components/tabs/OverviewTab.tsx` - Card grid
- `health-dashboard/src/components/CoreSystemCard.tsx` - Card component
- `health-dashboard/src/components/ServiceDetailsModal.tsx` - Modal pattern
- `health-dashboard/src/hooks/useHealth.ts` - Custom hook pattern

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

