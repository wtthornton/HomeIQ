/**
 * ModelSelector Component
 * Reusable model dropdown for AI model selection.
 * Extracted from Settings.tsx to eliminate 4x duplication.
 */

import React from 'react';

interface ModelSelectorProps {
  value: string;
  onChange: (value: string) => void;
  darkMode: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ value, onChange, darkMode }) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    className={`px-4 py-2 rounded-lg border ${
      darkMode
        ? 'bg-gray-700 border-gray-600 text-white'
        : 'bg-white border-gray-300 text-gray-900'
    } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
  >
    <optgroup label="Latest Models (2025)">
      <option value="gpt-5.1">GPT-5.1 (Latest)</option>
      <option value="gpt-5">GPT-5</option>
      <option value="gpt-4.1">GPT-4.1</option>
    </optgroup>
    <optgroup label="GPT-4o Series">
      <option value="gpt-4o">GPT-4o</option>
      <option value="gpt-4o-mini">GPT-4o-mini</option>
    </optgroup>
    <optgroup label="GPT-4 Series">
      <option value="gpt-4-turbo">GPT-4 Turbo</option>
      <option value="gpt-4">GPT-4</option>
    </optgroup>
    <optgroup label="Reasoning Models (o-series)">
      <option value="o1">o1</option>
      <option value="o1-mini">o1-mini</option>
      <option value="o1-preview">o1-preview</option>
      <option value="o3">o3</option>
      <option value="o3-mini">o3-mini</option>
      <option value="o4-mini">o4-mini</option>
    </optgroup>
    <optgroup label="Legacy Models">
      <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
    </optgroup>
  </select>
);
