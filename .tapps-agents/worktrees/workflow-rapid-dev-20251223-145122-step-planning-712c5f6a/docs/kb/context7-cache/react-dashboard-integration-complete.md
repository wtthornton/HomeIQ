# React Dashboard Integration - Complete Pattern
**Context7 KB Cache**

**Source:** Context7 /reactjs/react.dev + Implementation Experience  
**Topic:** Dashboard UI, tab navigation, form handling, state management  
**Retrieved:** October 11, 2025  
**Applied To:** HA Ingestor Dashboard

---

## Tab Navigation Pattern

### Simple Tab State Management
```typescript
export const Dashboard: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState('overview');
  
  const tabs = [
    { id: 'overview', label: '📊 Overview', icon: '📊' },
    { id: 'services', label: '🔧 Services', icon: '🔧' },
    { id: 'configuration', label: '🔧 Configuration', icon: '🔧' }
  ];
  
  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex space-x-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setSelectedTab(tab.id)}
            className={selectedTab === tab.id ? 'active' : 'inactive'}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Tab Content */}
      {selectedTab === 'overview' && <OverviewContent />}
      {selectedTab === 'services' && <ServicesContent />}
      {selectedTab === 'configuration' && <ConfigurationContent />}
    </div>
  );
};
```

**Benefits:**
- Simple state management
- Easy to add new tabs
- Clear content separation
- Good UX

---

## Configuration Form Pattern

### Form with API Integration
```typescript
interface ConfigFormProps {
  service: string;
}

export const ConfigForm: React.FC<ConfigFormProps> = ({ service }) => {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  // Load config on mount
  useEffect(() => {
    fetch(`/api/v1/integrations/${service}/config`)
      .then(res => res.json())
      .then(data => setConfig(data.settings));
  }, [service]);
  
  // Save changes
  const handleSave = async () => {
    setLoading(true);
    try {
      await fetch(`/api/v1/integrations/${service}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: config })
      });
      setSaved(true);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form>
      {Object.entries(config).map(([key, value]) => (
        <input
          key={key}
          value={value}
          onChange={e => setConfig({...config, [key]: e.target.value})}
        />
      ))}
      <button onClick={handleSave} disabled={loading}>
        {loading ? 'Saving...' : saved ? '✓ Saved' : 'Save'}
      </button>
    </form>
  );
};
```

---

## Masked Password Input

### Show/Hide Pattern
```typescript
const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});

const isSensitive = (key: string) => 
  key.toLowerCase().includes('token') ||
  key.toLowerCase().includes('key') ||
  key.toLowerCase().includes('password');

const maskValue = (value: string) => {
  if (!value) return '';
  return '••••••••' + value.slice(-4);
};

// Render input
<div className="relative">
  <input
    type={isSensitive(key) && !showSensitive[key] ? 'password' : 'text'}
    value={isSensitive(key) && !showSensitive[key] ? maskValue(value) : value}
    onChange={e => updateValue(key, e.target.value)}
  />
  {isSensitive(key) && (
    <button onClick={() => toggleShow(key)}>
      {showSensitive[key] ? 'Hide' : 'Show'}
    </button>
  )}
</div>
```

---

## Placeholder Content Pattern

### Empty Tab Placeholder
```typescript
const PlaceholderTab: React.FC<{
  icon: string;
  title: string;
  description: string;
  tip: string;
}> = ({ icon, title, description, tip }) => (
  <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-12 text-center">
    <div className="text-6xl mb-4">{icon}</div>
    <h2 className="text-2xl font-bold mb-2">{title}</h2>
    <p className="text-gray-600 mb-6">{description}</p>
    <p className="text-sm text-gray-500">{tip}</p>
  </div>
);

