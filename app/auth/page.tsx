'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'

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

export default function AuthPage() {
  const router = useRouter()
  const lang = useLang()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const t = {
    loginTab: lang === 'en' ? 'Login' : 'Σύνδεση',
    registerTab: lang === 'en' ? 'Register' : 'Εγγραφή',
    emailLabel: lang === 'en' ? 'Email' : 'Email',
    passwordLabel: lang === 'en' ? 'Password' : 'Κωδικός',
    loginBtn: lang === 'en' ? 'Login' : 'Σύνδεση',
    registerBtn: lang === 'en' ? 'Register' : 'Εγγραφή',
    googleBtn: lang === 'en' ? 'Continue with Google' : 'Συνέχεια με Google',
    or: lang === 'en' ? 'or' : 'ή',
    backHome: lang === 'en' ? '← Back to home' : '← Αρχική',
    checkEmail: lang === 'en'
      ? 'Check your email to confirm your account.'
      : 'Ελέγξτε το email σας για επιβεβαίωση.',
    forgotPassword: lang === 'en' ? 'Forgot password?' : 'Ξέχασες τον κωδικό;',
    resetSent: lang === 'en'
      ? 'Check your email for the password reset link.'
      : 'Ελέγξτε το email σας για τον σύνδεσμο επαναφοράς κωδικού.',
  }

  const clearState = () => {
    setError(null)
    setSuccess(null)
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    clearState()
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      router.push('/portfolio')
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    clearState()
    setLoading(true)
    const { error } = await supabase.auth.signUp({ email, password })
    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      setSuccess(t.checkEmail)
    }
  }

  const handleForgotPassword = async () => {
    if (!email) {
      setError(lang === 'en' ? 'Enter your email first.' : 'Εισάγετε πρώτα το email σας.')
      return
    }
    clearState()
    setLoading(true)
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: typeof window !== 'undefined' ? window.location.origin + '/auth/callback' : undefined,
    })
    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      setSuccess(t.resetSent)
    }
  }

  const handleGoogle = async () => {
    clearState()
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: typeof window !== 'undefined' ? window.location.origin + '/portfolio' : undefined,
      },
    })
  }

  const handleTabChange = (newTab: 'login' | 'register') => {
    setTab(newTab)
    clearState()
    setEmail('')
    setPassword('')
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-tabs">
          <button
            className={`auth-tab${tab === 'login' ? ' active' : ''}`}
            onClick={() => handleTabChange('login')}
          >
            {t.loginTab}
          </button>
          <button
            className={`auth-tab${tab === 'register' ? ' active' : ''}`}
            onClick={() => handleTabChange('register')}
          >
            {t.registerTab}
          </button>
        </div>

        {success ? (
          <div className="auth-success">{success}</div>
        ) : (
          <form onSubmit={tab === 'login' ? handleLogin : handleRegister}>
            <div className="auth-field">
              <label className="auth-label">{t.emailLabel}</label>
              <input
                className="tool-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
              />
            </div>
            <div className="auth-field">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="auth-label">{t.passwordLabel}</label>
                {tab === 'login' && (
                  <button
                    type="button"
                    onClick={handleForgotPassword}
                    style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: '0.75rem', cursor: 'pointer', padding: 0 }}
                  >
                    {t.forgotPassword}
                  </button>
                )}
              </div>
              <input
                className="tool-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required={tab === 'register'}
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
              />
            </div>

            {error && <div className="auth-error">{error}</div>}

            <button
              className="tool-calc-btn"
              type="submit"
              disabled={loading}
              style={{ width: '100%', marginTop: '1rem' }}
            >
              {loading ? '...' : tab === 'login' ? t.loginBtn : t.registerBtn}
            </button>
          </form>
        )}

        <div className="auth-divider">{t.or}</div>

        <button
          className="auth-google-btn auth-google-full"
          onClick={handleGoogle}
          type="button"
        >
          <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.8591-3.0477.8591-2.3441 0-4.3282-1.5831-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z" fill="#34A853"/>
            <path d="M3.964 10.71c-.18-.54-.2827-1.1168-.2827-1.71s.1023-1.17.2827-1.71V4.9582H.9574C.3477 6.1731 0 7.5477 0 9s.3477 2.8268.9574 4.0418L3.964 10.71z" fill="#FBBC05"/>
            <path d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5813C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9574 4.9582L3.964 7.29C4.6718 5.1627 6.6559 3.5795 9 3.5795z" fill="#EA4335"/>
          </svg>
          {t.googleBtn}
        </button>

        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <Link href="/" style={{ color: 'var(--muted)', fontSize: '0.82rem', textDecoration: 'none' }}>
            {t.backHome}
          </Link>
        </div>
      </div>
    </div>
  )
}
