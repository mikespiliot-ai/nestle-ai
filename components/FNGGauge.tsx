'use client'

interface FNGGaugeProps {
  value: number
  classification: string
}

const LABELS: Record<string, string> = {
  'Extreme Fear': 'Ακραίος Φόβος',
  Fear: 'Φόβος',
  Neutral: 'Ουδέτερο',
  Greed: 'Απληστία',
  'Extreme Greed': 'Ακραία Απληστία',
}

const ZONES = [
  { label: 'Extreme Fear', color: '#ff3d57', start: 0, end: 25 },
  { label: 'Fear', color: '#ff8c42', start: 25, end: 45 },
  { label: 'Neutral', color: '#f59e0b', start: 45, end: 55 },
  { label: 'Greed', color: '#84cc16', start: 55, end: 75 },
  { label: 'Extreme Greed', color: '#00e676', start: 75, end: 100 },
]

function getColor(value: number): string {
  for (const zone of ZONES) {
    if (value <= zone.end) return zone.color
  }
  return '#00e676'
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

export default function FNGGauge({ value, classification }: FNGGaugeProps) {
  const cx = 120
  const cy = 110
  const r = 90
  const strokeWidth = 16

  // Gauge goes from -180deg to 0deg (left to right, bottom is 0)
  // Map value 0-100 → -180 to 0 degrees (i.e., 180 deg sweep on bottom half)
  const startDeg = 180
  const endDeg = 360
  const needleAngle = startDeg + (value / 100) * 180

  const color = getColor(value)

  return (
    <div className="fng-panel">
      <div className="fng-title">Fear &amp; Greed Index</div>
      <div className="fng-gauge-wrap" style={{ width: 240, height: 150 }}>
        <svg width={240} height={150} viewBox="0 0 240 150">
          {/* Background arc */}
          <path
            d={describeArc(cx, cy, r, 180, 360)}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Zone arcs */}
          {ZONES.map((zone) => {
            const sa = 180 + (zone.start / 100) * 180
            const ea = 180 + (zone.end / 100) * 180
            return (
              <path
                key={zone.label}
                d={describeArc(cx, cy, r, sa, ea)}
                fill="none"
                stroke={zone.color}
                strokeWidth={strokeWidth}
                opacity={0.35}
              />
            )
          })}

          {/* Active arc (0 to value) */}
          <path
            d={describeArc(cx, cy, r, 180, needleAngle)}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Needle */}
          {(() => {
            const rad = ((needleAngle - 90) * Math.PI) / 180
            const nx = cx + (r - strokeWidth / 2 - 4) * Math.cos(rad)
            const ny = cy + (r - strokeWidth / 2 - 4) * Math.sin(rad)
            return (
              <>
                <line
                  x1={cx}
                  y1={cy}
                  x2={nx}
                  y2={ny}
                  stroke="white"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                />
                <circle cx={cx} cy={cy} r={5} fill="white" />
              </>
            )
          })()}
        </svg>
      </div>
      <div className="fng-value" style={{ color }}>
        {value}
      </div>
      <div className="fng-label">{LABELS[classification] || classification}</div>
    </div>
  )
}
