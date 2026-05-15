'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user)
      setLoading(false)
    })

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: typeof window !== 'undefined' ? window.location.origin + '/portfolio' : undefined,
      },
    })
  }

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
        <button className="auth-logout-btn" onClick={handleLogout} title="Αποσύνδεση">
          Αποσύνδεση
        </button>
      </div>
    )
  }

  return (
    <button className="auth-google-btn" onClick={handleLogin}>
      <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z" fill="#4285F4"/>
        <path d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.8591-3.0477.8591-2.3441 0-4.3282-1.5831-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853"/>
        <path d="M3.964 10.71c-.18-.54-.2827-1.1168-.2827-1.71s.1023-1.17.2827-1.71V4.9582H.9574C.3477 6.1731 0 7.5477 0 9s.3477 2.8268.9574 4.0418L3.964 10.71z" fill="#FBBC05"/>
        <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5813C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9574 4.9582L3.964 7.29C4.6718 5.1627 6.6559 3.5795 9 3.5795z" fill="#EA4335"/>
      </svg>
      Σύνδεση με Google
    </button>
  )
}
