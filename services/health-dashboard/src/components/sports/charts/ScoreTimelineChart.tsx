/**
 * ScoreTimelineChart Component
 * 
 * Displays score progression over game time using Recharts
 * Following Context7 KB Recharts patterns
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { getChartTheme } from './ChartTheme';

interface ScoreDataPoint {
  time: string;
  homeScore: number;
  awayScore: number;
  period?: string;
}

interface ScoreTimelineChartProps {
  data: ScoreDataPoint[];
  homeTeamName: string;
  awayTeamName: string;
  darkMode?: boolean;
}

export const ScoreTimelineChart: React.FC<ScoreTimelineChartProps> = ({
  data,
  homeTeamName,
  awayTeamName,
  darkMode = false
}) => {
  const theme = getChartTheme(darkMode);

  // Custom tooltip following Context7 KB pattern
  const CustomTooltip = ({ payload, label, active }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0]?.payload;
      const period = dataPoint?.period;
      
      return (
        <div 
          className="px-4 py-3 rounded-lg shadow-lg"
          style={{
            backgroundColor: theme.tooltip.background,
            border: `1px solid ${theme.tooltip.border}`
          }}
        >
          {period && (
            <p className="font-semibold mb-1 text-xs" style={{ color: theme.tooltip.text }}>
              {period}
            </p>
          )}
          <p className="font-semibold mb-2" style={{ color: theme.tooltip.text }}>
            {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
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
        📈 Score Timeline
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
          <XAxis 
            dataKey="time"
            stroke={theme.text}
            label={{ value: 'Game Time', position: 'insideBottom', offset: -5, fill: theme.text }}
          />
          <YAxis 
            stroke={theme.text}
            label={{ value: 'Score', angle: -90, position: 'insideLeft', fill: theme.text }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: '10px' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="homeScore"
            stroke="#3B82F6"
            strokeWidth={3}
            name={homeTeamName}
            dot={{ fill: '#3B82F6', r: 5 }}
            activeDot={{ r: 8 }}
          />
          <Line
            type="monotone"
            dataKey="awayScore"
            stroke="#EF4444"
            strokeWidth={3}
            name={awayTeamName}
            dot={{ fill: '#EF4444', r: 5 }}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

