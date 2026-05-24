import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error.response?.data || error)
  }
)

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const dashboardApi = {
  getKPIs:          ()       => api.get('/dashboard/kpis'),
  getSalesTrend:    (period) => api.get(`/dashboard/sales-trend?period=${period}`),
  getTopProducts:   ()       => api.get('/dashboard/top-products'),
  getOrderStatus:   ()       => api.get('/dashboard/order-status-distribution'),
  getRecentOrders:  ()       => api.get('/dashboard/recent-orders'),
  getInventoryAlerts: ()     => api.get('/dashboard/inventory-alerts'),
}

// ─── Orders ───────────────────────────────────────────────────────────────────
export const ordersApi = {
  list:         (params) => api.get('/orders/', { params }),
  get:          (id)     => api.get(`/orders/${id}`),
  updateStatus: (id, status) => api.put(`/orders/${id}/status`, { status }),
  getStats:     ()       => api.get('/orders/stats'),
}

// ─── Inventory ────────────────────────────────────────────────────────────────
export const inventoryApi = {
  list:    (params) => api.get('/inventory/', { params }),
  adjust:  (productId, data) => api.put(`/inventory/${productId}/adjust`, data),
  summary: ()       => api.get('/inventory/summary'),
}

// ─── Customers ────────────────────────────────────────────────────────────────
export const customersApi = {
  list:     (params) => api.get('/customers/', { params }),
  get:      (id)     => api.get(`/customers/${id}`),
  segments: ()       => api.get('/customers/segments'),
}

// ─── Procurement ─────────────────────────────────────────────────────────────
export const procurementApi = {
  listSuppliers:    ()     => api.get('/procurement/suppliers'),
  getSupplier:      (id)   => api.get(`/procurement/suppliers/${id}`),
  listRequests:     (params) => api.get('/procurement/requests', { params }),
  createRequest:    (data) => api.post('/procurement/requests', data),
  updateStatus:     (id, status) => api.put(`/procurement/requests/${id}/status`, { status }),
  getSuggestions:   ()     => api.get('/procurement/suggestions'),
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export const analyticsApi = {
  getForecast:      (days)  => api.get(`/analytics/forecast?days=${days}`),
  getProductForecast: (id, days) => api.get(`/analytics/forecast/product/${id}?days=${days}`),
  getRFM:           ()      => api.get('/analytics/rfm'),
  getMarketBasket:  (params) => api.get('/analytics/market-basket', { params }),
  getBIReport:      ()      => api.get('/analytics/bi-report'),
  getETLStatus:     ()      => api.get('/analytics/etl-status'),
}

export default api
