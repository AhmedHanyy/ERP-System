import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Package, ShoppingBag, Users, 
  Truck, BarChart3, Settings, BookOpen, Zap, Activity
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Overview' },
  { to: '/inventory',   icon: Package,         label: 'Inventory Control', roles: ['Admin', 'Operations Manager', 'Procurement Staff'] },
  { to: '/orders',      icon: ShoppingBag,     label: 'Sales Orders',      roles: ['Admin', 'Operations Manager', 'Customer Service'] },
  { to: '/customers',   icon: Users,           label: 'CRM',               roles: ['Admin', 'Customer Service'] },
  { to: '/procurement', icon: Truck,           label: 'Procurement',       roles: ['Admin', 'Procurement Staff'] },
  { to: '/analytics',   icon: BarChart3,       label: 'Intelligence',      roles: ['Admin', 'Analytics Manager'] },
]

const ADMIN_ITEMS = [
  { to: '/admin/logs',  icon: Activity,        label: 'Audit Ledger',      roles: ['Admin'] },
  { to: '/settings',    icon: Settings,        label: 'System Config',     roles: ['Admin'] },
]

export default function Sidebar() {
  const { user } = useAuth()

  const filterItems = (items) => items.filter(item => 
    !item.roles || item.roles.includes(user?.role) || user?.role === 'Admin'
  )

  return (
    <aside className="w-72 min-w-[18rem] h-screen bg-slate-900 border-r border-slate-800 flex flex-col pt-8 text-slate-300">
      {/* Premium Logo */}
      <div className="px-8 mb-12">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl bg-blue-600 flex items-center justify-center shadow-2xl shadow-blue-500/20 rotate-3">
             <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="text-2xl font-black text-white tracking-tighter">SmartERPi</span>
            <div className="h-1 w-6 bg-blue-500 rounded-full mt-1"></div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto scrollbar-hide">
        {filterItems(NAV_ITEMS).map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            {({ isActive }) => (
              <div className={clsx(
                'flex items-center gap-3 px-4 py-3.5 rounded-2xl text-[13px] font-bold transition-all group',
                isActive 
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' 
                  : 'hover:bg-white/5 hover:text-white'
              )}>
                <Icon className={clsx('w-5 h-5 transition-transform group-hover:scale-110', isActive ? 'text-blue-400' : 'text-slate-500')} />
                <span className="flex-1 tracking-tight">{label}</span>
              </div>
            )}
          </NavLink>
        ))}

        <div className="pt-8 pb-3 px-8">
           <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] border-b border-slate-800 pb-2">Administration</p>
        </div>

        {filterItems(ADMIN_ITEMS).map(({ to, icon: Icon, label }) => (
           <NavLink key={to} to={to}>
             {({ isActive }) => (
                <div className={clsx(
                    'flex items-center gap-3 px-4 py-3.5 rounded-2xl text-[13px] font-bold transition-all group',
                    isActive ? 'text-blue-400' : 'text-slate-500 hover:text-white'
                )}>
                    <Icon className="w-5 h-5 transition-transform group-hover:rotate-12" />
                    <span className="flex-1 tracking-tight">{label}</span>
                </div>
             )}
           </NavLink>
        ))}
      </nav>

      {/* Enterprise Footer */}
      <div className="p-8 mt-auto">
         <div className="bg-slate-800/50 rounded-2xl p-4 border border-slate-800">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm">
                    {user?.username?.substring(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-white truncate">{user?.username}</p>
                    <p className="text-[10px] font-black text-blue-500 uppercase tracking-tighter mt-0.5">{user?.role}</p>
                </div>
            </div>
         </div>
      </div>
    </aside>
  )
}
