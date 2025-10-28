'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout } from '@/components/Layout/Layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import { Modal } from '@/components/ui/Modal'
import { UploadModal } from '@/components/Documents/UploadModal'
import { documentsApi, Document, DocumentFilters } from '@/services/documents'
import { formatDate, formatFileSize } from '@/lib/utils'
import { Upload, Search, Filter, Eye, Download, Trash2, RefreshCw } from 'lucide-react'

export default function DocumentsPage() {
  const [filters, setFilters] = useState<DocumentFilters>({
    page: 1,
    per_page: 20,
  })
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const { data: documents, isLoading, refetch } = useQuery({
    queryKey: ['documents', filters],
    queryFn: () => documentsApi.getDocuments(filters),
    refetchInterval: 30000,
  })

  const handleSearch = () => {
    setFilters(prev => ({ ...prev, search: searchQuery, page: 1 }))
  }

  const handleFilterChange = (key: keyof DocumentFilters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value || undefined, page: 1 }))
  }

  const getStatusBadge = (status: Document['processing_status']) => {
    const variants = {
      pending: { variant: 'warning' as const, label: 'Pending' },
      processing: { variant: 'secondary' as const, label: 'Processing' },
      completed: { variant: 'success' as const, label: 'Completed' },
      failed: { variant: 'error' as const, label: 'Failed' },
    }
    const config = variants[status]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const categoryOptions = [
    { value: '', label: 'All Categories' },
    { value: 'Safety', label: 'Safety' },
    { value: 'Technical', label: 'Technical' },
    { value: 'Business', label: 'Business' },
    { value: 'Equipment', label: 'Equipment' },
    { value: 'Regulatory', label: 'Regulatory' },
    { value: 'Operational', label: 'Operational' },
  ]

  const statusOptions = [
    { value: '', label: 'All Status' },
    { value: 'pending', label: 'Pending' },
    { value: 'processing', label: 'Processing' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
  ]

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
            <p className="text-gray-600">Manage and view your processed documents</p>
          </div>
          <Button onClick={() => setShowUploadModal(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Document
          </Button>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-2">
                <div className="flex gap-2">
                  <Input
                    placeholder="Search documents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                  <Button onClick={handleSearch}>
                    <Search className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Select
                options={categoryOptions}
                placeholder="Select category"
                value={filters.category || ''}
                onChange={(e) => handleFilterChange('category', e.target.value)}
              />
              <Select
                options={statusOptions}
                placeholder="Select status"
                value={filters.status || ''}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                Documents ({documents?.total || 0})
              </CardTitle>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents?.documents?.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-blue-100 rounded-lg">
                            <Eye className="h-4 w-4 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{doc.filename}</p>
                            <p className="text-sm text-gray-500">{doc.mime_type}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {doc.classification?.category || 'Unknown'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(doc.processing_status)}
                      </TableCell>
                      <TableCell>
                        {formatFileSize(doc.file_size)}
                      </TableCell>
                      <TableCell>
                        {formatDate(doc.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Upload Modal */}
        <UploadModal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            setShowUploadModal(false)
            refetch()
          }}
        />
      </div>
    </Layout>
  )
}
