'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { documentsApi } from '@/services/documents'
import { formatFileSize } from '@/lib/utils'
import { Upload, X, FileText, AlertCircle } from 'lucide-react'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const uploadFiles = async () => {
    if (files.length === 0) return

    setUploading(true)
    setUploadProgress({})

    try {
      const uploadPromises = files.map(async (file, index) => {
        try {
          setUploadProgress(prev => ({ ...prev, [file.name]: 0 }))
          
          const result = await documentsApi.uploadDocument(file)
          
          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }))
          return result
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          throw error
        }
      })

      await Promise.all(uploadPromises)
      onSuccess()
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setUploading(false)
      setFiles([])
      setUploadProgress({})
    }
  }

  const getFileIcon = (file: File) => {
    if (file.type.includes('pdf')) return '📄'
    if (file.type.includes('word')) return '📝'
    if (file.type.includes('sheet')) return '📊'
    if (file.type.includes('presentation')) return '📽️'
    return '📄'
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Upload Documents" size="lg">
      <div className="space-y-6">
        {/* Drop Zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-700 mb-2">
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-sm text-gray-500">
            or click to select files
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Supports PDF, DOCX, XLSX, PPTX, TXT (max 50MB each)
          </p>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-medium text-gray-700">Selected Files ({files.length})</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getFileIcon(file)}</span>
                    <div>
                      <p className="font-medium text-gray-900">{file.name}</p>
                      <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {uploadProgress[file.name] !== undefined && (
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${uploadProgress[file.name]}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">
                          {uploadProgress[file.name]}%
                        </span>
                      </div>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      disabled={uploading}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            {files.length > 0 && (
              <p>
                Total size: {formatFileSize(files.reduce((acc, file) => acc + file.size, 0))}
              </p>
            )}
          </div>
          <div className="flex space-x-3">
            <Button variant="outline" onClick={onClose} disabled={uploading}>
              Cancel
            </Button>
            <Button
              onClick={uploadFiles}
              disabled={files.length === 0 || uploading}
            >
              {uploading ? 'Uploading...' : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  )
}
