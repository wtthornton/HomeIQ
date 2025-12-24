/**
 * Export Utilities
 * Functions for exporting data to CSV and JSON formats
 */

import type { Pattern } from '../types';

/**
 * Convert patterns to CSV format
 */
export function patternsToCSV(patterns: Pattern[], deviceNames: Record<string, string>): string {
  const headers = [
    'Pattern Type',
    'Device ID',
    'Device Name',
    'Confidence',
    'Occurrences',
    'First Detected',
    'Last Detected',
    'Metadata'
  ];

  const rows = patterns.map(pattern => {
    const deviceName = deviceNames[pattern.device_id] || pattern.device_id;
    const metadata = pattern.pattern_metadata ? JSON.stringify(pattern.pattern_metadata) : '';
    
    return [
      pattern.pattern_type || '',
      pattern.device_id || '',
      deviceName,
      (pattern.confidence || 0).toString(),
      (pattern.occurrences || 0).toString(),
      pattern.created_at || '',
      pattern.created_at || '', // Use created_at for both since Pattern type doesn't have last_detected
      metadata
    ];
  });

  // Escape CSV values (handle commas, quotes, newlines)
  const escapeCSV = (value: string): string => {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  };

  const csvRows = [
    headers.map(escapeCSV).join(','),
    ...rows.map(row => row.map(escapeCSV).join(','))
  ];

  return csvRows.join('\n');
}

/**
 * Convert patterns to JSON format
 */
export function patternsToJSON(patterns: Pattern[], deviceNames: Record<string, string>): string {
  const data = patterns.map(pattern => ({
    ...pattern,
    device_name: deviceNames[pattern.device_id] || pattern.device_id,
  }));

  return JSON.stringify(data, null, 2);
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
 * Export patterns to CSV file
 */
export function exportPatternsToCSV(
  patterns: Pattern[],
  deviceNames: Record<string, string>,
  filename?: string
): void {
  const csv = patternsToCSV(patterns, deviceNames);
  const timestamp = new Date().toISOString().split('T')[0];
  const defaultFilename = `patterns_export_${timestamp}.csv`;
  downloadFile(csv, filename || defaultFilename, 'text/csv');
}

/**
 * Export patterns to JSON file
 */
export function exportPatternsToJSON(
  patterns: Pattern[],
  deviceNames: Record<string, string>,
  filename?: string
): void {
  const json = patternsToJSON(patterns, deviceNames);
  const timestamp = new Date().toISOString().split('T')[0];
  const defaultFilename = `patterns_export_${timestamp}.json`;
  downloadFile(json, filename || defaultFilename, 'application/json');
}

