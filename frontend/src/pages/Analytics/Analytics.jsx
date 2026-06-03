import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { Sparkles, Users, ShoppingCart, BarChart3, Database, RefreshCw } from 'lucide-react'
import Forecasting  from './Forecasting'
import Segmentation from './Segmentation'
import MarketBasket from './MarketBasket'
import BIReports    from './BIReports'
import Simulator    from './Simulator'
import ETLVisualizer from './ETLVisualizer'

const TABS = [
  { path: 'forecasting', label: 'Forecasting',   icon: Sparkles, color: 'text-accent-violet' },
  { path: 'segmentation', label: 'Segmentation', icon: Users,    color: 'text-accent-emerald' },
  { path: 'market-basket', label: 'Basket Rules', icon: ShoppingCart, color: 'text-accent-sky' },
  { path: 'bi-reports',    label: 'BI Reports',   icon: BarChart3, color: 'text-brand-400' },
  { path: 'etl',           label: 'ETL Pipeline', icon: RefreshCw,  color: 'text-accent-sky' },
  { path: 'simulator',     label: 'Scenario Simulator', icon: Database,  color: 'text-text-muted' },
]

export default function Analytics() {
  const location = useLocation()
  
  return (
    <div className="space-y-6">
      <div className="page-header relative">
        <div className="flex items-center gap-3">
           <div className="p-2 rounded-xl bg-accent-violet/10 border border-accent-violet/20">
              <Sparkles className="w-5 h-5 text-accent-violet animate-pulse-slow" />
           </div>
           <div>
             <h2 className="page-title text-gradient-brand">Business Intelligence Engine</h2>
             <p className="page-subtitle">AI-driven decision support & predictive retail mining</p>
           </div>
        </div>

        {/* Tab Navigation */}
        <div className="mt-8 flex gap-1 p-1 border border-border rounded-xl shadow-sm w-fit" style={{ backgroundColor: 'var(--bg-surface)' }}>
          {TABS.map(tab => (
            <NavLink
              key={tab.path}
              to={`/analytics/${tab.path}`}
              className={({ isActive }) => `
                flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200
                ${isActive 
                  ? 'bg-brand-50 dark:bg-blue-950/40 text-brand-600 dark:text-blue-400 shadow-sm border border-brand-100 dark:border-blue-900/30' 
                  : 'text-text-muted hover:text-text-secondary hover:bg-bg-hover'
                }
              `}
            >
              <tab.icon className={`w-3.5 h-3.5 ${tab.color}`} />
              {tab.label}
            </NavLink>
          ))}
        </div>
      </div>

      <div className="animate-fade-in">
        <Routes>
          <Route index element={<Navigate to="forecasting" replace />} />
          <Route path="forecasting"   element={<Forecasting />} />
          <Route path="segmentation"  element={<Segmentation />} />
          <Route path="market-basket" element={<MarketBasket />} />
          <Route path="bi-reports"    element={<BIReports />} />
          <Route path="etl"           element={<ETLVisualizer />} />
          <Route path="simulator"     element={<Simulator />} />
        </Routes>
      </div>
    </div>
  )
}
