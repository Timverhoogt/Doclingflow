import { apiClient } from './api'

export interface AppSettings {
  llm_provider: string
  llm_model: string
  llm_api_key: string
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  classification_categories: string[]
  watch_folders: string[]
  processing_batch_size: number
  max_file_size: number
  supported_formats: string[]
}

export interface WatchFolder {
  path: string
  enabled: boolean
  recursive: boolean
  file_patterns: string[]
}

export interface ProcessingJob {
  id: string
  document_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error_message?: string
  created_at: string
  updated_at: string
}

export const settingsApi = {
  // Get current settings
  getSettings: async (): Promise<AppSettings> => {
    const response = await apiClient.get('/settings')
    return response.data
  },

  // Update settings
  updateSettings: async (settings: Partial<AppSettings>): Promise<AppSettings> => {
    const response = await apiClient.patch('/settings', settings)
    return response.data
  },

  // Get watch folders
  getWatchFolders: async (): Promise<WatchFolder[]> => {
    const response = await apiClient.get('/settings/watch-folders')
    return response.data
  },

  // Add watch folder
  addWatchFolder: async (folder: Omit<WatchFolder, 'path'> & { path: string }): Promise<WatchFolder> => {
    const response = await apiClient.post('/settings/watch-folders', folder)
    return response.data
  },

  // Remove watch folder
  removeWatchFolder: async (path: string): Promise<void> => {
    await apiClient.delete(`/settings/watch-folders/${encodeURIComponent(path)}`)
  },
}

export const jobsApi = {
  // Get processing jobs
  getJobs: async (status?: string, limit?: number): Promise<ProcessingJob[]> => {
    const response = await apiClient.get('/jobs', {
      params: { status, limit }
    })
    return response.data
  },

  // Get single job
  getJob: async (id: string): Promise<ProcessingJob> => {
    const response = await apiClient.get(`/jobs/${id}`)
    return response.data
  },

  // Retry failed job
  retryJob: async (id: string): Promise<ProcessingJob> => {
    const response = await apiClient.post(`/jobs/${id}/retry`)
    return response.data
  },

  // Cancel job
  cancelJob: async (id: string): Promise<void> => {
    await apiClient.delete(`/jobs/${id}`)
  },
}
