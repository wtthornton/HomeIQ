# React Dashboard UI/UX Patterns
**Context7 KB Cache**

**Libraries:** React Chart.js 2, Tailwind CSS, React Icons  
**Topic:** Dashboard design, data visualization, responsive layouts  
**Retrieved:** October 10, 2025

---

## Chart.js with React

**Library:** /reactchartjs/react-chartjs-2 (Trust Score: 7.5, 70 snippets)

### Basic Chart Usage

```jsx
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  BarElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register components
ChartJS.register(
  LineElement,
  PointElement,
  BarElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend
);

// Line Chart
<Line
  data={{
    labels: ['Jan', 'Feb', 'Mar'],
    datasets: [{
      label: 'Dataset 1',
      data: [65, 59, 80],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  }}
  options={{
    responsive: true,
    maintainAspectRatio: false
  }}
/>

// Bar Chart
<Bar
  data={chartData}
  options={{ maintainAspectRatio: false }}
  height={300}
/>
```

### Real-Time Data Updates

```jsx
const [chartData, setChartData] = useState({
  labels: [],
  datasets: []
});

useEffect(() => {
  // Update chart data when new data arrives
  setChartData({
    labels: newLabels,
    datasets: [{
      data: newData,
      backgroundColor: 'rgba(75, 192, 192, 0.2)'
    }]
  });
}, [newData]);
```

### Click Events

```jsx
import { useRef } from 'react';
import { Bar, getElementAtEvent } from 'react-chartjs-2';

function ChartWithClick() {
  const chartRef = useRef();
  
  const onClick = (event) => {
    const element = getElementAtEvent(chartRef.current, event);
    console.log('Clicked element:', element);
  };
  
  return <Bar ref={chartRef} data={data} onClick={onClick} />;
}
```

---

## Tailwind CSS Responsive Layouts

**Library:** /websites/tailwindcss (Trust Score: 7.5, 1,615 snippets)

### Responsive Grid Layouts

```html
<!-- Mobile-first responsive grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  <!-- Adapts from 1 to 4 columns based on screen size -->
</div>

<!-- Dashboard grid pattern -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {cards.map(card => <Card key={card.id} {...card} />)}
</div>
```

### Responsive Cards

```html
<!-- Card component with responsive padding -->
<div class="bg-white rounded-lg shadow-md p-4 sm:p-6 lg:p-8">
  <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between">
    <div>
      <h3 class="text-lg sm:text-xl font-semibold">Title</h3>
      <p class="text-sm text-gray-600 mt-1">Description</p>
    </div>
    <div class="mt-4 sm:mt-0">
      <span class="text-2xl sm:text-3xl font-bold">Value</span>
    </div>
  </div>
</div>
```

### Responsive Typography

```html
<h1 class="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold">
  Responsive heading
</h1>
<p class="text-sm sm:text-base lg:text-lg">
  Responsive text
</p>
```

### Responsive Spacing

```html
<!-- Padding scales with screen size -->
<div class="px-4 sm:px-6 lg:px-8">
  <div class="py-4 sm:py-6 lg:py-8">
    Content
  </div>
</div>
```

---

## React Icons

**Library:** /react-icons/react-icons (Trust Score: 7.2, 38 snippets)

### Basic Usage

```jsx
import { FaBeer, FaHome, FaCloud } from 'react-icons/fa';
import { MdSettings, MdDashboard } from 'react-icons/md';
import { BsLightningFill } from 'react-icons/bs';
import { AiOutlineThunderbolt } from 'react-icons/ai';

function IconExample() {
  return (
    <div>
      <FaBeer className="text-2xl text-blue-600" />
      <FaHome size={24} color="#333" />
      <MdDashboard style={{ fontSize: '32px', color: '#667eea' }} />
    </div>
  );
}
```

### Icon Libraries Available

```jsx
import { FaIcon } from 'react-icons/fa';  // Font Awesome
import { MdIcon } from 'react-icons/md';  // Material Design
import { AiIcon } from 'react-icons/ai';  // Ant Design
import { BiIcon } from 'react-icons/bi';  // BoxIcons
import { BsIcon } from 'react-icons/bs';  // Bootstrap
import { GoIcon } from 'react-icons/go';  // GitHub Octicons
import { IoIcon } from 'react-icons/io5'; // Ionicons
import { TiIcon } from 'react-icons/ti';  // Typicons
```

---

## Dashboard UI Best Practices

### Card Component Pattern

```jsx
const MetricCard = ({ title, value, icon: Icon, change, status }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600 mb-1">{title}</p>
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        {change && (
          <p className={`text-sm mt-2 ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
          </p>
        )}
      </div>
      <div className={`p-3 rounded-full ${
        status === 'healthy' ? 'bg-green-100' : 'bg-red-100'
      }`}>
        <Icon className={`text-2xl ${
          status === 'healthy' ? 'text-green-600' : 'text-red-600'
        }`} />
      </div>
    </div>
  </div>
);
```

### Status Badge Pattern

```jsx
const StatusBadge = ({ status }) => {
  const colors = {
    healthy: 'bg-green-100 text-green-800',
    degraded: 'bg-yellow-100 text-yellow-800',
    unhealthy: 'bg-red-100 text-red-800'
  };
  
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status]}`}>
      {status}
    </span>
  );
};
```

### Responsive Dashboard Grid

```jsx
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  {/* Header */}
  <div className="mb-8">
    <h1 className="text-3xl font-bold">Dashboard</h1>
  </div>
  
  {/* Metrics Grid */}
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    {metrics.map(metric => <MetricCard key={metric.id} {...metric} />)}
  </div>
  
  {/* Charts Section */}
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div className="bg-white rounded-lg shadow p-6">
      <Line data={chartData} options={chartOptions} />
    </div>
  </div>
</div>
```

---

**Source:** Context7 research  
**Applied To:** HA Ingestor Dashboard enhancement  
**Cached:** 2025-10-10