// Usage
{selectedTab === 'services' && (
  <PlaceholderTab
    icon="🔧"
    title="Service Management"
    description="Individual service configuration and monitoring"
    tip="Tip: Use the Configuration tab to manage service credentials"
  />
)}
```

---

## Service Status Table

### Real-Time Status Table
```typescript
export const ServiceControl: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  
  useEffect(() => {
    const loadServices = async () => {
      const res = await fetch('/api/v1/services');
      const data = await res.json();
      setServices(data.services || []);
    };
    
    loadServices();
    const interval = setInterval(loadServices, 5000);  // Auto-refresh
    return () => clearInterval(interval);
  }, []);
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return '🟢';
      case 'stopped': return '🔴';
      case 'error': return '⚠️';
      default: return '⚪';
    }
  };
  
  return (
    <table>
      <thead>
        <tr>
          <th>Service</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {services.map(service => (
          <tr key={service.service}>
            <td>{service.service}</td>
            <td>
              {getStatusIcon(service.status)} {service.status}
            </td>
            <td>
              <button onClick={() => restart(service.service)}>
                Restart
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

---

## Dark Mode Pattern

### Theme Toggle
```typescript
const [darkMode, setDarkMode] = useState(false);

useEffect(() => {
  if (darkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}, [darkMode]);

return (
  <button onClick={() => setDarkMode(!darkMode)}>
    {darkMode ? '☀️' : '🌙'}
  </button>
);
```

### Dark Mode Classes
```typescript
className={`bg-white dark:bg-gray-800`}
className={`text-gray-900 dark:text-white`}
className={`border-gray-200 dark:border-gray-700`}
```

---

## Best Practices

### 1. Loading States
```typescript
if (loading) {
  return (
    <div className="flex justify-center py-12">
      <div className="animate-spin h-12 w-12 border-b-2 border-blue-600" />
    </div>
  );
}
```

### 2. Error States
```typescript
if (error) {
  return (
    <div className="bg-red-50 p-4 rounded">
      <p className="text-red-800">{error}</p>
    </div>
  );
}
```

### 3. Success Feedback
```typescript
const [saved, setSaved] = useState(false);

const handleSave = async () => {
  await save();
  setSaved(true);
  setTimeout(() => setSaved(false), 3000);  // Clear after 3s
};

return (
  <button>
    {saved ? '✓ Saved' : 'Save Changes'}
  </button>
);
```

### 4. Confirmation Dialogs
```typescript
const handleRestart = async () => {
  if (!confirm(`Restart ${service} service?`)) {
    return;
  }
  await restart(service);
};
```

---

## Performance Optimization

### Auto-Refresh Pattern
```typescript
useEffect(() => {
  const refresh = async () => {
    const data = await fetchData();
    setData(data);
  };
  
  refresh();  // Initial load
  const interval = setInterval(refresh, 5000);  // Every 5s
  
  return () => clearInterval(interval);  // Cleanup
}, []);
```

### Debounced Input
```typescript
const [value, setValue] = useState('');
const [debouncedValue, setDebouncedValue] = useState('');

useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedValue(value);
  }, 500);
  
  return () => clearTimeout(timer);
}, [value]);
```

---

## Common Pitfalls

### ❌ Don't: Direct State Mutation
```typescript
// Wrong
config[key] = value;
setConfig(config);

// Right
setConfig({ ...config, [key]: value });
```

### ❌ Don't: Missing Cleanup
```typescript
// Wrong
useEffect(() => {
  setInterval(fetch, 5000);
}, []);

// Right
useEffect(() => {
  const interval = setInterval(fetch, 5000);
  return () => clearInterval(interval);
}, []);
```

### ❌ Don't: Inline Object Creation
```typescript
// Wrong (creates new object every render)
<Component data={{ key: value }} />

// Right
const data = useMemo(() => ({ key: value }), [value]);
<Component data={data} />
```

---

**Saved to KB:** 2025-10-11  
**Topics:** react, dashboard, forms, state_management, tabs  
**Use Case:** Dashboard applications with configuration management  
**Complexity:** Low-Medium  
**Applied To:** HA Ingestor Dashboard v4.0

