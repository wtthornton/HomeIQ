/**
 * Synergy Visualization Charts
 * Interactive charts for synergy analysis and impact visualization
 * 
 * Phase 1: Enhanced Cards with Interactive Visualizations
 */

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { motion } from 'framer-motion';
import type { SynergyOpportunity } from '../types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
  Filler
);

interface SynergyChartProps {
  synergy: SynergyOpportunity;
  darkMode?: boolean;
}

/**
 * Impact Score Circular Gauge
 * Animated speedometer-style gauge showing impact score (0-100%)
 */
export const ImpactScoreGauge: React.FC<SynergyChartProps> = ({ synergy, darkMode = false }) => {
  const impactScore = Math.round(synergy.impact_score * 100);
  
  // Color based on score: red (<50%) → yellow (50-75%) → green (>75%)
  const getColor = (score: number) => {
    if (score < 50) return '#ef4444'; // red
    if (score < 75) return '#eab308'; // yellow
    return '#22c55e'; // green
  };

  const color = getColor(impactScore);

  // Create doughnut chart data for gauge
  const data = {
    labels: ['Impact Score', 'Remaining'],
    datasets: [{
      data: [impactScore, 100 - impactScore],
      backgroundColor: [color, darkMode ? '#374151' : '#e5e7eb'],
      borderWidth: 0,
      cutout: '75%'
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        enabled: false
      }
    },
    animation: {
      animateRotate: true,
      duration: 1500
    }
  };

  return (
    <div className="relative w-32 h-32 mx-auto">
      <Doughnut data={data} options={options} />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
            className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}
            style={{ color }}
          >
            {impactScore}%
          </motion.div>
          <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Impact
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Score Breakdown Bar Chart
 * Horizontal bar chart showing component scores
 */
export const ScoreBreakdownChart: React.FC<SynergyChartProps> = ({ synergy, darkMode = false }) => {
  // Get breakdown from explanation_breakdown or explanation.score_breakdown
  const breakdown = synergy.explanation_breakdown || 
                   synergy.explanation?.score_breakdown || 
                   {};

  if (Object.keys(breakdown).length === 0) {
    return (
      <div className={`text-center py-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        <p className="text-sm">Score breakdown not available</p>
      </div>
    );
  }

  // Convert to array and format labels
  const entries = Object.entries(breakdown)
    .map(([key, value]) => ({
      label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      value: typeof value === 'number' ? Math.round(value * 100) : 0
    }))
    .sort((a, b) => b.value - a.value);

  const data = {
    labels: entries.map(e => e.label),
    datasets: [{
      label: 'Score (%)',
      data: entries.map(e => e.value),
      backgroundColor: entries.map(e => {
        // Color gradient based on value
        if (e.value >= 80) return 'rgba(34, 197, 94, 0.8)'; // green
        if (e.value >= 60) return 'rgba(234, 179, 8, 0.8)'; // yellow
        return 'rgba(239, 68, 68, 0.8)'; // red
      }),
      borderColor: entries.map(e => {
        if (e.value >= 80) return 'rgba(34, 197, 94, 1)';
        if (e.value >= 60) return 'rgba(234, 179, 8, 1)';
        return 'rgba(239, 68, 68, 1)';
      }),
      borderWidth: 2,
    }]
  };

  const options = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            return `${context.parsed.x}%`;
          }
        },
        backgroundColor: darkMode ? '#1f2937' : '#ffffff',
        titleColor: darkMode ? '#f3f4f6' : '#111827',
        bodyColor: darkMode ? '#d1d5db' : '#374151',
        borderColor: darkMode ? '#374151' : '#e5e7eb',
        borderWidth: 1
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        max: 100,
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280',
          callback: (value: any) => `${value}%`
        },
        grid: {
          color: darkMode ? '#374151' : '#e5e7eb'
        }
      },
      y: {
        ticks: {
          color: darkMode ? '#9ca3af' : '#6b7280'
        },
        grid: {
          display: false
        }
      }
    }
  };

  return (
    <div className="h-64">
      <Bar data={data} options={options} />
    </div>
  );
};

/**
 * Synergy Timeline Visualization
 * Mini timeline showing usage patterns (if available)
 */
export const SynergyTimeline: React.FC<SynergyChartProps & { timelineData?: any[] }> = ({ 
  darkMode = false,
  timelineData 
}) => {
  // If no timeline data, show placeholder
  if (!timelineData || timelineData.length === 0) {
    return (
      <div className={`text-center py-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        <p className="text-sm">Timeline data not available</p>
      </div>
    );
  }

  // Timeline visualization would go here
  // For now, return placeholder
  return (
    <div className={`text-center py-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
      <p className="text-sm">Timeline visualization coming soon</p>
    </div>
  );
};

