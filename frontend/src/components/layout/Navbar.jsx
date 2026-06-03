import { Bell, Search, LogOut, Shield } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Navbar() {
  const { user, logout } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [showNotifs, setShowNotifs] = useState(false)

  const fetchNotifs = async () => {
    try {
        const res = await axios.get(`/api/analytics/notifications?role=${user?.role}`)
        setNotifications(res.data)
    } catch {}
  }

  useEffect(() => { fetchNotifs() }, [user])

  return (
    <header className="h-20 bg-white border-b border-slate-100 px-8 flex items-center justify-between shrink-0 z-40">
      {/* Search Bar */}
      <div className="relative flex-1 max-w-lg hidden md:block">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Global system search..."
          className="w-full bg-slate-50 border border-slate-100 rounded-2xl pl-11 pr-4 py-2.5 text-sm focus:ring-4 focus:ring-blue-500/5 outline-none placeholder:text-slate-400 transition-all"
        />
      </div>

      {/* Right Icons */}
      <div className="flex items-center gap-6 ml-auto">
        {/* Notifications */}
        <div className="relative">
            <button 
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative p-2.5 text-slate-500 hover:bg-slate-50 rounded-xl transition-all"
            >
                <Bell className="w-5 h-5" />
                {notifications.some(n => !n.is_read) && (
                    <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-white"></span>
                )}
            </button>

            {showNotifs && (
                <div className="absolute right-0 mt-4 w-80 bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                    <div className="p-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
                        <span className="font-bold text-slate-800">System Alerts</span>
                        <span className="text-[10px] uppercase tracking-wider text-blue-600 font-bold">New Logs</span>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length > 0 ? notifications.map(n => (
                            <div key={n.id} className="p-4 border-b border-slate-50 hover:bg-slate-50 transition-colors">
                                <p className="text-sm font-bold text-slate-900 mb-1">{n.title}</p>
                                <p className="text-xs text-slate-500 leading-relaxed">{n.message}</p>
                            </div>
                        )) : (
                            <div className="p-8 text-center text-slate-400 text-sm">No new notifications</div>
                        )}
                    </div>
                </div>
            )}
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-4 pl-6 border-l border-slate-100">
            <div className="text-right hidden sm:block">
                <p className="text-sm font-bold text-slate-900 leading-none">{user?.username || 'System'}</p>
                <p className="text-[10px] uppercase tracking-tight text-blue-600 font-bold mt-1.5 flex items-center justify-end gap-1">
                    <Shield className="w-2.5 h-2.5" />
                    {user?.role}
                </p>
            </div>
            <button 
                onClick={logout}
                className="p-3 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all group"
            >
                <LogOut className="w-5 h-5 group-hover:scale-110 transition-transform" />
            </button>
        </div>
      </div>
    </header>
  )
}
