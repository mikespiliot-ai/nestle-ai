'use client'
import { useEffect, useRef } from 'react'

interface SparklineChartProps {
  data: number[]
  positive: boolean
}

export default function SparklineChart({ data, positive }: SparklineChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !data || data.length < 2) return
    const ctx = canvas.getContext('2d')!
    const w = canvas.width
    const h = canvas.height

    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1

    ctx.clearRect(0, 0, w, h)

    const color = positive ? '#00e676' : '#ff3d57'

    const grad = ctx.createLinearGradient(0, 0, 0, h)
    grad.addColorStop(0, positive ? 'rgba(0,230,118,0.3)' : 'rgba(255,61,87,0.3)')
    grad.addColorStop(1, 'rgba(0,0,0,0)')

    const pts = data.map((v, i) => ({
      x: (i / (data.length - 1)) * w,
      y: h - ((v - min) / range) * h * 0.85 - h * 0.07,
    }))

    // Fill area
    ctx.beginPath()
    ctx.moveTo(pts[0].x, h)
    pts.forEach((pt) => ctx.lineTo(pt.x, pt.y))
    ctx.lineTo(pts[pts.length - 1].x, h)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    // Line
    ctx.beginPath()
    ctx.moveTo(pts[0].x, pts[0].y)
    pts.forEach((pt) => ctx.lineTo(pt.x, pt.y))
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.stroke()
  }, [data, positive])

  return (
    <canvas
      ref={canvasRef}
      width={200}
      height={50}
      className="card-sparkline"
      style={{ width: '100%', height: '50px' }}
    />
  )
}
