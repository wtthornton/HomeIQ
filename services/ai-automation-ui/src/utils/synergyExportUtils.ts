/**
 * Synergy Export Utilities
 * Functions for exporting synergies to CSV and JSON formats
 */

import type { SynergyOpportunity } from '../types';

/**
 * Convert synergies to CSV format
 */
export function synergiesToCSV(synergies: SynergyOpportunity[]): string {
  const headers = [
    'Synergy ID',
    'Synergy Type',
    'Device IDs',
    'Area',
    'Impact Score',
    'Confidence',
    'Complexity',
    'Validated by Patterns',
    'Pattern Support Score',
    'Created At',
    'Trigger Entity',
    'Trigger Name',
    'Action Entity',
    'Action Name',
    'Rationale',
    'Estimated Savings'
  ];

  const rows = synergies.map(synergy => {
    const deviceIds = typeof synergy.device_ids === 'string' 
      ? synergy.device_ids 
      : JSON.stringify(synergy.device_ids);
    
    return [
      synergy.synergy_id || synergy.id.toString(),
      synergy.synergy_type || '',
      deviceIds,
      synergy.area || '',
      (synergy.impact_score || 0).toString(),
      (synergy.confidence || 0).toString(),
      synergy.complexity || '',
      (synergy.validated_by_patterns || false).toString(),
      (synergy.pattern_support_score || 0).toString(),
      synergy.created_at || '',
      synergy.opportunity_metadata?.trigger_entity || '',
      synergy.opportunity_metadata?.trigger_name || '',
      synergy.opportunity_metadata?.action_entity || '',
      synergy.opportunity_metadata?.action_name || '',
      synergy.opportunity_metadata?.rationale || synergy.rationale || '',
      synergy.opportunity_metadata?.estimated_savings || ''
    ];
  });

  // Escape CSV values (handle commas, quotes, newlines)
  const escapeCSV = (value: string): string => {
    const stringValue = String(value);
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  };

  const csvRows = [
    headers.map(escapeCSV).join(','),
    ...rows.map(row => row.map(escapeCSV).join(','))
  ];

  return csvRows.join('\n');
}

/**
 * Convert synergies to JSON format
 */
export function synergiesToJSON(synergies: SynergyOpportunity[]): string {
  return JSON.stringify(synergies, null, 2);
}

/**
 * Download data as file
 */
export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export synergies to CSV file
 */
export function exportSynergiesToCSV(
  synergies: SynergyOpportunity[],
  filename?: string
): void {
  const csv = synergiesToCSV(synergies);
  const timestamp = new Date().toISOString().split('T')[0];
  const defaultFilename = `synergies_export_${timestamp}.csv`;
  downloadFile(csv, filename || defaultFilename, 'text/csv');
}

/**
 * Export synergies to JSON file
 */
export function exportSynergiesToJSON(
  synergies: SynergyOpportunity[],
  filename?: string
): void {
  const json = synergiesToJSON(synergies);
  const timestamp = new Date().toISOString().split('T')[0];
  const defaultFilename = `synergies_export_${timestamp}.json`;
  downloadFile(json, filename || defaultFilename, 'application/json');
}



