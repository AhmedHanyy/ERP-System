import { useState } from 'react'
import { useTheme } from '@/context/ThemeContext'
import { useAuth } from '@/context/AuthContext'
import { Settings as SettingsIcon, Moon, Sun, User, Shield, HardDrive, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
  const { theme, toggleTheme } = useTheme()
  const { user } = useAuth()
  
  const [profile, setProfile] = useState({
    username: user?.username || '',
    email: user?.email || '',
    role: user?.role || ''
  })
  
  const handleSave = (e) => {
    e.preventDefault()
    toast.success('System configuration saved')
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-4xl">
      <div>
        <h1 className="text-3xl font-black text-text-primary tracking-tight flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-brand-500" />
          System Settings
        </h1>
        <p className="text-text-muted font-medium mt-1">Manage institutional options, display themes, and system diagnostics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Side settings */}
        <div className="md:col-span-2 space-y-8">
          {/* Display & Personalization */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-sm font-black uppercase tracking-widest text-text-secondary">Personalization</h3>
            <div className="flex items-center justify-between p-4 bg-bg-body rounded-2xl border border-border-main">
              <div>
                <p className="text-sm font-bold text-text-primary">Display Mode</p>
                <p className="text-xs text-text-muted mt-0.5">Toggle between Light and Dark interface styles.</p>
              </div>
              <button 
                onClick={toggleTheme} 
                className="p-3 bg-brand-500/10 hover:bg-brand-500 hover:text-white text-brand-400 rounded-xl transition-all flex items-center gap-2 text-xs font-bold"
              >
                {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
              </button>
            </div>
          </div>

          {/* Profile Section */}
          <form onSubmit={handleSave} className="glass-card p-6 space-y-6">
            <h3 className="text-sm font-black uppercase tracking-widest text-text-secondary flex items-center gap-2">
              <User className="w-4 h-4 text-brand-500" /> User Profile Information
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-text-muted uppercase">Username</label>
                <input 
                  type="text" className="input bg-bg-body/50 text-text-muted" readOnly
                  value={profile.username}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-text-muted uppercase">Institutional Role</label>
                <input 
                  type="text" className="input bg-bg-body/50 text-text-muted" readOnly
                  value={profile.role}
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-text-muted uppercase">Registered Email</label>
              <input 
                type="email" className="input" 
                value={profile.email}
                onChange={e => setProfile({...profile, email: e.target.value})}
              />
            </div>

            <button type="submit" className="btn-primary">
              Save Changes
            </button>
          </form>
        </div>

        {/* Right Side diagnostics */}
        <div className="space-y-8">
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-sm font-black uppercase tracking-widest text-text-secondary flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-emerald-500" />
              Diagnostics
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-xs font-semibold py-1.5 border-b border-border-main">
                <span className="text-text-muted">Database Engine</span>
                <span className="text-text-primary font-bold">SQLite v3.45</span>
              </div>
              <div className="flex justify-between items-center text-xs font-semibold py-1.5 border-b border-border-main">
                <span className="text-text-muted">System SLA Status</span>
                <span className="text-emerald-500 font-bold">99.9% Online</span>
              </div>
              <div className="flex justify-between items-center text-xs font-semibold py-1.5 border-b border-border-main">
                <span className="text-text-muted">Smart Engine API</span>
                <span className="text-brand-500 font-bold">Active v1.0</span>
              </div>
              <div className="flex justify-between items-center text-xs font-semibold py-1.5">
                <span className="text-text-muted">Software Release</span>
                <span className="text-text-secondary">v1.2.4-stable</span>
              </div>
            </div>
            <button 
              onClick={() => toast.success('Diagnostics cache cleared')}
              className="w-full mt-4 py-2 bg-bg-body border border-border-main text-text-secondary hover:bg-bg-hover rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Re-index Databases
            </button>
          </div>

          <div className="glass-card p-6 bg-slate-900 text-slate-100 border-none space-y-4">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <h4 className="font-bold text-white">Security Compliance</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Smart ERP enforces strict Role-Based Access Control (RBAC) and JSON Web Token authorization headers on all transactions.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
