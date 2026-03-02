import { fetchJSON } from '../lib/api-client';

export interface AdminOverview {
  totalSuggestions: number
  activeAutomations: number
  systemStatus: string
  apiStatus: string
  softPromptEnabled: boolean
  softPromptLoaded: boolean
  softPromptModelId: string | null
  guardrailEnabled: boolean
  guardrailLoaded: boolean
  guardrailModelName: string | null
  updatedAt: string
}

export interface AdminConfig {
  dataApiUrl: string
  databasePath: string
  logLevel: string
  openaiModel: string
  softPromptModelDir: string
  guardrailModelName: string
}

export interface TrainingRunRecord {
  id: number
  trainingType?: string
  status: string
  startedAt: string
  finishedAt: string | null
  datasetSize: number | null
  baseModel: string | null
  outputDir: string | null
  runIdentifier: string | null
  finalLoss: number | null
  errorMessage: string | null
  metadataPath: string | null
  triggeredBy: string
}

export interface GNNTrainingStatus {
  hasActiveRun: boolean
  activeRun: TrainingRunRecord | null
  modelExists: boolean
  modelPath: string
  modelInfo: Record<string, any>
}

const ADMIN_BASE = '/api/v1/admin'

export async function getAdminOverview(): Promise<AdminOverview> {
  return fetchJSON<AdminOverview>(`${ADMIN_BASE}/overview`)
}

export async function getAdminConfig(): Promise<AdminConfig> {
  return fetchJSON<AdminConfig>(`${ADMIN_BASE}/config`)
}

export async function getTrainingRuns(limit = 20): Promise<TrainingRunRecord[]> {
  return fetchJSON<TrainingRunRecord[]>(`${ADMIN_BASE}/training/runs?limit=${limit}`)
}

export async function triggerTrainingRun(): Promise<TrainingRunRecord> {
  return fetchJSON<TrainingRunRecord>(`${ADMIN_BASE}/training/trigger`, { method: 'POST' })
}

export async function getGNNTrainingRuns(limit = 20): Promise<TrainingRunRecord[]> {
  return fetchJSON<TrainingRunRecord[]>(`${ADMIN_BASE}/training/gnn/runs?limit=${limit}`)
}

export async function triggerGNNTrainingRun(epochs?: number, force = false): Promise<TrainingRunRecord> {
  const params = new URLSearchParams()
  if (epochs) params.append('epochs', epochs.toString())
  if (force) params.append('force', 'true')
  return fetchJSON<TrainingRunRecord>(`${ADMIN_BASE}/training/gnn/trigger?${params.toString()}`, { method: 'POST' })
}

export async function getGNNTrainingStatus(): Promise<GNNTrainingStatus> {
  return fetchJSON<GNNTrainingStatus>(`${ADMIN_BASE}/training/gnn/status`)
}

export async function deleteTrainingRun(runId: number): Promise<void> {
  return fetchJSON<void>(`${ADMIN_BASE}/training/runs/${runId}`, { method: 'DELETE' })
}

export interface ClearOldRunsResponse {
  deleted_count: number
  message: string
}

export async function clearOldTrainingRuns(
  trainingType?: string,
  olderThanDays = 30,
  keepRecent = 10
): Promise<ClearOldRunsResponse> {
  const params = new URLSearchParams()
  if (trainingType) params.append('training_type', trainingType)
  params.append('older_than_days', olderThanDays.toString())
  params.append('keep_recent', keepRecent.toString())
  return fetchJSON<ClearOldRunsResponse>(`${ADMIN_BASE}/training/runs?${params.toString()}`, { method: 'DELETE' })
}

