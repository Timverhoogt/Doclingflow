import { Layout } from '@/components/Layout/Layout'
import { StatsOverview } from '@/components/Dashboard/StatsOverview'
import { ProcessingChart } from '@/components/Dashboard/ProcessingChart'
import { CategoryDistribution } from '@/components/Dashboard/CategoryDistribution'
import { RecentDocuments } from '@/components/Dashboard/RecentDocuments'
import { QueueStatus } from '@/components/Dashboard/QueueStatus'

export default function HomePage() {
  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Overview of your document processing system</p>
        </div>

        {/* Stats Overview */}
        <StatsOverview />

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ProcessingChart />
          <CategoryDistribution />
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <RecentDocuments />
          </div>
          <div>
            <QueueStatus />
          </div>
        </div>
      </div>
    </Layout>
  )
}
