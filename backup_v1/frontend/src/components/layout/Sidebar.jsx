import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Package, ShoppingBag, Users, 
  Truck, BarChart3, Settings, BookOpen, ChevronRight, Zap
} from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Overview' },
  { to: '/inventory',   icon: Package,         label: 'Inventory Control' },
  { to: '/orders',      icon: ShoppingBag,     label: 'Sales Orders' },
  { to: '/customers',   icon: Users,           label: 'CRM' },
  { to: '/procurement', icon: Truck,           label: 'Supply Chain' },
  { to: '/analytics',   icon: BarChart3,       label: 'Business Intelligence' },
]

const ADMIN_ITEMS = [
  { to: '/settings',    icon: Settings,        label: 'System Config' },
  { to: '/knowledge',   icon: BookOpen,        label: 'Knowledge Base' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 min-w-64 h-screen bg-white border-r border-border flex flex-col pt-6">
      {/* Logo */}
      <div className="px-6 mb-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
             <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-text-primary tracking-tight">SmartERP</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            {({ isActive }) => (
              <div className={clsx('sidebar-link', isActive && 'active')}>
                <Icon className={clsx('w-4.5 h-4.5', isActive ? 'text-brand-600' : 'text-text-muted')} />
                <span className="flex-1">{label}</span>
              </div>
            )}
          </NavLink>
        ))}

        <div className="pt-6 pb-2 px-6">
           <p className="text-[10px] font-bold text-text-muted uppercase tracking-[0.1em]">Administration</p>
        </div>

        {ADMIN_ITEMS.map(({ to, icon: Icon, label }) => (
           <div key={to} className="sidebar-link">
             <Icon className="w-4.5 h-4.5 text-text-muted" />
             <span className="flex-1">{label}</span>
           </div>
        ))}
      </nav>

      {/* User Info */}
      <div className="p-4 border-t border-border mt-auto mb-2">
         <div className="flex items-center gap-3 p-2">
            <div className="w-10 h-10 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 font-bold">
               AH
            </div>
            <div className="flex-1 overflow-hidden">
               <p className="text-sm font-bold text-text-primary truncate">Ahmed Hany</p>
               <p className="text-[11px] text-text-muted">Admin</p>
            </div>
         </div>
      </div>
    </aside>
  )
}
