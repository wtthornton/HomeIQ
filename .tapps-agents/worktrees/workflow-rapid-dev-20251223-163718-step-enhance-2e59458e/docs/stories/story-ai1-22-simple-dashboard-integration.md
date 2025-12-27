# Story AI1.22: Simple Dashboard Integration (Simplified for Single Home)

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.22  
**Priority:** Critical  
**Estimated Effort:** 2-3 hours (Simplified from 8-10 hours)  
**Dependencies:** Story AI1.10 (API endpoints), Story AI1.19 (Safety Validation), Story AI1.20 (Rollback)

---

## User Story

**As a** user  
**I want** AI automation features in the health-dashboard  
**so that** I can manage automations without switching apps

---

## Business Value

- **Unified user experience** - Single dashboard for all features
- **No context switching** - Everything in one place
- **Simple and fast** - No complex navigation needed
- **Mobile friendly** - Works on phone

**Simplified for single home use case:**
- No complex filtering (5-10 suggestions max)
- No separate views (single page)
- No modals (inline expansion)
- Fast to implement and maintain

---

## Acceptance Criteria

1. ✅ New "AI Automations" tab added to health-dashboard (13th tab)
2. ✅ NL request input at top of tab
3. ✅ Suggestions list below input (simple list, not grid)
4. ✅ Inline approve/reject buttons (no modal needed)
5. ✅ Expandable YAML preview (click to show/hide)
6. ✅ Rollback button for deployed automations
7. ✅ Dark mode support
8. ✅ Mobile responsive (works on phone)

---

## Technical Implementation Notes

### Single-Page Layout (Simple!)

**Update: services/health-dashboard/src/components/Dashboard.tsx**

```typescript
const TABS = [
  // ... existing tabs ...
  { id: 'configuration', name: 'Configuration', icon: '⚙️' },
  { id: 'ai-automations', name: 'AI Automations', icon: '🤖' }, // NEW - 13th tab
];
```

### AI Automations Tab (Single View)

**Create: services/health-dashboard/src/components/tabs/AIAutomationsTab.tsx**

```typescript
import React, { useState } from 'react';
import { useSuggestions } from '../../hooks/useSuggestions';
import { NLInput } from '../ai/NLInput';
import { SuggestionItem } from '../ai/SuggestionItem';

export const AIAutomationsTab: React.FC<{ darkMode: boolean }> = ({ darkMode }) => {
  const { suggestions, loading, error, refresh } = useSuggestions();
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        🤖 AI Automations
      </h2>
      
      {/* NL Input at Top */}
      <NLInput darkMode={darkMode} onSuccess={refresh} />
      
      {/* Simple List of Suggestions */}
      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Suggestions ({suggestions.length})
        </h3>
        
        {loading && suggestions.length === 0 && (
          <div className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
            Loading suggestions...
          </div>
        )}
        
        {error && (
          <div className={`p-4 rounded-lg ${darkMode ? 'bg-red-900/20 text-red-300' : 'bg-red-100 text-red-600'}`}>
            {error}
          </div>
        )}
        
        {suggestions.map(suggestion => (
          <SuggestionItem
            key={suggestion.id}
            suggestion={suggestion}
            darkMode={darkMode}
            onRefresh={refresh}
          />
        ))}
        
        {suggestions.length === 0 && !loading && !error && (
          <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            No suggestions yet. Create one above or wait for the next analysis run.
          </div>
        )}
      </div>
    </div>
  );
};
```

### NL Input Component (Simple)

**Create: services/health-dashboard/src/components/ai/NLInput.tsx**

```typescript
import React, { useState } from 'react';

interface Props {
  darkMode: boolean;
  onSuccess: () => void;
}

export const NLInput: React.FC<Props> = ({ darkMode, onSuccess }) => {
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (request.length < 10) return;
    
    setLoading(true);
    setMessage('');
    
    try {
      const response = await fetch('http://localhost:8018/api/nl/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_text: request, user_id: 'default' })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessage('✅ Automation generated! See below.');
        setRequest('');
        onSuccess();
      } else {
        setMessage('❌ Failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      setMessage('❌ Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className={`p-6 rounded-lg border ${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300'
    }`}>
      <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        ✨ Create Automation
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="E.g., Turn on kitchen light at 7 AM on weekdays"
          className={`w-full px-3 py-2 rounded-lg border ${
            darkMode
              ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
              : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
          }`}
          rows={3}
        />
        
        <div className="flex items-center justify-between">
          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {request.length} chars (min 10)
          </span>
          <button
            type="submit"
            disabled={loading || request.length < 10}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </form>
      
      {message && (
        <div className={`mt-3 text-sm ${
          message.startsWith('✅') 
            ? (darkMode ? 'text-green-300' : 'text-green-600')
            : (darkMode ? 'text-red-300' : 'text-red-600')
        }`}>
          {message}
        </div>
      )}
    </div>
  );
};
```

