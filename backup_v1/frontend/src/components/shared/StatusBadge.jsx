import clsx from 'clsx'

const STATUS_CONFIG = {
  // Order statuses
  'Pending':    { cls: 'badge-neutral', dot: 'bg-text-muted' },
  'Preparing':  { cls: 'badge-info',    dot: 'bg-accent-sky' },
  'Shipped':    { cls: 'badge-brand',   dot: 'bg-brand-400' },
  'Delivered':  { cls: 'badge-success', dot: 'bg-accent-emerald' },
  'Cancelled':  { cls: 'badge-danger',  dot: 'bg-accent-rose' },
  // Inventory statuses
  'In Stock':      { cls: 'badge-success', dot: 'bg-accent-emerald' },
  'Low Stock':     { cls: 'badge-warning', dot: 'bg-accent-amber' },
  'Out of Stock':  { cls: 'badge-danger',  dot: 'bg-accent-rose' },
  // Procurement statuses
  'Draft':      { cls: 'badge-neutral', dot: 'bg-text-muted' },
  'Sent':       { cls: 'badge-info',    dot: 'bg-accent-sky' },
  'Confirmed':  { cls: 'badge-brand',   dot: 'bg-brand-400' },
  'Received':   { cls: 'badge-success', dot: 'bg-accent-emerald' },
  // Customer segments
  'Champion':   { cls: 'badge-success', dot: 'bg-accent-emerald' },
  'Loyal':      { cls: 'badge-brand',   dot: 'bg-brand-400' },
  'At-Risk':    { cls: 'badge-warning', dot: 'bg-accent-amber' },
  'Lost':       { cls: 'badge-danger',  dot: 'bg-accent-rose' },
  'New':        { cls: 'badge-info',    dot: 'bg-accent-sky' },
  // Urgency
  'Critical':   { cls: 'badge-danger',  dot: 'bg-accent-rose' },
  'High':       { cls: 'badge-warning', dot: 'bg-accent-amber' },
}

export default function StatusBadge({ status, showDot = true }) {
  const config = STATUS_CONFIG[status] || { cls: 'badge-neutral', dot: 'bg-text-muted' }
  return (
    <span className={config.cls}>
      {showDot && <span className={clsx('w-1.5 h-1.5 rounded-full', config.dot)} />}
      {status}
    </span>
  )
}
