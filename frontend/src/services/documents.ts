import { apiClient } from './api'

export interface Document {
  id: string
  filename: string
  file_path: string
  file_size: number
  mime_type: string
  classification: {
    category: string
    subcategory?: string
    confidence: number
  }
  entities: Array<{
    type: string
    value: string
    confidence: number
  }>
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
  page: number
  per_page: number
}

export interface DocumentFilters {
  category?: string
  status?: string
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  per_page?: number
}

export interface DocumentChunk {
  id: string
  content: string
  metadata: Record<string, any>
  similarity_score?: number
}

export const documentsApi = {
  // Get list of documents with filters
  getDocuments: async (filters: DocumentFilters = {}): Promise<DocumentListResponse> => {
    const response = await apiClient.get('/documents', { params: filters })
    return response.data
  },

  // Get single document by ID
  getDocument: async (id: string): Promise<Document> => {
    const response = await apiClient.get(`/documents/${id}`)
    return response.data
  },

  // Get document chunks
  getDocumentChunks: async (id: string): Promise<DocumentChunk[]> => {
    const response = await apiClient.get(`/documents/${id}/chunks`)
    return response.data
  },

  // Upload document
  uploadDocument: async (file: File): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Delete document
  deleteDocument: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}`)
  },
}
