/**
 * AgentEvaluationTab — Main container for Agent Evaluation dashboard section
 * E4.S4: Agent selector, Summary Matrix, Trend Charts, Alerts, Session Viewer
 */

import React, { useState, useEffect, useCallback } from 'react';
import { EvalAlertBanner, type EvalAlertData } from './EvalAlertBanner';
import { SummaryMatrix, type MetricScore } from './SummaryMatrix';
import { ScoreTrendChart, type TrendData } from './ScoreTrendChart';
import { SessionTraceViewer, type SessionTraceData } from './SessionTraceViewer';

interface AgentInfo {
  agent_name: string;
  last_run: string | null;
  sessions_evaluated: number;
  total_evaluations: number;
  alerts_triggered: number;
  aggregate_scores: Record<string, number>;
}

interface AgentEvaluationTabProps {
  darkMode: boolean;
}

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, {
      headers: { 'X-API-Key': localStorage.getItem('apiKey') || '' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export const AgentEvaluationTab: React.FC<AgentEvaluationTabProps> = ({ darkMode }) => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [scores, setScores] = useState<MetricScore[]>([]);
  const [trends, setTrends] = useState<TrendData>({});
  const [alerts, setAlerts] = useState<EvalAlertData[]>([]);
  const [period, setPeriod] = useState('7d');
  const [selectedTrace, setSelectedTrace] = useState<SessionTraceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  // Load agents list
  useEffect(() => {
    (async () => {
      setLoading(true);
      const data = await fetchJson<{ agents: AgentInfo[] }>(`${API_BASE}/evaluations`);
      if (data?.agents) {
        setAgents(data.agents);
        if (data.agents.length > 0 && !selectedAgent) {
          setSelectedAgent(data.agents[0].agent_name);
        }
      }
      setLoading(false);
    })();
  }, []);

  // Load agent-specific data when selection changes
  const loadAgentData = useCallback(async (agent: string, p: string) => {
    if (!agent) return;

    const [scoresData, trendsData, alertsData] = await Promise.all([
      fetchJson<{ scores: MetricScore[] }>(`${API_BASE}/evaluations/${agent}/history?page_size=200`),
      fetchJson<{ trends: TrendData }>(`${API_BASE}/evaluations/${agent}/trends?period=${p}`),
      fetchJson<{ alerts: EvalAlertData[] }>(`${API_BASE}/evaluations/${agent}/alerts`),
    ]);

    if (scoresData?.scores) setScores(scoresData.scores);
    else setScores([]);

    if (trendsData?.trends) setTrends(trendsData.trends);
    else setTrends({});

    if (alertsData?.alerts) setAlerts(alertsData.alerts);
    else setAlerts([]);
  }, []);

  useEffect(() => {
    loadAgentData(selectedAgent, period);
  }, [selectedAgent, period, loadAgentData]);

  const handleTrigger = async () => {
    if (!selectedAgent || triggering) return;
    setTriggering(true);
    try {
      await fetch(`${API_BASE}/evaluations/${selectedAgent}/trigger`, {
        method: 'POST',
        headers: { 'X-API-Key': localStorage.getItem('apiKey') || '' },
      });
      // Reload data after trigger
      await loadAgentData(selectedAgent, period);
    } finally {
      setTriggering(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    await fetch(`${API_BASE}/evaluations/${selectedAgent}/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': localStorage.getItem('apiKey') || '',
      },
      body: JSON.stringify({ by: 'dashboard-user', note: '' }),
    });
    await loadAgentData(selectedAgent, period);
  };

  // Derive thresholds from the selected agent's info
  const currentAgent = agents.find(a => a.agent_name === selectedAgent);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Loading evaluation data...
        </div>
      </div>
    );
  }

  if (!loading && agents.length === 0) {
    return (
      <div className={`rounded-lg border p-12 text-center ${
        darkMode ? 'border-gray-700 bg-gray-800/30' : 'border-gray-200 bg-white'
      }`}>
        <div className="text-6xl mb-4">🔍</div>
        <h3 className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          No Agent Evaluations
        </h3>
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No agents have been evaluated yet. Agent evaluations will appear here once the evaluation scheduler runs.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with agent selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Agent Evaluation
          </h2>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            5-level evaluation pyramid scores and trends
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Agent selector */}
          <select
            value={selectedAgent}
            onChange={e => setSelectedAgent(e.target.value)}
            className={`px-3 py-2 rounded-lg border text-sm ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            }`}
            aria-label="Select agent"
          >
            {agents.map(a => (
              <option key={a.agent_name} value={a.agent_name}>
                {a.agent_name}
              </option>
            ))}
          </select>

          {/* Manual trigger */}
          <button
            onClick={handleTrigger}
            disabled={triggering || !selectedAgent}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              triggering
                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {triggering ? 'Running...' : 'Run Evaluation'}
          </button>
        </div>
      </div>

      {/* Last run info */}
      {currentAgent?.last_run && (
        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          Last evaluation: {new Date(currentAgent.last_run).toLocaleString()}
          {' \u00b7 '}
          {currentAgent.sessions_evaluated} sessions
          {' \u00b7 '}
          {currentAgent.total_evaluations} evaluations
        </div>
      )}

      {/* Alert banner */}
      <EvalAlertBanner
        alerts={alerts}
        onAcknowledge={handleAcknowledge}
        darkMode={darkMode}
      />

      {/* Summary Matrix */}
      <div className={`rounded-lg border p-4 ${
        darkMode ? 'border-gray-700 bg-gray-800/30' : 'border-gray-200 bg-white'
      }`}>
        <h3 className={`text-sm font-semibold mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Summary Matrix
        </h3>
        <SummaryMatrix
          scores={scores}
          darkMode={darkMode}
        />
      </div>

      {/* Trend Charts */}
      <div className={`rounded-lg border p-4 ${
        darkMode ? 'border-gray-700 bg-gray-800/30' : 'border-gray-200 bg-white'
      }`}>
        <h3 className={`text-sm font-semibold mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Score Trends
        </h3>
        <ScoreTrendChart
          trends={trends}
          period={period}
          onPeriodChange={setPeriod}
          darkMode={darkMode}
        />
      </div>

      {/* Session Trace Viewer */}
      <div className={`rounded-lg border p-4 ${
        darkMode ? 'border-gray-700 bg-gray-800/30' : 'border-gray-200 bg-white'
      }`}>
        <h3 className={`text-sm font-semibold mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Session Trace
        </h3>
        <SessionTraceViewer
          trace={selectedTrace}
          onClose={() => setSelectedTrace(null)}
          darkMode={darkMode}
        />
      </div>
    </div>
  );
};
