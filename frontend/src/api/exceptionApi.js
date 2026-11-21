import apiClient from './apiClient';

export const exceptionApi = {
  getExceptions: (params = {}) => apiClient.get('/exceptions', { params }),
  submitResolution: (payload) => apiClient.post('/exceptions/resolve', payload),
  verifyResolution: (resolutionId, payload) =>
    apiClient.post(`/exceptions/${resolutionId}/verify`, payload),
  directResolve: (resolutionId, payload) =>
    apiClient.post(`/exceptions/${resolutionId}/direct-resolve`, payload),
};

export default exceptionApi;
