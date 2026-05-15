'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'

function useLang() {
  const [lang, setLang] = useState<'el' | 'en'>('el')
  useEffect(() => {
    const stored = localStorage.getItem('lang') as 'el' | 'en' | null
    if (stored === 'en') setLang('en')
    const handler = () => {
      const v = localStorage.getItem('lang') as 'el' | 'en' | null
      setLang(v === 'en' ? 'en' : 'el')
    }
    window.addEventListener('langchange', handler)
    return () => window.removeEventListener('langchange', handler)
  }, [])
  return lang
}

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const lang = useLang()

  useEffect(() => {
    // Get initial session
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
  }

  if (loading) {
    return (
      <div className="auth-btn-skeleton" />
    )
  }

  if (user) {
    const avatarUrl = user.user_metadata?.avatar_url as string | undefined
    const displayName = (user.user_metadata?.full_name as string | undefined) || user.email || 'User'
    const initials = displayName.charAt(0).toUpperCase()
    const logoutLabel = lang === 'en' ? 'Logout' : 'Αποσύνδεση'

    return (
      <div className="auth-user-wrap">
        {avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={avatarUrl}
            alt={displayName}
            className="auth-avatar"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="auth-avatar-placeholder">{initials}</div>
        )}
        <button className="auth-logout-btn" onClick={handleLogout} title={logoutLabel}>
          {logoutLabel}
        </button>
      </div>
    )
  }

  const loginLabel = lang === 'en' ? 'Login' : 'Σύνδεση'

  return (
    <button className="auth-google-btn" onClick={() => router.push('/auth')}>
      {loginLabel}
    </button>
  )
}
