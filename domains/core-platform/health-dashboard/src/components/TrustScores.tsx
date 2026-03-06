import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { 
  useTrustScores, 
  getTrustLevel, 
  TrustScore 
} from '../hooks/useTrustScore';
import { SkeletonCard } from './skeletons';

interface TrustScoreRowProps {
  score: TrustScore;
  darkMode: boolean;
}

const TrustScoreRow: React.FC<TrustScoreRowProps> = ({ score, darkMode }) => {
  const level = getTrustLevel(score.trust_score);
  const percentage = Math.round(score.trust_score * 100);
  
  const getVariant = () => {
    if (score.trust_score >= 0.8) return 'success';
    if (score.trust_score >= 0.4) return 'warning';
    return 'destructive';
  };
  
  return (
    <div className="flex items-center gap-4">
      <span className={`w-24 text-sm font-medium capitalize ${
        darkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>
        {score.domain}
      </span>
      <div className="flex-1">
        <Progress 
          value={percentage} 
          variant={getVariant()}
          size="lg"
        />
      </div>
      <div className={`w-16 text-right text-sm font-semibold ${level.textColor}`}>
        {percentage}%
      </div>
    </div>
  );
};

interface TrustScoreWidgetProps {
  darkMode: boolean;
}

export const TrustScoreWidget: React.FC<TrustScoreWidgetProps> = ({ darkMode }) => {
  const { scores, loading, error, refresh } = useTrustScores();

  if (loading && scores.length === 0) {
    return <SkeletonCard variant="default" />;
  }

  return (
    <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className={darkMode ? 'text-gray-300' : ''}>
          🤝 Domain Trust Scores
        </CardTitle>
        <button
          onClick={refresh}
          className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
            darkMode 
              ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' 
              : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
          }`}
        >
          Refresh
        </button>
      </CardHeader>
      <CardContent>
        {error && (
          <div className={`mb-4 p-3 rounded text-sm ${
            darkMode 
              ? 'bg-red-900/20 border border-red-700 text-red-300' 
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}>
            {error}
          </div>
        )}
        
        {scores.length > 0 ? (
          <div className="space-y-4">
            {scores.map(score => (
              <TrustScoreRow 
                key={score.domain} 
                score={score} 
                darkMode={darkMode} 
              />
            ))}
          </div>
        ) : (
          <p className={`text-center py-4 text-sm ${
            darkMode ? 'text-gray-400' : 'text-gray-500'
          }`}>
            No trust scores available yet. Trust scores build as you approve or reject automations.
          </p>
        )}
        
        <div className={`mt-6 pt-4 border-t text-sm ${
          darkMode ? 'border-gray-700 text-gray-400' : 'border-gray-200 text-gray-500'
        }`}>
          <p className="font-medium mb-2">Trust levels determine approval flow:</p>
          <ul className="space-y-1 ml-4">
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span><strong className="text-green-500">High (≥80%)</strong>: Streamlined one-click approval</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span><strong className="text-yellow-500">Medium (40-79%)</strong>: Standard approval with explanation</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span><strong className="text-red-500">Low (&lt;40%)</strong>: Extra confirmation step required</span>
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};

interface TrustScoreStatsProps {
  scores: TrustScore[];
  darkMode: boolean;
}

export const TrustScoreStats: React.FC<TrustScoreStatsProps> = ({ scores, darkMode }) => {
  const totalInteractions = scores.reduce((sum, s) => sum + s.total_interactions, 0);
  const totalApprovals = scores.reduce((sum, s) => sum + s.approvals, 0);
  const totalRejections = scores.reduce((sum, s) => sum + s.rejections, 0);
  const totalOverrides = scores.reduce((sum, s) => sum + s.overrides, 0);
  
  const avgTrustScore = scores.length > 0
    ? scores.reduce((sum, s) => sum + s.trust_score, 0) / scores.length
    : 0;

  const statItems = [
    { label: 'Avg Trust', value: `${Math.round(avgTrustScore * 100)}%`, icon: '🎯' },
    { label: 'Total Interactions', value: totalInteractions.toString(), icon: '📊' },
    { label: 'Approvals', value: totalApprovals.toString(), icon: '✅' },
    { label: 'Rejections', value: totalRejections.toString(), icon: '❌' },
    { label: 'Overrides', value: totalOverrides.toString(), icon: '⚠️' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {statItems.map(({ label, value, icon }) => (
        <div
          key={label}
          className={`p-3 rounded-lg ${
            darkMode ? 'bg-gray-700/50' : 'bg-gray-50'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{icon}</span>
            <span className={`text-xs font-medium ${
              darkMode ? 'text-gray-400' : 'text-gray-500'
            }`}>
              {label}
            </span>
          </div>
          <span className={`text-xl font-bold ${
            darkMode ? 'text-white' : 'text-gray-900'
          }`}>
            {value}
          </span>
        </div>
      ))}
    </div>
  );
};

export { useTrustScores, useTrustScore, getTrustLevel } from '../hooks/useTrustScore';
