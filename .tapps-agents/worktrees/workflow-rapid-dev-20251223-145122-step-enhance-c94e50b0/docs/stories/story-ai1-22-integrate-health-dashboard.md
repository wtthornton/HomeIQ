# Story AI1.22: Integrate with Health Dashboard

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.22  
**Priority:** Critical  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.10 (API endpoints), Story AI1.19 (Safety Validation), Story AI1.20 (Audit Trail)

---

## User Story

**As a** user  
**I want** AI automation features integrated into the health-dashboard  
**so that** I have a unified interface without switching between applications

---

## Business Value

- **Unified user experience** - Single dashboard for all home automation needs
- **Reduced context switching** - No separate app to manage
- **Consistent design** - Reuses existing health-dashboard components and patterns
- **Shared authentication** - Single login, unified permissions
- **Better discoverability** - Users find AI features naturally while browsing dashboard
- **Simplified deployment** - One frontend to build and maintain

---

## Acceptance Criteria

1. ✅ New "AI Automations" tab added to health-dashboard (13th tab)
2. ✅ Tab displays pending suggestions with approve/reject workflow
3. ✅ Safety validation results shown before approval
4. ✅ Audit history viewable for deployed automations
5. ✅ Natural language request input integrated
6. ✅ Rollback functionality accessible from UI
7. ✅ Matches existing dashboard design (TailwindCSS, dark mode support)
8. ✅ Mobile responsive (works on phones and tablets)
9. ✅ Loading states and error handling consistent with other tabs
10. ✅ Real-time updates via WebSocket (optional Phase 2)

---

## Technical Implementation Notes

### Architecture Decision: Consolidate Frontend

**Original Epic AI1 Plan:** Separate React app (`ai-automation-frontend` on port 3002)  
**Enhanced Plan:** Integrate into existing `health-dashboard` (port 3000) as new tab

**Benefits:**
- Single codebase for all frontend features
- Reuse existing components (cards, modals, buttons)
- Consistent design system and UX patterns
- Shared state management and API clients
- Simplified deployment (one Docker container)

### New Tab Structure

**Update: services/health-dashboard/src/components/Dashboard.tsx**

```typescript
const TABS = [
  { id: 'overview', name: 'Overview', icon: '📊' },
  { id: 'services', name: 'Services', icon: '🔧' },
  { id: 'dependencies', name: 'Dependencies', icon: '🔗' },
  { id: 'devices', name: 'Devices', icon: '💡' },
  { id: 'events', name: 'Events', icon: '📡' },
  { id: 'logs', name: 'Logs', icon: '📋' },
  { id: 'sports', name: 'Sports', icon: '🏈' },
  { id: 'data-sources', name: 'Data Sources', icon: '📊' },
  { id: 'energy', name: 'Energy', icon: '⚡' },
  { id: 'analytics', name: 'Analytics', icon: '📈' },
  { id: 'alerts', name: 'Alerts', icon: '🔔' },
  { id: 'configuration', name: 'Configuration', icon: '⚙️' },
  { id: 'ai-automations', name: 'AI Automations', icon: '🤖' }, // NEW TAB
];
```

### AI Automations Tab Component

**Create: services/health-dashboard/src/components/tabs/AIAutomationsTab.tsx**

```typescript
import React, { useState } from 'react';
import { useSuggestions } from '../../hooks/useSuggestions';
import { SuggestionsList } from '../ai-automations/SuggestionsList';
import { NLRequestInput } from '../ai-automations/NLRequestInput';
import { AuditHistory } from '../ai-automations/AuditHistory';
import { SafetyReport } from '../ai-automations/SafetyReport';
import type { TabProps } from './types';

export const AIAutomationsTab: React.FC<TabProps> = ({ darkMode }) => {
  const [activeView, setActiveView] = useState<'suggestions' | 'audit' | 'create'>('suggestions');
  const { suggestions, loading, error, refresh } = useSuggestions();
  
  return (
    <div className="space-y-6">
      {/* Header with View Selector */}
      <div className="flex items-center justify-between">
        <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🤖 AI Automations
        </h2>
        
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveView('suggestions')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeView === 'suggestions'
                ? 'bg-blue-600 text-white'
                : darkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            💡 Suggestions
          </button>
          
          <button
            onClick={() => setActiveView('create')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeView === 'create'
                ? 'bg-blue-600 text-white'
                : darkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            ✨ Create
          </button>
          
          <button
            onClick={() => setActiveView('audit')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeView === 'audit'
                ? 'bg-blue-600 text-white'
                : darkMode
                ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            📜 History
          </button>
        </div>
      </div>
      
      {/* Content Views */}
      {activeView === 'suggestions' && (
        <SuggestionsList
          suggestions={suggestions}
          loading={loading}
          error={error}
          onRefresh={refresh}
          darkMode={darkMode}
        />
      )}
      
      {activeView === 'create' && (
        <NLRequestInput
          darkMode={darkMode}
          onSuccess={refresh}
        />
      )}
      
      {activeView === 'audit' && (
        <AuditHistory
          darkMode={darkMode}
        />
      )}
    </div>
  );
};
```

