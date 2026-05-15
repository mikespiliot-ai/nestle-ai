import { createClient } from '@supabase/supabase-js'

const rawUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const rawKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

const url = rawUrl.startsWith('https://') ? rawUrl : 'https://placeholder.supabase.co'
const key = rawKey.length > 10 ? rawKey : 'placeholder_anon_key_for_build_only'

export const supabase = createClient(url, key)
