'use client'
import { useEffect, useState } from 'react'

export default function Splash() {
  const [visible, setVisible] = useState(false)
  const [hiding, setHiding] = useState(false)

  useEffect(() => {
    if (!sessionStorage.getItem('cryptolive_splash')) setVisible(true)
  }, [])

  const handleGo = () => {
    setHiding(true)
    sessionStorage.setItem('cryptolive_splash', '1')
    setTimeout(() => setVisible(false), 600)
  }

  if (!visible) return null

  return (
    <div className={`splash${hiding ? ' hiding' : ''}`}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center' }}>
        <h1>₿ CryptoLive</h1>
        <p>Τιμές κρυπτονομισμάτων σε πραγματικό χρόνο</p>
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        {['🔴 Live τιμές', '📊 Διαδραστικά γραφήματα', '💼 Portfolio tracker'].map(pill => (
          <span key={pill} style={{ padding: '0.4rem 1rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '999px', fontSize: '0.85rem' }}>
            {pill}
          </span>
        ))}
      </div>
      <button className="splash-btn" onClick={handleGo}>Let&#39;s Go →</button>
    </div>
  )
}
