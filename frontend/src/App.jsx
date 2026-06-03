import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import Layout from '@/components/layout/Layout'
import Dashboard  from '@/pages/Dashboard/Dashboard'
import Orders     from '@/pages/Orders/Orders'
import Inventory  from '@/pages/Inventory/Inventory'
import Procurement from '@/pages/Procurement/Procurement'
import Customers  from '@/pages/Customers/Customers'
import Analytics  from '@/pages/Analytics/Analytics'
import Login      from '@/pages/Auth/Login'

const ProtectedRoute = ({ children, roles = [] }) => {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) return null;
    if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
    
    if (roles.length > 0 && !roles.includes(user.role) && user.role !== 'Admin') {
        return <Navigate to="/dashboard" replace />;
    }

    return children;
};

export default function App() {
  return (
    <AuthProvider>
        <div className="min-h-screen bg-bg-primary">
            <Routes>
                <Route path="/login" element={<Login />} />
                
                <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                    <Route index element={<Navigate to="/dashboard" replace />} />
                    <Route path="dashboard"   element={<Dashboard />} />
                    <Route path="orders"      element={<ProtectedRoute roles={['Admin', 'Operations Manager', 'Customer Service']}><Orders /></ProtectedRoute>} />
                    <Route path="inventory"   element={<ProtectedRoute roles={['Admin', 'Operations Manager', 'Procurement Staff']}><Inventory /></ProtectedRoute>} />
                    <Route path="procurement" element={<ProtectedRoute roles={['Admin', 'Procurement Staff']}><Procurement /></ProtectedRoute>} />
                    <Route path="customers"   element={<ProtectedRoute roles={['Admin', 'Customer Service']}><Customers /></ProtectedRoute>} />
                    <Route path="analytics/*" element={<ProtectedRoute roles={['Admin', 'Analytics Manager']}><Analytics /></ProtectedRoute>} />
                </Route>
            </Routes>
        </div>
    </AuthProvider>
  )
}
