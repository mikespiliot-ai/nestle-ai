import { getGlobal } from '@/lib/api'

export async function GET() {
  const data = await getGlobal()
  return Response.json(data)
}
