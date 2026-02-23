/**
 * AlertFilters Component
 * 
 * Filter controls for alerts (severity, service, acknowledged)
 */

import React from 'react';

interface AlertFiltersProps {
  selectedSeverity: string;
  selectedService: string;
  showAcknowledged: boolean;
  services: string[];
  onSeverityChange: (severity: string) => void;
  onServiceChange: (service: string) => void;
  onShowAcknowledgedChange: (show: boolean) => void;
  darkMode: boolean;
}

export const AlertFilters: React.FC<AlertFiltersProps> = ({
  selectedSeverity,
  selectedService,
  showAcknowledged,
  services,
  onSeverityChange,
  onServiceChange,
  onShowAcknowledgedChange,
  darkMode
}): JSX.Element => {
  const selectClass = `px-4 py-2 rounded-lg border ${
    darkMode
      ? 'bg-gray-700 border-gray-600 text-white'
      : 'bg-white border-gray-300 text-gray-900'
  }`;

  return (
    <div className="flex flex-wrap gap-4 mb-6">
      {/* Severity Filter */}
      <select
        value={selectedSeverity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className={selectClass}
        aria-label="Filter by severity"
      >
        <option value="all">All Severities</option>
        <option value="critical">Critical</option>
        <option value="error">Error</option>
        <option value="warning">Warning</option>
        <option value="info">Info</option>
      </select>

      {/* Service Filter */}
      <select
        value={selectedService}
        onChange={(e) => onServiceChange(e.target.value)}
        className={selectClass}
        aria-label="Filter by service"
      >
        <option value="all">All Services</option>
        {services.map((service) => (
          <option key={service} value={service}>
            {service}
          </option>
        ))}
      </select>

      {/* Show Acknowledged Toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showAcknowledged}
          onChange={(e) => onShowAcknowledgedChange(e.target.checked)}
          className="w-4 h-4"
        />
        <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Show Acknowledged
        </span>
      </label>
    </div>
  );
};

