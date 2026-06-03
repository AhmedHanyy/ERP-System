import { Bell, Search, LogOut, Shield, Sun, Moon } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
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
    <header className="h-20 px-8 flex items-center justify-between shrink-0 z-40" style={{ backgroundColor: 'var(--bg-surface)', borderBottom: '1px solid var(--border-main)' }}>
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
      <div className="flex items-center gap-4 ml-auto">
        {/* Theme Toggle */}
        <button 
            onClick={toggleTheme}
            className="p-2.5 rounded-xl transition-all hover:opacity-70"
            style={{ color: 'var(--text-muted)' }}
            title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
        >
            {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
        </button>

        {/* Notifications */}
        <div className="relative">
            <button 
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative p-2.5 text-text-secondary hover:bg-bg-hover rounded-xl transition-all"
            >
                <Bell className="w-5 h-5" />
                {notifications.some(n => !n.is_read) && (
                    <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-white"></span>
                )}
            </button>

            {showNotifs && (
                <div className="absolute right-0 mt-4 w-80 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-main)' }}>
                    <div className="p-4 bg-slate-50 dark:bg-slate-800 border-b border-border-main flex justify-between items-center">
                        <span className="font-bold text-text-primary">Notification Center</span>
                        <button 
                            onClick={async () => {
                                try {
                                    await axios.post('/api/analytics/notifications/clear');
                                    fetchNotifs();
                                } catch {}
                            }}
                            className="text-[10px] uppercase tracking-wider text-blue-600 font-bold hover:opacity-80 transition-opacity"
                        >
                            Mark all as read
                        </button>
                    </div>
                    <div className="max-h-96 overflow-y-auto scrollbar-hide">
                        {notifications.length > 0 ? (
                            ['Inventory', 'Procurement', 'Forecasting', 'Customer Analytics', 'System'].map(cat => {
                                const catNotifs = notifications.filter(n => n.category === cat || (!n.category && cat === 'System'));
                                if (catNotifs.length === 0) return null;

                                return (
                                    <div key={cat} className="p-2">
                                        <div className="px-3 py-1.5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                                            <span className="text-[10px] font-black uppercase tracking-widest text-text-muted">{cat}</span>
                                        </div>
                                        {catNotifs.map(n => (
                                            <div 
                                                key={n.id} 
                                                className={`p-4 rounded-xl mb-1 hover:bg-bg-body transition-colors cursor-pointer group ${!n.is_read ? 'bg-blue-50/30 dark:bg-blue-900/10' : ''}`}
                                                onClick={async () => {
                                                    try {
                                                        await axios.patch(`/api/analytics/notifications/${n.id}`);
                                                        fetchNotifs();
                                                    } catch {}
                                                }}
                                            >
                                                <div className="flex justify-between items-start gap-4">
                                                    <div>
                                                        <p className={`text-sm font-bold ${!n.is_read ? 'text-blue-600 dark:text-blue-400' : 'text-text-primary'}`}>{n.title}</p>
                                                        <p className="text-xs text-text-secondary leading-relaxed mt-1">{n.message}</p>
                                                        <p className="text-[9px] text-text-muted font-bold mt-2 uppercase tracking-tight">{new Date(n.created_at).toLocaleTimeString()}</p>
                                                    </div>
                                                    {!n.is_read && <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5" />}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                );
                            })
                        ) : (
                            <div className="p-8 text-center text-text-muted text-sm italic">System clear. No pending alerts.</div>
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
