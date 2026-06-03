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
  
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [kpiData, forecastData, rfmData, basketData] = await Promise.all([
        dashboardApi.getKPIs().catch(e => { console.error('KPI error:', e); return null; }),
        analyticsApi.getForecast(30).catch(e => { console.error('Forecast error:', e); return null; }),
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

  useEffect(() => { loadData() }, [])

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
                    <p className="text-[10px] font-black text-text-muted uppercase tracking-widest">Current Period</p>
                    <p className="text-sm font-bold text-text-primary">Fiscal Q3 / 2026</p>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1"><ForecastingWidget stats={forecast} /></div>
            <div className="lg:col-span-1"><SegmentationWidget data={rfm} /></div>
            <div className="lg:col-span-1"><BasketAnalysisWidget bundles={basket} /></div>
        </div>
      )}

      {/* 🛠️ Visual Layout Grid (Task 6) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Main Section */}
        <div className="xl:col-span-8 space-y-8">
          {(role === 'Admin' || role === 'Analytics Manager') && (
            <div className="glass-card p-8 group">
               <SalesPerformanceChart />
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
    if (role === 'Admin') return (
        <>
            <KPICard title="Institutional Revenue" value={kpis?.revenue?.value || 0} prefix="EGP " icon={DollarSign} color="emerald" change={kpis?.revenue?.change || 0} />
            <KPICard title="Total Settlements" value={kpis?.total_orders?.value || 0} icon={ShoppingBag} color="brand" change={kpis?.total_orders?.change || 0} />
            <KPICard title="Projected Margin" value={kpis?.margin?.value || 0} suffix="%" icon={TrendingUp} color="sky" change={kpis?.margin?.change || 0} label="MoM Margin Change" />
            <KPICard title="Growth Velocity" value={kpis?.revenue?.change || 0} suffix="%" icon={Target} color="amber" label="MoM Growth Rate" />
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
    if (role === 'Operations Manager') return (
        <>
            <KPICard title="Throughput" value={kpis?.throughput || 0} icon={ShoppingBag} color="emerald" label="Orders Handled" />
            <KPICard title="Service Level" value={kpis?.service_level || 98.5} suffix="%" icon={Target} color="brand" label="On-Time Delivery SLA" />
            <KPICard title="Process Alerts" value={kpis?.process_alerts || 0} icon={AlertTriangle} color="amber" label="Urgent Alerts Pending" />
            <KPICard title="Efficiency Index" value={4.9} suffix="/5" icon={TrendingUp} color="sky" label="SOP Health Index" />
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
