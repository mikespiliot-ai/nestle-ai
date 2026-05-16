import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  'https://nuvemdfqriecjsemepaf.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51dmVtZGZxcmllY2pzZW1lcGFmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg3MTE0OTYsImV4cCI6MjA5NDI4NzQ5Nn0.GxNPdZGSL-kca-FXFA4_EcLvmFE9c21l_KFDWahgbJ4'
)
