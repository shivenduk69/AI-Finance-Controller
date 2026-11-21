import apiClient from './apiClient';

export const aiApi = {
  chat: (payload) => apiClient.post('/ai/chat', payload),
  getConversations: () => apiClient.get('/ai/conversations'),
  getConversationMessages: (id) => apiClient.get(`/ai/conversations/${id}/messages`),
  deleteConversation: (id) => apiClient.delete(`/ai/conversations/${id}`),
  taxAudit: (payload = {}) => apiClient.post('/ai/tax-audit', payload),
  cashForecast: (days = 7) => apiClient.get('/ai/cash-forecast', { params: { days } }),
};

export default aiApi;
