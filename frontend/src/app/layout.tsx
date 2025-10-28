import './globals.css'
import { Inter } from 'next/font/google'
import { QueryProvider } from '@/components/providers/QueryProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Doclingflow - Document Intelligence Platform',
  description: 'AI-powered document processing and search for petrochemical storage terminals',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  )
}
