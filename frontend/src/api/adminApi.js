import apiClient from './apiClient';

export const adminApi = {
  getMetrics: () => apiClient.get('/admin/metrics'),
  getMerchants: () => apiClient.get('/admin/merchants'),
  createMerchant: (payload) => apiClient.post('/admin/merchants', payload),
  getStores: (merchantId) => apiClient.get('/admin/stores', { params: { merchant_id: merchantId } }),
  createStore: (payload) => apiClient.post('/admin/stores', payload),
  getUsers: () => apiClient.get('/admin/users'),
  createUser: (payload) => apiClient.post('/admin/users', payload),
  getAuditLogs: (params = {}) => apiClient.get('/admin/audit-logs', { params }),
  getConfig: () => apiClient.get('/admin/config'),
  updateConfig: (payload) => apiClient.put('/admin/config', payload),
};

export default adminApi;
