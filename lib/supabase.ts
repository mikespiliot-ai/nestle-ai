import { createClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://nuvemdfqriecjsemepaf.supabase.co'
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51dmVtZGZxcmllY2pzZW1lcGFmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg3MTE0OTYsImV4cCI6MjA5NDI4NzQ5Nn0.GxNPdZGSL-kca-FXFA4_EcLvmFE9c21l_KFDWahgbJ4'

export const supabase = createClient(url, key)
