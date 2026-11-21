import apiClient from './apiClient';

export const ticketApi = {
  getTickets: (params = {}) => apiClient.get('/tickets', { params }),
  createTicket: (payload) => apiClient.post('/tickets', payload),
  replyTicket: (ticketId, payload) => apiClient.post(`/tickets/${ticketId}/reply`, payload),
};

export default ticketApi;
