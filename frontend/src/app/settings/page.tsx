'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Layout } from '@/components/Layout/Layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { settingsApi, AppSettings, WatchFolder } from '@/services/settings'
import { Settings, Plus, Trash2, Save, FolderPlus } from 'lucide-react'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'llm' | 'processing' | 'folders'>('general')
  const [showAddFolderModal, setShowAddFolderModal] = useState(false)
  const [newFolder, setNewFolder] = useState<Partial<WatchFolder>>({
    enabled: true,
    recursive: true,
    file_patterns: ['*.pdf', '*.docx', '*.xlsx', '*.pptx'],
  })

  const queryClient = useQueryClient()

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.getSettings,
  })

  const { data: watchFolders, isLoading: foldersLoading } = useQuery({
    queryKey: ['settings', 'watch-folders'],
    queryFn: settingsApi.getWatchFolders,
  })

  const updateSettingsMutation = useMutation({
    mutationFn: settingsApi.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const addFolderMutation = useMutation({
    mutationFn: settingsApi.addWatchFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'watch-folders'] })
      setShowAddFolderModal(false)
      setNewFolder({ enabled: true, recursive: true, file_patterns: ['*.pdf', '*.docx', '*.xlsx', '*.pptx'] })
    },
  })

  const removeFolderMutation = useMutation({
    mutationFn: settingsApi.removeWatchFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'watch-folders'] })
    },
  })

  const handleSaveSettings = (updatedSettings: Partial<AppSettings>) => {
    updateSettingsMutation.mutate(updatedSettings)
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'llm', label: 'LLM Settings', icon: Settings },
    { id: 'processing', label: 'Processing', icon: Settings },
    { id: 'folders', label: 'Watch Folders', icon: FolderPlus },
  ]

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600">Configure your document processing system</p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-4 w-4 inline mr-2" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* General Settings */}
        {activeTab === 'general' && (
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Max File Size (MB)"
                  type="number"
                  value={settings?.max_file_size ? settings.max_file_size / (1024 * 1024) : 50}
                  onChange={(e) => handleSaveSettings({ max_file_size: parseInt(e.target.value) * 1024 * 1024 })}
                />
                <Input
                  label="Processing Batch Size"
                  type="number"
                  value={settings?.processing_batch_size || 5}
                  onChange={(e) => handleSaveSettings({ processing_batch_size: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Supported Formats</label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {settings?.supported_formats?.map((format) => (
                    <Badge key={format} variant="secondary">{format}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* LLM Settings */}
        {activeTab === 'llm' && (
          <Card>
            <CardHeader>
              <CardTitle>LLM Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                  label="LLM Provider"
                  options={[
                    { value: 'openrouter', label: 'OpenRouter' },
                    { value: 'openai', label: 'OpenAI' },
                    { value: 'anthropic', label: 'Anthropic' },
                  ]}
                  value={settings?.llm_provider || 'openrouter'}
                  onChange={(e) => handleSaveSettings({ llm_provider: e.target.value })}
                />
                <Input
                  label="LLM Model"
                  value={settings?.llm_model || 'claude-3.5-sonnet'}
                  onChange={(e) => handleSaveSettings({ llm_model: e.target.value })}
                />
              </div>
              <Input
                label="API Key"
                type="password"
                value={settings?.llm_api_key || ''}
                onChange={(e) => handleSaveSettings({ llm_api_key: e.target.value })}
                helperText="Your API key is encrypted and stored securely"
              />
              <Input
                label="Embedding Model"
                value={settings?.embedding_model || 'text-embedding-3-small'}
                onChange={(e) => handleSaveSettings({ embedding_model: e.target.value })}
              />
            </CardContent>
          </Card>
        )}

        {/* Processing Settings */}
        {activeTab === 'processing' && (
          <Card>
            <CardHeader>
              <CardTitle>Processing Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Chunk Size"
                  type="number"
                  value={settings?.chunk_size || 1000}
                  onChange={(e) => handleSaveSettings({ chunk_size: parseInt(e.target.value) })}
                  helperText="Number of characters per chunk"
                />
                <Input
                  label="Chunk Overlap"
                  type="number"
                  value={settings?.chunk_overlap || 200}
                  onChange={(e) => handleSaveSettings({ chunk_overlap: parseInt(e.target.value) })}
                  helperText="Overlap between chunks"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Classification Categories</label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {settings?.classification_categories?.map((category) => (
                    <Badge key={category} variant="secondary">{category}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Watch Folders */}
        {activeTab === 'folders' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Watch Folders</CardTitle>
                <Button onClick={() => setShowAddFolderModal(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Folder
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {foldersLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {watchFolders?.map((folder) => (
                    <div key={folder.path} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{folder.path}</p>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge variant={folder.enabled ? 'success' : 'secondary'}>
                            {folder.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                          {folder.recursive && (
                            <Badge variant="secondary">Recursive</Badge>
                          )}
                          <span className="text-sm text-gray-500">
                            {folder.file_patterns.length} patterns
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFolderMutation.mutate(folder.path)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Add Folder Modal */}
        <Modal
          isOpen={showAddFolderModal}
          onClose={() => setShowAddFolderModal(false)}
          title="Add Watch Folder"
        >
          <div className="space-y-4">
            <Input
              label="Folder Path"
              placeholder="/path/to/folder"
              value={newFolder.path || ''}
              onChange={(e) => setNewFolder(prev => ({ ...prev, path: e.target.value }))}
            />
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={newFolder.enabled}
                  onChange={(e) => setNewFolder(prev => ({ ...prev, enabled: e.target.checked }))}
                  className="mr-2"
                />
                Enabled
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={newFolder.recursive}
                  onChange={(e) => setNewFolder(prev => ({ ...prev, recursive: e.target.checked }))}
                  className="mr-2"
                />
                Recursive
              </label>
            </div>
            <div className="flex space-x-3">
              <Button
                variant="outline"
                onClick={() => setShowAddFolderModal(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => addFolderMutation.mutate(newFolder as WatchFolder)}
                disabled={!newFolder.path || addFolderMutation.isPending}
              >
                {addFolderMutation.isPending ? 'Adding...' : 'Add Folder'}
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </Layout>
  )
}
