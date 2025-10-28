import { apiClient } from './api'

export interface AnalyticsOverview {
  total_documents: number
  documents_by_category: Record<string, number>
  documents_by_status: Record<string, number>
  total_chunks: number
  processing_queue_size: number
  last_updated: string
}

export interface TimelineData {
  date: string
  documents_processed: number
  documents_failed: number
}

export interface CategoryDistribution {
  category: string
  count: number
  percentage: number
}

export interface ProcessingQueueStatus {
  pending: number
  processing: number
  completed: number
  failed: number
  total: number
}

export const analyticsApi = {
  // Get overview statistics
  getOverview: async (): Promise<AnalyticsOverview> => {
    const response = await apiClient.get('/analytics/overview')
    return response.data
  },

  // Get timeline data for charts
  getTimeline: async (days: number = 30): Promise<TimelineData[]> => {
    const response = await apiClient.get('/analytics/timeline', {
      params: { days }
    })
    return response.data
  },

  // Get category distribution
  getCategories: async (): Promise<CategoryDistribution[]> => {
    const response = await apiClient.get('/analytics/categories')
    return response.data
  },

  // Get processing queue status
  getQueueStatus: async (): Promise<ProcessingQueueStatus> => {
    const response = await apiClient.get('/analytics/processing-queue')
    return response.data
  },
}
