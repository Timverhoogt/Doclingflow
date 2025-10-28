import { apiClient } from './api'

export interface SearchQuery {
  query: string
  filters?: {
    category?: string
    date_from?: string
    date_to?: string
    document_ids?: string[]
  }
  limit?: number
  offset?: number
}

export interface SearchResult {
  id: string
  content: string
  metadata: {
    document_id: string
    document_title: string
    category: string
    chunk_index: number
    [key: string]: any
  }
  similarity_score: number
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
  filters_applied: Record<string, any>
}

export interface SearchFilters {
  categories: string[]
  date_range: {
    min: string
    max: string
  }
  document_count: number
}

export const searchApi = {
  // Semantic search using vector similarity
  semanticSearch: async (query: SearchQuery): Promise<SearchResponse> => {
    const response = await apiClient.post('/search/semantic', query)
    return response.data
  },

  // Hybrid search combining vector and keyword search
  hybridSearch: async (query: SearchQuery): Promise<SearchResponse> => {
    const response = await apiClient.post('/search/hybrid', query)
    return response.data
  },

  // Get available search filters
  getFilters: async (): Promise<SearchFilters> => {
    const response = await apiClient.get('/search/filters')
    return response.data
  },
}