### Suggestions List Component

**Create: services/health-dashboard/src/components/ai-automations/SuggestionsList.tsx**

```typescript
import React, { useState } from 'react';
import { SuggestionCard } from './SuggestionCard';
import { SuggestionDetailModal } from './SuggestionDetailModal';
import { SkeletonCard } from '../skeletons';
import type { Suggestion } from '../../types';

interface Props {
  suggestions: Suggestion[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  darkMode: boolean;
}

export const SuggestionsList: React.FC<Props> = ({
  suggestions,
  loading,
  error,
  onRefresh,
  darkMode
}) => {
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  // Filter suggestions
  const filteredSuggestions = suggestions.filter(s => {
    const matchesSearch = !searchTerm || 
      s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = !statusFilter || s.status === statusFilter;
    
    return matchesSearch && matchesStatus;
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
      <div className={`p-8 text-center rounded-lg ${
        darkMode ? 'bg-red-900/20 text-red-300' : 'bg-red-100 text-red-600'
      }`}>
        <p className="text-lg font-semibold mb-2">⚠️ Failed to load suggestions</p>
        <p className="text-sm mb-4">{error}</p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Try Again
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
            darkMode
              ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
              : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
          } focus:outline-none focus:ring-2 focus:ring-blue-500`}
        />
        
        <div className="flex items-center justify-between">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`px-4 py-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="deployed">Deployed</option>
            <option value="rejected">Rejected</option>
          </select>
          
          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {filteredSuggestions.length} suggestion{filteredSuggestions.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
      
      {/* Suggestions Grid */}
      {filteredSuggestions.length > 0 ? (
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
      ) : (
        <div className={`text-center py-12 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <p className="text-lg mb-2">No suggestions found</p>
          <p className="text-sm">
            {searchTerm || statusFilter
              ? 'Try adjusting your filters'
              : 'Create a new automation or wait for the next analysis run'}
          </p>
        </div>
      )}
      
      {/* Detail Modal */}
      {selectedSuggestion && (
        <SuggestionDetailModal
          suggestion={selectedSuggestion}
          onClose={() => setSelectedSuggestion(null)}
          onRefresh={onRefresh}
          darkMode={darkMode}
        />
      )}
    </div>
  );
};
```

### Suggestion Detail Modal (with Safety & Rollback)

**Create: services/health-dashboard/src/components/ai-automations/SuggestionDetailModal.tsx**

```typescript
import React, { useState } from 'react';
import { approveSuggestion, rejectSuggestion, rollbackAutomation } from '../../services/api';
import { SafetyReport } from './SafetyReport';
import { YAMLViewer } from './YAMLViewer';
import type { Suggestion } from '../../types';

interface Props {
  suggestion: Suggestion;
  onClose: () => void;
  onRefresh: () => void;
  darkMode: boolean;
}

