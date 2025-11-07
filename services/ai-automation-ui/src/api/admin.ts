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

const ADMIN_BASE = '/api/v1/admin'

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>
  }

  const message = await response.text()
  throw new Error(message || `Admin request failed with status ${response.status}`)
}

export async function getAdminOverview(): Promise<AdminOverview> {
  const response = await fetch(`${ADMIN_BASE}/overview`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })

  return handleResponse<AdminOverview>(response)
}

export async function getAdminConfig(): Promise<AdminConfig> {
  const response = await fetch(`${ADMIN_BASE}/config`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })

  return handleResponse<AdminConfig>(response)
}

export async function getTrainingRuns(limit = 20): Promise<TrainingRunRecord[]> {
  const response = await fetch(`${ADMIN_BASE}/training/runs?limit=${limit}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })

  return handleResponse<TrainingRunRecord[]>(response)
}

export async function triggerTrainingRun(): Promise<TrainingRunRecord> {
  const response = await fetch(`${ADMIN_BASE}/training/trigger`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })

  return handleResponse<TrainingRunRecord>(response)
}

