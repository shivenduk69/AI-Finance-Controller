import apiClient from './apiClient';

export const reconciliationApi = {
  getSummary: (params = {}) => apiClient.get('/reconciliation/summary', { params }),
  getTransactions: (params = {}) => apiClient.get('/reconciliation/transactions', { params }),
  getTransactionAudit: (txId) => apiClient.get(`/reconciliation/transactions/${txId}/audit`),
};

export default reconciliationApi;
