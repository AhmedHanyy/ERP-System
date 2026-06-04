import { useState, useEffect } from 'react'
import { ShoppingBag, DollarSign, Truck, BarChart2, Calendar, Target, AlertTriangle, Users, TrendingUp, Layers } from 'lucide-react'
import { dashboardApi, analyticsApi } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import KPICard  from '@/components/shared/KPICard'
import { PageLoader, ErrorState } from '@/components/shared/States'
import { ForecastingWidget, SegmentationWidget, BasketAnalysisWidget } from './InformaticsWidgets'
import SalesPerformanceChart from './SalesPerformanceChart'
import TopSKUProgress        from './TopSKUProgress'
import RecentOrdersTable     from './RecentOrdersTable'
import CustomerInsights      from './CustomerInsights'
import ProcurementTimeline   from './ProcurementTimeline'

export default function Dashboard() {
  const { user } = useAuth()
  const [kpis,      setKpis]      = useState(null)
  const [forecast,  setForecast]  = useState(null)
  const [rfm,       setRfm]       = useState(null)
  const [basket,    setBasket]    = useState(null)
  const [dateRange, setDateRange] = useState('all')
  
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [kpiData, forecastData, rfmData, basketData] = await Promise.all([
        dashboardApi.getKPIs(dateRange).catch(e => { console.error('KPI error:', e); return null; }),
        analyticsApi.getForecast(30, dateRange).catch(e => { console.error('Forecast error:', e); return null; }),
        analyticsApi.getRFM().catch(e => { console.error('RFM error:', e); return null; }),
        analyticsApi.getMarketBasket().catch(e => { console.error('Basket error:', e); return null; })
      ])
      
      setKpis(kpiData)
      setForecast(forecastData)
      setRfm(rfmData)
      setBasket(basketData)
    } catch (e) {
      setError('Failed to load dashboard analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [dateRange])

  if (loading) return <PageLoader />
  if (error)   return <ErrorState message={error} onRetry={loadData} />

  const role = user?.role || 'Admin'

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700 pb-12">
      {/* Premium Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="badge-brand">{role} Workspace</span>
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">Live System Update</span>
          </div>
          <h2 className="text-4xl font-black text-text-primary tracking-tight">Enterprise Intelligence</h2>
          <p className="text-text-muted font-medium mt-1">Strategic command center for SmartERP ecosystem.</p>
        </div>
        
        <div className="flex items-center gap-3">
            <div className="p-3 bg-white dark:bg-slate-900 border border-border-main rounded-2xl flex items-center gap-4 px-6 shadow-sm">
                <div className="text-right">
                    <p className="text-[10px] font-black text-text-muted uppercase tracking-widest">Date Range</p>
                    <select 
                        className="text-sm font-bold text-text-primary bg-transparent border-none outline-none cursor-pointer p-0 m-0"
                        value={dateRange}
                        onChange={(e) => setDateRange(e.target.value)}
                    >
                        <option value="30d">Last 30 Days</option>
                        <option value="90d">Last 90 Days</option>
                        <option value="6m">Last 6 Months</option>
                        <option value="12m">Last 12 Months</option>
                        <option value="all">All Time / Live</option>
                    </select>
                </div>
                <div className="w-px h-8 bg-border-main" />
                <Calendar className="w-5 h-5 text-blue-500" />
            </div>
        </div>
      </div>

      {/* 🚀 Role-Specific KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {renderRoleKPIs(role, kpis)}
      </div>

      {/* 📊 Strategic Intelligence Row (Task 5) */}
      {(role === 'Admin' || role === 'Analytics Manager') && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-1"><ForecastingWidget stats={forecast} /></div>
            <div className="lg:col-span-1"><SegmentationWidget data={rfm} /></div>
            <div className="lg:col-span-1"><BasketAnalysisWidget bundles={basket} /></div>
            <div className="lg:col-span-1">
               <div className="glass-card p-6 h-full flex flex-col relative overflow-hidden group hover:shadow-card-hover transition-all duration-300">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-bl-full -z-10 group-hover:bg-rose-500/10 transition-colors"></div>
                  <div className="flex justify-between items-start mb-6">
                     <div>
                        <h3 className="font-bold text-text-primary mb-1">Unmapped Revenue</h3>
                        <p className="text-[10px] text-text-muted uppercase tracking-wider font-bold">Historical Legacy Data</p>
                     </div>
                     <div className="p-2.5 bg-rose-500/10 rounded-xl text-rose-500">
                        <AlertTriangle className="w-5 h-5" />
                     </div>
                  </div>
                  
                  <div className="mt-auto space-y-4">
                     <div>
                        <p className="text-3xl font-bold text-text-primary tracking-tight">
                           <span className="text-sm text-text-muted mr-1 font-normal">EGP</span>
                           {kpis?.unmapped_stats?.revenue?.toLocaleString() || 0}
                        </p>
                     </div>
                     
                     <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                        <div>
                           <p className="text-[10px] text-text-muted uppercase mb-1">Units Sold</p>
                           <p className="text-sm font-bold text-text-primary">{kpis?.unmapped_stats?.units?.toLocaleString() || 0}</p>
                        </div>
                        <div>
                           <p className="text-[10px] text-text-muted uppercase mb-1">Revenue Share</p>
                           <p className="text-sm font-bold text-rose-400">{kpis?.unmapped_stats?.share_pct || 0}%</p>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
        </div>
      )}

      {/* 🛠️ Visual Layout Grid (Task 6) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Main Section */}
        <div className="xl:col-span-8 space-y-8">
          {(role === 'Admin' || role === 'Analytics Manager') && (
            <div className="glass-card p-8 group">
               <SalesPerformanceChart dateRange={dateRange} />
            </div>
          )}

          {(role === 'Procurement Staff' || role === 'Operations Manager') && (
            <RecentOrdersTable />
          )}
          
          {role === 'Analytics Manager' && <RecentOrdersTable />}
          {role === 'Admin' && <RecentOrdersTable />}
        </div>

        {/* Info Section */}
        <div className="xl:col-span-4 space-y-8">
          <TopSKUProgress />
          {renderSidePanel(role, rfm)}
        </div>
      </div>
    </div>
  )
}

