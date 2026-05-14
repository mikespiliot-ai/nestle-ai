import type { Metadata } from 'next'
import Script from 'next/script'
import Nav from '@/components/Nav'
import './globals.css'

export const metadata: Metadata = {
  title: 'CryptoLive',
  description: 'Live cryptocurrency prices in real time',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="el">
      <body>
        <Script
          src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
          strategy="beforeInteractive"
        />
        <Nav />
        {children}
      </body>
    </html>
  )
}
