import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import Dashboard  from '@/pages/Dashboard/Dashboard'
import Orders     from '@/pages/Orders/Orders'
import Inventory  from '@/pages/Inventory/Inventory'
import Procurement from '@/pages/Procurement/Procurement'
import Customers  from '@/pages/Customers/Customers'
import Analytics  from '@/pages/Analytics/Analytics'

export default function App() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"   element={<Dashboard />} />
          <Route path="orders"      element={<Orders />} />
          <Route path="inventory"   element={<Inventory />} />
          <Route path="procurement" element={<Procurement />} />
          <Route path="customers"   element={<Customers />} />
          <Route path="analytics/*" element={<Analytics />} />
        </Route>
      </Routes>
    </div>
  )
}