export const SuggestionDetailModal: React.FC<Props> = ({
  suggestion,
  onClose,
  onRefresh,
  darkMode
}) => {
  const [loading, setLoading] = useState(false);
  const [safetyReport, setSafetyReport] = useState(null);
  const [showRollback, setShowRollback] = useState(false);
  const [rollbackReason, setRollbackReason] = useState('');
  
  const handleApprove = async () => {
    setLoading(true);
    try {
      const result = await approveSuggestion(suggestion.id);
      setSafetyReport(result.safety_report);
      
      if (result.safety_passed) {
        onRefresh();
        onClose();
      }
    } catch (error) {
      console.error('Approval failed:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleReject = async () => {
    setLoading(true);
    try {
      await rejectSuggestion(suggestion.id);
      onRefresh();
      onClose();
    } finally {
      setLoading(false);
    }
  };
  
  const handleRollback = async () => {
    if (!rollbackReason.trim()) {
      alert('Please provide a reason for rollback');
      return;
    }
    
    setLoading(true);
    try {
      await rollbackAutomation(suggestion.ha_automation_id, rollbackReason);
      onRefresh();
      onClose();
    } catch (error) {
      console.error('Rollback failed:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div
        className={`max-w-4xl w-full max-h-[90vh] overflow-y-auto rounded-xl shadow-2xl ${
          darkMode ? 'bg-gray-800' : 'bg-white'
        }`}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">💡 {suggestion.title}</h2>
              <p className="text-blue-100">{suggestion.description}</p>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white text-2xl"
            >
              ×
            </button>
          </div>
          
          {/* Status Badge */}
          <div className="mt-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              suggestion.status === 'deployed'
                ? 'bg-green-500/20 text-green-100'
                : suggestion.status === 'approved'
                ? 'bg-blue-500/20 text-blue-100'
                : 'bg-yellow-500/20 text-yellow-100'
            }`}>
              {suggestion.status.toUpperCase()}
            </span>
            <span className="ml-3 text-sm text-blue-100">
              Confidence: {(suggestion.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-6">
          {/* YAML Preview */}
          <div>
            <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              📄 Automation YAML
            </h3>
            <YAMLViewer
              yaml={suggestion.automation_yaml}
              darkMode={darkMode}
            />
          </div>
          
          {/* Safety Report */}
          {safetyReport && (
            <SafetyReport
              report={safetyReport}
              darkMode={darkMode}
            />
          )}
          
          {/* Rollback Section (if deployed) */}
          {suggestion.status === 'deployed' && (
            <div className={`p-4 rounded-lg border ${
              darkMode
                ? 'bg-red-900/20 border-red-700'
                : 'bg-red-50 border-red-200'
            }`}>
              <h3 className={`text-lg font-semibold mb-3 ${
                darkMode ? 'text-red-300' : 'text-red-700'
              }`}>
                ⚠️ Rollback Automation
              </h3>
              
              {!showRollback ? (
                <button
                  onClick={() => setShowRollback(true)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Rollback to Previous Version
                </button>
              ) : (
                <div className="space-y-3">
                  <textarea
                    value={rollbackReason}
                    onChange={(e) => setRollbackReason(e.target.value)}
                    placeholder="Why are you rolling back this automation?"
                    className={`w-full px-3 py-2 rounded-lg border ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white'
                        : 'bg-white border-gray-300 text-gray-900'
                    }`}
                    rows={3}
                  />
                  <div className="flex space-x-2">
                    <button
                      onClick={handleRollback}
                      disabled={loading}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                      {loading ? 'Rolling back...' : 'Confirm Rollback'}
                    </button>
                    <button
                      onClick={() => setShowRollback(false)}
                      className={`px-4 py-2 rounded-lg transition-colors ${
                        darkMode
                          ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Actions */}
        {suggestion.status === 'pending' && (
          <div className={`sticky bottom-0 p-6 border-t ${
            darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'
          }`}>
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleReject}
                disabled={loading}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                } disabled:opacity-50`}
              >
                ❌ Reject
              </button>
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                {loading ? '⏳ Approving...' : '✅ Approve & Deploy'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

### Natural Language Request Input

**Create: services/health-dashboard/src/components/ai-automations/NLRequestInput.tsx**

```typescript
import React, { useState } from 'react';
import { generateFromNL } from '../../services/api';

interface Props {
  darkMode: boolean;
  onSuccess: () => void;
}

export const NLRequestInput: React.FC<Props> = ({ darkMode, onSuccess }) => {
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (request.length < 10) {
      alert('Please provide a more detailed request (at least 10 characters)');
      return;
    }
    
    setLoading(true);
    try {
      const generated = await generateFromNL(request);
      setResult(generated);
      
      if (generated.success) {
        onSuccess();
      }
    } catch (error) {
      console.error('Generation failed:', error);
      setResult({ success: false, error: error.message });
    } finally {
      setLoading(false);
    }
  };
  
  const examples = [
    "Turn off the heater when any window is open for more than 10 minutes",
    "Turn on kitchen lights at 7 AM on weekdays",
    "Send notification when front door is left open for 5 minutes",
    "Close all blinds when it's too sunny outside"
  ];
  
  return (
    <div className="space-y-6">
      {/* Instructions */}
      <div className={`p-6 rounded-lg ${
        darkMode ? 'bg-blue-900/20 border border-blue-700' : 'bg-blue-50 border border-blue-200'
      }`}>
        <h3 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
          ✨ Create Automation from Natural Language
        </h3>
        <p className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-600'}`}>
          Describe what you want your automation to do in plain English. Our AI will generate the automation for you!
        </p>
      </div>
      
      {/* Input Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={`block text-sm font-medium mb-2 ${
            darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            What should the automation do?
          </label>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="Example: Turn on living room lights when motion is detected after sunset"
            className={`w-full px-4 py-3 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            rows={4}
          />
          <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {request.length} characters (minimum 10)
          </p>
        </div>
        
        <button
          type="submit"
          disabled={loading || request.length < 10}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {loading ? '⏳ Generating automation...' : '✨ Generate Automation'}
        </button>
      </form>
      
      {/* Example Requests */}
      <div>
        <h4 className={`text-sm font-medium mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Example requests:
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {examples.map((example, idx) => (
            <button
              key={idx}
              onClick={() => setRequest(example)}
              className={`p-3 rounded-lg text-left text-sm transition-colors ${
                darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
      
      {/* Result */}
      {result && (
        <div className={`p-6 rounded-lg border ${
          result.success
            ? darkMode
              ? 'bg-green-900/20 border-green-700'
              : 'bg-green-50 border-green-200'
            : darkMode
            ? 'bg-red-900/20 border-red-700'
            : 'bg-red-50 border-red-200'
        }`}>
          {result.success ? (
            <div>
              <h3 className={`text-lg font-semibold mb-2 ${
                darkMode ? 'text-green-300' : 'text-green-700'
              }`}>
                ✅ Automation Generated!
              </h3>
              <p className={`text-sm mb-4 ${darkMode ? 'text-green-200' : 'text-green-600'}`}>
                {result.automation.description}
              </p>
              <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Review the automation in the "Suggestions" tab to approve and deploy it.
              </p>
            </div>
          ) : (
            <div>
              <h3 className={`text-lg font-semibold mb-2 ${
                darkMode ? 'text-red-300' : 'text-red-700'
              }`}>
                ❌ Generation Failed
              </h3>
              <p className={`text-sm ${darkMode ? 'text-red-200' : 'text-red-600'}`}>
                {result.error || 'Failed to generate automation. Please try again.'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

### API Service Updates

**Update: services/health-dashboard/src/services/api.ts**

```typescript
// Add AI automation endpoints
export const approveSuggestion = async (suggestionId: number) => {
  const response = await fetch(`${API_URL}/api/deploy/${suggestionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return response.json();
};

export const rejectSuggestion = async (suggestionId: number) => {
  const response = await fetch(`${API_URL}/api/suggestions/${suggestionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return response.json();
};

export const rollbackAutomation = async (automationId: string, reason: string) => {
  const response = await fetch(`${API_URL}/api/deploy/${automationId}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason })
  });
  return response.json();
};

export const generateFromNL = async (requestText: string) => {
  const response = await fetch(`${API_URL}/api/nl/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_text: requestText, user_id: 'default' })
  });
  return response.json();
};

export const getAuditHistory = async (automationId?: string) => {
  const url = automationId
    ? `${API_URL}/api/deploy/${automationId}/history`
    : `${API_URL}/api/deploy/audit/all`;
  const response = await fetch(url);
  return response.json();
};
```

---

## Integration Verification

**IV1: New tab appears in dashboard**
- Open health-dashboard
- Verify "AI Automations" tab visible
- Click tab → loads without errors

**IV2: Suggestions display correctly**
- Verify card grid matches other tabs (Services, Devices)
- Dark mode toggle works
- Mobile responsive layout verified

**IV3: Approve/reject workflow functional**
- Click suggestion card → modal opens
- Approve suggestion → safety validation runs
- Verify deployment to HA
- Audit record created

**IV4: Natural language generation works**
- Enter request → automation generated
- Appears in suggestions list
- Can approve and deploy

**IV5: Rollback accessible**
- Deployed automation shows rollback button
- Enter reason → rollback completes
- Previous version restored in HA

---

## Tasks Breakdown

1. **Add AI Automations tab to Dashboard** (0.5 hours)
2. **Create AIAutomationsTab component** (1 hour)
3. **Create SuggestionsList component** (1.5 hours)
4. **Create SuggestionDetailModal with safety/rollback** (2 hours)
5. **Create NLRequestInput component** (1.5 hours)
6. **Create AuditHistory component** (1 hour)
7. **Update API service with new endpoints** (0.5 hours)
8. **Styling and responsiveness** (1 hour)
9. **Integration testing** (1 hour)

**Total:** 8-10 hours

---

## Definition of Done

- [ ] AI Automations tab added to dashboard
- [ ] All components created and styled
- [ ] Suggestions list displays correctly
- [ ] Detail modal with approve/reject works
- [ ] Safety validation shown before approval
- [ ] Rollback functionality accessible
- [ ] NL request input functional
- [ ] Audit history viewable
- [ ] Dark mode fully supported
- [ ] Mobile responsive verified
- [ ] API integration complete
- [ ] Loading states and error handling
- [ ] Unit tests for components (Vitest)
- [ ] E2E test for complete flow (Playwright)
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

## Testing Strategy

### Component Tests (Vitest)

```typescript
// tests/components/AIAutomationsTab.test.tsx
import { render, screen } from '@testing-library/react';
import { AIAutomationsTab } from '../src/components/tabs/AIAutomationsTab';

describe('AIAutomationsTab', () => {
  it('renders three view buttons', () => {
    render(<AIAutomationsTab darkMode={false} />);
    
    expect(screen.getByText('💡 Suggestions')).toBeInTheDocument();
    expect(screen.getByText('✨ Create')).toBeInTheDocument();
    expect(screen.getByText('📜 History')).toBeInTheDocument();
  });
  
  it('switches views on button click', () => {
    render(<AIAutomationsTab darkMode={false} />);
    
    fireEvent.click(screen.getByText('✨ Create'));
    
    expect(screen.getByPlaceholderText(/Example:/)).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright)

```typescript
// tests/e2e/ai-automations.spec.ts
import { test, expect } from '@playwright/test';

test('complete automation approval flow', async ({ page }) => {
  // 1. Navigate to AI Automations tab
  await page.goto('http://localhost:3000');
  await page.click('text=AI Automations');
  
  // 2. Click suggestion card
  await page.click('.suggestion-card:first-child');
  
  // 3. Verify modal opens
  await expect(page.locator('.modal')).toBeVisible();
  
  // 4. Approve automation
  await page.click('text=Approve & Deploy');
  
  // 5. Wait for deployment
  await page.waitForSelector('text=deployed', { timeout: 10000 });
  
  // 6. Verify appears in deployed list
  await page.click('text=Suggestions');
  await page.selectOption('select', 'deployed');
  
  await expect(page.locator('.suggestion-card')).toBeVisible();
});

test('NL request generation flow', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.click('text=AI Automations');
  await page.click('text=✨ Create');
  
  // Enter request
  await page.fill('textarea', 'Turn on kitchen light at 7 AM');
  await page.click('text=Generate Automation');
  
  // Wait for generation
  await page.waitForSelector('text=Automation Generated', { timeout: 15000 });
  
  // Verify success message
  await expect(page.locator('text=✅')).toBeVisible();
});
```

---

## Reference Files

**Copy patterns from:**
- `health-dashboard/src/components/Dashboard.tsx` - Tab structure
- `health-dashboard/src/components/tabs/ServicesTab.tsx` - List view pattern
- `health-dashboard/src/components/tabs/DevicesTab.tsx` - Card grid pattern
- `health-dashboard/src/components/ServiceDetailsModal.tsx` - Modal pattern
- `health-dashboard/src/hooks/useHealth.ts` - Custom hook pattern

---

## Notes

- **Design consistency critical** - Should feel like native dashboard feature
- **Reuse existing components** - Cards, buttons, modals from shared components
- **No separate build** - All part of health-dashboard build process
- **URL routing** - Consider adding `/dashboard#ai-automations` deep linking
- Future enhancement: WebSocket real-time updates for suggestions
- Future enhancement: Bulk approve/reject multiple suggestions
- Future enhancement: Automation templates library

---

**Story Status:** Ready for Development  
**Assigned To:** TBD  
**Created:** 2025-10-16  
**Updated:** 2025-10-16