### Suggestion Item (Inline Actions, No Modal)

**Create: services/health-dashboard/src/components/ai/SuggestionItem.tsx**

```typescript
import React, { useState } from 'react';

interface Suggestion {
  id: number;
  title: string;
  description: string;
  automation_yaml: string;
  confidence: number;
  status: string;
}

interface Props {
  suggestion: Suggestion;
  darkMode: boolean;
  onRefresh: () => void;
}

export const SuggestionItem: React.FC<Props> = ({ suggestion, darkMode, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const handleApprove = async () => {
    if (!confirm(`Deploy "${suggestion.title}" to Home Assistant?`)) return;
    
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8018/api/deploy/${suggestion.id}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert('✅ Deployed successfully!');
        onRefresh();
      } else {
        alert('❌ Deployment failed: ' + (data.detail?.summary || 'Unknown error'));
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleReject = async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8018/api/suggestions/${suggestion.id}/reject`, {
        method: 'POST'
      });
      
      if (response.ok) {
        onRefresh();
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRollback = async () => {
    const reason = prompt('Why are you rolling back this automation?');
    if (!reason) return;
    
    setLoading(true);
    try {
      // Extract automation_id from suggestion (you'd store this)
      const automationId = suggestion.title.toLowerCase().replace(/ /g, '_');
      
      const response = await fetch(`http://localhost:8018/api/deploy/${automationId}/rollback`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert('✅ Rolled back successfully!');
        onRefresh();
      } else {
        alert('❌ Rollback failed');
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Status colors
  const statusColor = {
    pending: darkMode ? 'text-yellow-300' : 'text-yellow-600',
    approved: darkMode ? 'text-green-300' : 'text-green-600',
    deployed: darkMode ? 'text-blue-300' : 'text-blue-600',
    rejected: darkMode ? 'text-red-300' : 'text-red-600',
  }[suggestion.status] || 'text-gray-500';
  
  return (
    <div className={`p-4 rounded-lg border ${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            💡 {suggestion.title}
          </h4>
          <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {suggestion.description}
          </p>
        </div>
        <span className={`text-xs font-medium ${statusColor}`}>
          {suggestion.status.toUpperCase()}
        </span>
      </div>
      
      {/* Confidence */}
      <div className={`text-xs mb-3 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        Safety Score: {Math.round(suggestion.confidence * 100)}%
      </div>
      
      {/* YAML Preview (Expandable) */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`text-sm ${darkMode ? 'text-blue-400' : 'text-blue-600'} mb-2`}
      >
        {expanded ? '▼' : '▶'} {expanded ? 'Hide' : 'Show'} YAML
      </button>
      
      {expanded && (
        <pre className={`text-xs p-3 rounded overflow-x-auto mb-3 ${
          darkMode ? 'bg-gray-900 text-gray-300' : 'bg-gray-100 text-gray-800'
        }`}>
          {suggestion.automation_yaml}
        </pre>
      )}
      
      {/* Actions (Inline) */}
      <div className="flex space-x-2">
        {suggestion.status === 'pending' && (
          <>
            <button
              onClick={handleApprove}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              ✅ Approve & Deploy
            </button>
            <button
              onClick={handleReject}
              disabled={loading}
              className={`px-4 py-2 rounded text-sm ${
                darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
              }`}
            >
              ❌ Reject
            </button>
          </>
        )}
        
        {suggestion.status === 'deployed' && (
          <button
            onClick={handleRollback}
            disabled={loading}
            className="px-4 py-2 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 disabled:opacity-50"
          >
            ⏪ Rollback
          </button>
        )}
      </div>
    </div>
  );
};
```

### Custom Hook (Reuse Existing Pattern)

**Create: services/health-dashboard/src/hooks/useSuggestions.ts**

```typescript
import { useState, useEffect } from 'react';

export function useSuggestions() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchSuggestions = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8018/api/suggestions');
      const data = await response.json();
      setSuggestions(data.suggestions || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchSuggestions();
    // Refresh every 60 seconds
    const interval = setInterval(fetchSuggestions, 60000);
    return () => clearInterval(interval);
  }, []);
  
  return { suggestions, loading, error, refresh: fetchSuggestions };
}
```

### Complete Tab Structure

**File Structure:**
```
services/health-dashboard/src/
├── components/
│   ├── tabs/
│   │   └── AIAutomationsTab.tsx    # Main tab (50 lines)
│   └── ai/
│       ├── NLInput.tsx              # NL input form (80 lines)
│       └── SuggestionItem.tsx       # Single suggestion (120 lines)
└── hooks/
    └── useSuggestions.ts            # Data fetching (30 lines)
```

**Total:** ~280 lines (vs 800+ in original complex version)

---

## Integration Verification

**IV1: Tab appears in dashboard**
- Open health-dashboard → Click "AI Automations" tab
- Verify loads without errors

**IV2: NL generation works**
- Enter request → Click Generate
- Verify automation appears in list below

**IV3: Approve workflow works**
- Click Approve → Verify deploys to HA
- Status changes to "deployed"

**IV4: Rollback works**
- Click Rollback on deployed automation
- Enter reason → Verify restores previous version

**IV5: Mobile responsive**
- Test on phone (375px width)
- Verify buttons are tappable
- Verify text readable

---

## Tasks Breakdown

1. **Add AI Automations tab to Dashboard** (0.5 hours)
2. **Create AIAutomationsTab component** (0.5 hours)
3. **Create NLInput component** (1 hour)
4. **Create SuggestionItem component** (1 hour)
5. **Create useSuggestions hook** (0.5 hours)
6. **Styling and dark mode** (0.5 hours)

**Total:** 2-3 hours

---

## Definition of Done

- [ ] AI Automations tab added to dashboard
- [ ] Single-page layout implemented
- [ ] NL input form functional
- [ ] Suggestions list displays correctly
- [ ] Inline approve/reject works
- [ ] Expandable YAML preview
- [ ] Rollback button functional
- [ ] Dark mode supported
- [ ] Mobile responsive verified
- [ ] No modals or complex navigation
- [ ] Integration test passes
- [ ] Code reviewed and approved

---

## Design Philosophy

### Simple is Better
- **No modals** - Everything inline
- **No tabs within tabs** - Single scrollable page
- **No complex filters** - Just search if needed (maybe Phase 2)
- **No separate views** - Create + suggestions on same page

### Fast Interaction
- **Click to expand YAML** - Faster than modal
- **Inline buttons** - One click to approve
- **No confirmation dialogs** - Browser confirm() is fine for MVP
- **Auto-refresh** - New suggestions appear automatically

### Mobile First
- **Vertical stack** - Works on narrow screens
- **Large touch targets** - Easy to tap on phone
- **Readable text** - No tiny fonts
- **Simple navigation** - Scroll, don't navigate

---

## Reference Files

**Copy patterns from:**
- `health-dashboard/src/components/tabs/ServicesTab.tsx` - Simple list view
- `health-dashboard/src/hooks/useHealth.ts` - Data fetching pattern
- `health-dashboard/src/components/Dashboard.tsx` - Tab structure

**Keep it simple - this isn't enterprise software!**

---

## Notes

- **Target: <300 lines of code total** (vs 800+ in complex version)
- **No separate components folder** - Just put in `components/ai/`
- **No TypeScript complexity** - Simple interfaces
- **No state management** - Just useState and fetch
- **Browser APIs OK** - confirm(), alert() for simple interactions
- Future enhancement: Add search if you have >20 suggestions
- Future enhancement: Modal for complex automations if needed

---

**Story Status:** Simplified and Ready  
**Estimated Effort:** 2-3 hours (vs 8-10 hours)  
**Created:** 2025-10-16

**Complexity Reduction:** 70% fewer lines of code, 70% less time! 🎉

