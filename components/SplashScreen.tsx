'use client'
import { useState, useEffect } from 'react'

export default function SplashScreen() {
  const [visible, setVisible] = useState(false)
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const seen = sessionStorage.getItem('splash_seen')
    if (!seen) {
      setVisible(true)
    }
  }, [])

  const handleEnter = () => {
    sessionStorage.setItem('splash_seen', '1')
    setVisible(false)
    setTimeout(() => setHidden(true), 650)
  }

  if (hidden) return null
  if (!visible) return null

  return (
    <div className="splash-screen">
      <div className="splash-dots">
        <div className="splash-dot" />
        <div className="splash-dot" />
        <div className="splash-dot" />
      </div>
      <div className="splash-logo">CryptoLive</div>
      <div className="splash-subtitle">Ζωντανές τιμές κρυπτονομισμάτων σε πραγματικό χρόνο</div>
      <button className="splash-btn" onClick={handleEnter}>
        Είσοδος →
      </button>
    </div>
  )
}
