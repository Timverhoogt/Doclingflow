'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout } from '@/components/Layout/Layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { searchApi, SearchQuery, SearchResult } from '@/services/search'
import { formatDate } from '@/lib/utils'
import { Search, Filter, FileText, ExternalLink } from 'lucide-react'

export default function SearchPage() {
  const [searchQuery, setSearchQuery] = useState<SearchQuery>({
    query: '',
    limit: 20,
    offset: 0,
  })
  const [searchType, setSearchType] = useState<'semantic' | 'hybrid'>('semantic')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const { data: filters } = useQuery({
    queryKey: ['search', 'filters'],
    queryFn: searchApi.getFilters,
  })

  const handleSearch = async () => {
    if (!searchQuery.query.trim()) return

    setIsSearching(true)
    try {
      const response = searchType === 'semantic' 
        ? await searchApi.semanticSearch(searchQuery)
        : await searchApi.hybridSearch(searchQuery)
      
      setResults(response.results)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const getCategoryColor = (category: string) => {
    const colors = {
      Safety: 'bg-red-100 text-red-800',
      Technical: 'bg-blue-100 text-blue-800',
      Business: 'bg-green-100 text-green-800',
      Equipment: 'bg-yellow-100 text-yellow-800',
      Regulatory: 'bg-purple-100 text-purple-800',
      Operational: 'bg-indigo-100 text-indigo-800',
    }
    return colors[category as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Search</h1>
          <p className="text-gray-600">Find documents using semantic and hybrid search</p>
        </div>

        {/* Search Interface */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Search Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Search Input */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <Input
                    placeholder="Enter your search query..."
                    value={searchQuery.query}
                    onChange={(e) => setSearchQuery(prev => ({ ...prev, query: e.target.value }))}
                    onKeyPress={handleKeyPress}
                  />
                </div>
                <Select
                  options={[
                    { value: 'semantic', label: 'Semantic Search' },
                    { value: 'hybrid', label: 'Hybrid Search' },
                  ]}
                  value={searchType}
                  onChange={(e) => setSearchType(e.target.value as 'semantic' | 'hybrid')}
                />
                <Button onClick={handleSearch} disabled={isSearching || !searchQuery.query.trim()}>
                  {isSearching ? 'Searching...' : 'Search'}
                </Button>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Select
                  label="Category"
                  options={[
                    { value: '', label: 'All Categories' },
                    ...(filters?.categories?.map(cat => ({ value: cat, label: cat })) || [])
                  ]}
                  value={searchQuery.filters?.category || ''}
                  onChange={(e) => setSearchQuery(prev => ({
                    ...prev,
                    filters: { ...prev.filters, category: e.target.value || undefined }
                  }))}
                />
                <Input
                  label="Date From"
                  type="date"
                  value={searchQuery.filters?.date_from || ''}
                  onChange={(e) => setSearchQuery(prev => ({
                    ...prev,
                    filters: { ...prev.filters, date_from: e.target.value || undefined }
                  }))}
                />
                <Input
                  label="Date To"
                  type="date"
                  value={searchQuery.filters?.date_to || ''}
                  onChange={(e) => setSearchQuery(prev => ({
                    ...prev,
                    filters: { ...prev.filters, date_to: e.target.value || undefined }
                  }))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Search Results */}
        {results.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>
                Search Results ({results.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {results.map((result, index) => (
                  <div key={result.id} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="h-4 w-4 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">
                            {result.metadata.document_title}
                          </h3>
                          <div className="flex items-center space-x-2 mt-1">
                            <Badge className={getCategoryColor(result.metadata.category)}>
                              {result.metadata.category}
                            </Badge>
                            <span className="text-xs text-gray-500">
                              Chunk {result.metadata.chunk_index + 1}
                            </span>
                            <span className="text-xs text-gray-500">
                              Score: {(result.similarity_score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <div className="text-sm text-gray-700 leading-relaxed">
                      {result.content}
                    </div>
                    
                    <div className="flex items-center justify-between mt-3 pt-3 border-t">
                      <div className="text-xs text-gray-500">
                        Document ID: {result.metadata.document_id}
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDate(result.metadata.created_at || new Date())}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* No Results */}
        {results.length === 0 && searchQuery.query && !isSearching && (
          <Card>
            <CardContent className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-500">
                Try adjusting your search query or filters
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  )
}
