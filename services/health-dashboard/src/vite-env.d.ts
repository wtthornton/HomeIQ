/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_DATA_API_URL?: string
  readonly VITE_AI_API_URL?: string
  readonly VITE_WS_URL?: string
  readonly VITE_PORT?: string
  readonly VITE_PREVIEW_PORT?: string
  readonly VITE_BASE_URL?: string
  readonly VITE_ENABLE_DEVTOOLS?: string
  readonly VITE_LOG_LEVEL?: string
  readonly VITE_AI_AUTOMATION_UI_URL?: string
  readonly VITE_HA_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
