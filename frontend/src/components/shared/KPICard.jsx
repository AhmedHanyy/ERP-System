import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'
import clsx from 'clsx'

export default function KPICard({ title, value, change, label, icon: Icon, color = 'brand', prefix = '', suffix = '', chartData = [] }) {
  const isPositive = change > 0
  const isNeutral  = change === 0

  return (
    <div className="glass-card p-6 flex flex-col justify-between">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="stat-label text-text-muted">{title}</p>
          <p className="stat-value text-2xl mt-1">
            {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
        </div>
        <div className={clsx('p-2.5 rounded-xl bg-opacity-10', {
          'bg-brand-500 text-brand-500': color === 'brand',
          'bg-accent-emerald text-accent-emerald': color === 'emerald',
          'bg-accent-sky text-accent-sky': color === 'sky',
          'bg-accent-amber text-accent-amber': color === 'amber',
          'bg-accent-rose text-accent-rose': color === 'rose',
        })}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="flex items-end justify-between gap-4 mt-auto">
        {change !== undefined ? (
          <div className={clsx(
            'flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-lg',
            isPositive ? 'text-accent-emerald bg-emerald-50 dark:bg-emerald-950/20' : 'text-accent-rose bg-rose-50 dark:bg-rose-950/20'
          )}>
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {Math.abs(change)}%
            <span className="text-text-muted font-normal ml-0.5">vs last month</span>
          </div>
        ) : label ? (
          <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">{label}</span>
        ) : null}

        {/* Mini Sparkline */}
        <div className="h-10 w-20">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData.length ? chartData : [{v:10}, {v:15}, {v:12}, {v:18}, {v:14}, {v:20}]}>
              <defs>
                <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isPositive ? '#10B981' : '#F43F5E'} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={isPositive ? '#10B981' : '#F43F5E'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area 
                type="monotone" dataKey="v" 
                stroke={isPositive ? '#10B981' : '#F43F5E'} 
                strokeWidth={2} fill={`url(#grad-${color})`} 
                dot={false} 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
