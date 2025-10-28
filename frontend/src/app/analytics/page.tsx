'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout } from '@/components/Layout/Layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { analyticsApi } from '@/services/analytics'
import { ProcessingChart } from '@/components/Dashboard/ProcessingChart'
import { CategoryDistribution } from '@/components/Dashboard/CategoryDistribution'
import { StatsOverview } from '@/components/Dashboard/StatsOverview'
import { QueueStatus } from '@/components/Dashboard/QueueStatus'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { BarChart3, TrendingUp, Calendar } from 'lucide-react'

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('30')

  const { data: overview } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: analyticsApi.getOverview,
    refetchInterval: 30000,
  })

  const { data: timeline } = useQuery({
    queryKey: ['analytics', 'timeline', timeRange],
    queryFn: () => analyticsApi.getTimeline(parseInt(timeRange)),
    refetchInterval: 60000,
  })

  const { data: categories } = useQuery({
    queryKey: ['analytics', 'categories'],
    queryFn: analyticsApi.getCategories,
    refetchInterval: 60000,
  })

  const { data: queueStatus } = useQuery({
    queryKey: ['analytics', 'queue-status'],
    queryFn: analyticsApi.getQueueStatus,
    refetchInterval: 10000,
  })

  const timeRangeOptions = [
    { value: '7', label: 'Last 7 days' },
    { value: '30', label: 'Last 30 days' },
    { value: '90', label: 'Last 90 days' },
    { value: '365', label: 'Last year' },
  ]

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
            <p className="text-gray-600">Detailed insights into your document processing system</p>
          </div>
          <div className="flex items-center space-x-3">
            <Select
              options={timeRangeOptions}
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
            />
            <Button variant="outline">
              <Calendar className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Overview Stats */}
        <StatsOverview />

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ProcessingChart />
          <CategoryDistribution />
        </div>

        {/* Additional Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Processing Performance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Processing Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Success Rate</span>
                  <span className="text-lg font-semibold text-green-600">
                    {overview ? 
                      `${((overview.documents_by_status?.completed || 0) / 
                        (overview.total_documents || 1) * 100).toFixed(1)}%` 
                      : '0%'
                    }
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Avg Processing Time</span>
                  <span className="text-lg font-semibold">2.3 min</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Queue Wait Time</span>
                  <span className="text-lg font-semibold">45 sec</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Queue Status */}
          <QueueStatus />

          {/* Document Types */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Document Types
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categories}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="category" 
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Detailed Timeline */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <YAxis />
                  <Tooltip 
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                    formatter={(value, name) => [
                      value,
                      name === 'documents_processed' ? 'Processed' : 'Failed'
                    ]}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="documents_processed" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="documents_failed" 
                    stroke="#ef4444" 
                    strokeWidth={2}
                    dot={{ fill: '#ef4444' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-green-600">99.9%</div>
                <div className="text-sm text-gray-600">Uptime</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-blue-600">2.1s</div>
                <div className="text-sm text-gray-600">Avg Response</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">45%</div>
                <div className="text-sm text-gray-600">CPU Usage</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-purple-600">2.1GB</div>
                <div className="text-sm text-gray-600">Memory</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}
