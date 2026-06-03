import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Package, ShoppingBag, Users, UserCog,
  Truck, BarChart3, Settings, Zap, Activity, ChevronLeft, ChevronRight
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Overview' },
  { to: '/inventory',   icon: Package,         label: 'Inventory Control', roles: ['Admin', 'Operations Manager', 'Procurement Staff', 'Procurement Officer'] },
  { to: '/orders',      icon: ShoppingBag,     label: 'Sales Orders',      roles: ['Admin', 'Operations Manager', 'Customer Service'] },
  { to: '/customers',   icon: Users,           label: 'CRM',               roles: ['Admin', 'Customer Service'] },
  { to: '/procurement', icon: Truck,           label: 'Procurement',       roles: ['Admin', 'Procurement Staff', 'Procurement Officer'] },
  { to: '/analytics',   icon: BarChart3,       label: 'Intelligence',      roles: ['Admin', 'Analytics Manager'] },
]

const ADMIN_ITEMS = [
  { to: '/users',       icon: UserCog,         label: 'User Governance',   roles: ['Admin'] },
  { to: '/admin/logs',  icon: Activity,        label: 'Audit Ledger',      roles: ['Admin'] },
  { to: '/settings',    icon: Settings,        label: 'System Config',     roles: ['Admin'] },
]

export default function Sidebar() {
  const { user } = useAuth()
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('sidebar-collapsed') === 'true'
  })

  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', isCollapsed)
  }, [isCollapsed])

  const filterItems = (items) => items.filter(item => 
    !item.roles || item.roles.includes(user?.role) || user?.role === 'Admin'
  )

  return (
    <aside className={clsx(
      "h-screen bg-slate-900 border-r border-slate-800 flex flex-col pt-8 text-slate-300 transition-all duration-300 ease-in-out relative shrink-0",
      isCollapsed ? "w-20 min-w-[5rem]" : "w-72 min-w-[18rem]"
    )}>
      {/* Premium Logo */}
      <div className={clsx("mb-12 transition-all duration-300 flex items-center", isCollapsed ? "px-4 flex flex-col gap-4" : "px-8 justify-between")}>
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl bg-blue-600 flex items-center justify-center shadow-2xl shadow-blue-500/20 rotate-3 shrink-0">
             <Zap className="w-6 h-6 text-white" />
          </div>
          {!isCollapsed && (
            <div>
              <span className="text-2xl font-black text-white tracking-tighter">SmartERPi</span>
              <div className="h-1 w-6 bg-blue-500 rounded-full mt-1"></div>
            </div>
          )}
        </div>
        
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)} 
          className={clsx(
            "p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors",
            isCollapsed && "w-8 h-8 flex items-center justify-center"
          )}
          title={isCollapsed ? "Expand Navigation" : "Collapse Navigation"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto scrollbar-hide">
        {filterItems(NAV_ITEMS).map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}>
            {({ isActive }) => (
              <div 
                title={isCollapsed ? label : undefined}
                className={clsx(
                  'flex items-center rounded-2xl text-[13px] font-bold transition-all group',
                  isCollapsed ? 'justify-center p-3.5' : 'gap-3 px-4 py-3.5',
                  isActive 
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' 
                    : 'hover:bg-white/5 hover:text-white'
                )}
              >
                <Icon className={clsx('w-5 h-5 transition-transform group-hover:scale-110 shrink-0', isActive ? 'text-blue-400' : 'text-slate-500')} />
                {!isCollapsed && <span className="flex-1 tracking-tight">{label}</span>}
              </div>
            )}
          </NavLink>
        ))}

        {isCollapsed ? (
          <div className="py-4 border-b border-slate-800 mx-2" />
        ) : (
          <div className="pt-8 pb-3 px-8">
             <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] border-b border-slate-800 pb-2">Administration</p>
          </div>
        )}

        {filterItems(ADMIN_ITEMS).map(({ to, icon: Icon, label }) => (
           <NavLink key={to} to={to}>
             {({ isActive }) => (
                <div 
                  title={isCollapsed ? label : undefined}
                  className={clsx(
                    'flex items-center rounded-2xl text-[13px] font-bold transition-all group',
                    isCollapsed ? 'justify-center p-3.5' : 'gap-3 px-4 py-3.5',
                    isActive ? 'text-blue-400' : 'text-slate-500 hover:text-white'
                  )}
                >
                    <Icon className="w-5 h-5 transition-transform group-hover:rotate-12 shrink-0" />
                    {!isCollapsed && <span className="flex-1 tracking-tight">{label}</span>}
                </div>
             )}
           </NavLink>
        ))}
      </nav>

      {/* Enterprise Footer */}
      <div className={clsx("mt-auto transition-all duration-300", isCollapsed ? "p-4 flex justify-center" : "p-8")}>
         {isCollapsed ? (
           <div 
             title={`${user?.username} (${user?.role})`}
             className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm border border-slate-850 shadow-lg cursor-pointer"
           >
               {user?.username?.substring(0, 2).toUpperCase() || 'US'}
           </div>
         ) : (
           <div className="bg-slate-800/50 rounded-2xl p-4 border border-slate-800">
              <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm shrink-0">
                      {user?.username?.substring(0, 2).toUpperCase() || 'US'}
                  </div>
                  <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-white truncate">{user?.username || 'User'}</p>
                      <p className="text-[10px] font-black text-blue-500 uppercase tracking-tighter mt-0.5">{user?.role || 'Staff'}</p>
                  </div>
              </div>
           </div>
         )}
      </div>
    </aside>
  )
}
