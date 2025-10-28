'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { analyticsApi } from '@/services/analytics'
import { Clock, CheckCircle, AlertCircle, Pause } from 'lucide-react'

export function QueueStatus() {
  const { data: queueStatus, isLoading } = useQuery({
    queryKey: ['analytics', 'queue-status'],
    queryFn: analyticsApi.getQueueStatus,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processing Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="h-4 w-4 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-20" />
                </div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-8" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const queueItems = [
    {
      label: 'Pending',
      value: queueStatus?.pending || 0,
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
    {
      label: 'Processing',
      value: queueStatus?.processing || 0,
      icon: Pause,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      label: 'Completed',
      value: queueStatus?.completed || 0,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      label: 'Failed',
      value: queueStatus?.failed || 0,
      icon: AlertCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {queueItems.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-full ${item.bgColor}`}>
                  <item.icon className={`h-4 w-4 ${item.color}`} />
                </div>
                <span className="text-sm font-medium text-gray-700">
                  {item.label}
                </span>
              </div>
              <Badge variant="secondary" className="font-mono">
                {item.value}
              </Badge>
            </div>
          ))}
          
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Total</span>
              <Badge variant="default" className="font-mono">
                {queueStatus?.total || 0}
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
