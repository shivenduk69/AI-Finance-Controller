import apiClient from './apiClient';

export const notificationApi = {
  getNotifications: (params = {}) => apiClient.get('/notifications', { params }),
  markAsRead: (notificationId) => apiClient.post(`/notifications/${notificationId}/read`),
  markAllAsRead: () => apiClient.post('/notifications/read-all'),
};

export default notificationApi;
