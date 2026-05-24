import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8', xl: 'w-12 h-12' }
  return <Loader2 className={`${sizes[size]} animate-spin text-brand-400 ${className}`} />
}

export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <LoadingSpinner size="lg" />
      <p className="text-sm text-text-muted">Loading data...</p>
    </div>
  )
}

export function ErrorState({ message = 'Failed to load data', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
      <div className="w-12 h-12 rounded-2xl bg-accent-rose/10 flex items-center justify-center">
        <span className="text-accent-rose text-xl">!</span>
      </div>
      <div>
        <p className="text-text-primary font-medium">{message}</p>
        <p className="text-xs text-text-muted mt-1">Make sure the backend server is running on port 5000</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-xs mt-2">
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title = 'No data found', subtitle, icon: Icon }) {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-center">
      {Icon && (
        <div className="w-12 h-12 rounded-2xl bg-bg-hover flex items-center justify-center">
          <Icon className="w-5 h-5 text-text-muted" />
        </div>
      )}
      <div>
        <p className="text-text-secondary font-medium text-sm">{title}</p>
        {subtitle && <p className="text-xs text-text-muted mt-1">{subtitle}</p>}
      </div>
    </div>
  )
}
