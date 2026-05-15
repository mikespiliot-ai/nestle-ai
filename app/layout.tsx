import type { Metadata } from 'next'
import { Inter, Space_Grotesk } from 'next/font/google'
import './globals.css'
import AuroraBackground from '@/components/AuroraBackground'
import ParticleCanvas from '@/components/ParticleCanvas'
import TickerTape from '@/components/TickerTape'
import NavWithMenu from '@/components/NavWithMenu'
import SplashScreen from '@/components/SplashScreen'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], variable: '--font-space' })

export const metadata: Metadata = {
  title: 'CryptoLive — Ζωντανές Τιμές Κρυπτονομισμάτων',
  description: 'Ζωντανές τιμές κρυπτονομισμάτων σε πραγματικό χρόνο. Bitcoin, Ethereum, και 20+ κορυφαία κρυπτονομίσματα.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="el" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body>
        <AuroraBackground />
        <ParticleCanvas />
        <TickerTape />
        <NavWithMenu />
        <SplashScreen />
        <main style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </main>
      </body>
    </html>
  )
}