function renderRoleKPIs(role, kpis) {
    if (role === 'Admin' || role === 'Operations Manager' || role === 'Analytics Manager') return (
        <>
            <KPICard title="Total Revenue" value={kpis?.revenue?.value || 0} prefix="EGP " icon={DollarSign} color="emerald" change={kpis?.revenue?.change} />
            <KPICard title="Total Orders" value={kpis?.orders?.value || 0} icon={ShoppingBag} color="brand" change={kpis?.orders?.change} />
            <KPICard title="Total Customers" value={kpis?.customers?.value || 0} icon={Users} color="sky" change={kpis?.customers?.change} />
            <KPICard title="Active Products" value={kpis?.products?.value || 0} icon={Layers} color="amber" change={kpis?.products?.change} />
            <KPICard title="Inventory Value" value={kpis?.inventory_value?.value || 0} prefix="EGP " icon={TrendingUp} color="brand" change={kpis?.inventory_value?.change} />
            <KPICard title="Average Order Value" value={kpis?.aov?.value || 0} prefix="EGP " icon={DollarSign} color="emerald" change={kpis?.aov?.change} />
            <KPICard title="Gross Profit" value={kpis?.gross_profit?.value || 0} prefix="EGP " icon={TrendingUp} color="sky" change={kpis?.gross_profit?.change} />
            <KPICard title="Gross Margin" value={kpis?.gross_margin?.value || 0} suffix="%" icon={Target} color="amber" change={kpis?.gross_margin?.change} />
        </>
    )
    if (role === 'Procurement Staff' || role === 'Procurement Officer') return (
        <>
            <KPICard title="Stock Depletion" value={kpis?.low_stock_alerts?.value || 0} icon={AlertTriangle} color="rose" label="CRITICAL REORDERS" />
            <KPICard title="Transit Assets" value={kpis?.transit_assets?.count || 0} icon={Truck} color="brand" label={`Value: EGP ${kpis?.transit_assets?.value?.toLocaleString() || 0}`} />
            <KPICard title="Supply Latency" value={kpis?.supply_latency || 7.2} suffix=" Days" icon={Calendar} color="sky" label="Average Delivery Lead" />
            <KPICard title="Resource Allocation" value={kpis?.resource_allocation || 45} suffix="%" icon={DollarSign} color="amber" label="Budget Allocated" />
        </>
    )
    return (
        <>
            <KPICard title="System Orders" value={kpis?.total_orders?.value || 0} icon={ShoppingBag} color="brand" change={kpis?.total_orders?.change || 0} />
            <KPICard title="Market Revenue" value={kpis?.revenue?.value || 0} prefix="EGP " icon={DollarSign} color="sky" change={kpis?.revenue?.change || 0} />
            <KPICard title="Client Retention" value={kpis?.client_retention || 88} suffix="%" icon={Users} color="emerald" label="Returning Customers" />
            <KPICard title="System SLA" value={99.9} suffix="%" icon={Target} color="amber" label="System Availability" />
        </>
    )
}

function renderSidePanel(role, rfm) {
    switch(role) {
        case 'Procurement Staff':
        case 'Procurement Officer': return <ProcurementTimeline hideFull />;
        case 'Customer Service': return <CustomerInsights />;
        case 'Analytics Manager': return <SegmentationWidget data={rfm} />;
        default: return <CustomerInsights />;
    }
}
