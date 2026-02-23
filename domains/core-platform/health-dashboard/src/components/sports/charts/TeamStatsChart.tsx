/**
 * TeamStatsChart Component
 * 
 * Horizontal bar chart comparing team statistics
 * Following Context7 KB Recharts patterns for bar charts
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { getChartTheme } from './ChartTheme';
import type { GameStats } from '../../../types/sports';

interface TeamStatsChartProps {
  stats: GameStats;
  homeTeamName: string;
  awayTeamName: string;
  darkMode?: boolean;
}

export const TeamStatsChart: React.FC<TeamStatsChartProps> = ({
  stats,
  homeTeamName,
  awayTeamName,
  darkMode = false
}) => {
  const theme = getChartTheme(darkMode);

  // Transform stats into chart data
  const chartData = Object.entries(stats).map(([category, values]) => ({
    category,
    [homeTeamName]: values.home,
    [awayTeamName]: values.away
  }));

  // Custom tooltip
  const CustomTooltip = ({ payload, label, active }: any) => {
    if (active && payload && payload.length) {
      return (
        <div 
          className="px-4 py-3 rounded-lg shadow-lg"
          style={{
            backgroundColor: theme.tooltip.background,
            border: `1px solid ${theme.tooltip.border}`
          }}
        >
          <p className="font-semibold mb-2" style={{ color: theme.tooltip.text }}>
            {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.fill }} className="text-sm font-medium">
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg`}>
      <h3 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        📊 Team Stats Comparison
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={chartData}
          layout="horizontal"
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis 
            type="number"
            stroke={theme.text}
          />
          <YAxis 
            type="category"
            dataKey="category"
            stroke={theme.text}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          <Bar 
            dataKey={homeTeamName}
            fill="#3B82F6"
            radius={[0, 4, 4, 0]}
          />
          <Bar 
            dataKey={awayTeamName}
            fill="#EF4444"
            radius={[0, 4, 4, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

