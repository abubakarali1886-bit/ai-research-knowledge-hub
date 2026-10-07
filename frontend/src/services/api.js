import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Get all documents
export const getDocuments = async () => {
  try {
    const response = await api.get('/documents/')
    return response.data
  } catch (error) {
    console.error('Error fetching documents:', error)
    throw error
  }
}

// Get document by ID
export const getDocument = async (id) => {
  try {
    const response = await api.get(`/documents/${id}`)
    return response.data
  } catch (error) {
    console.error('Error fetching document:', error)
    throw error
  }
}

export const deleteDocument = async (id) => {
  const response = await api.delete(`/documents/${id}`)
  return response.data
}

export const updateDocumentMetadata = async (id, metadata) => (await api.put(`/documents/${id}/metadata`, metadata)).data

export const downloadDocument = async (id) => {
  const response = await api.get(`/documents/${id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = response.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `document-${id}`
  link.click()
  URL.revokeObjectURL(url)
}

export const getDocumentViewUrl = async (id) => {
  const response = await api.get(`/documents/${id}/view`, { responseType: 'blob' })
  return URL.createObjectURL(response.data)
}

export const saveDocument = async (id) => (await api.post(`/documents/${id}/save`)).data
export const unsaveDocument = async (id) => (await api.delete(`/documents/${id}/save`)).data
export const getSavedDocuments = async () => (await api.get('/documents/saved/list')).data

// Upload document
export const uploadDocument = async (formData) => {
  try {
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  } catch (error) {
    console.error('Error uploading document:', error)
    throw error
  }
}

export const previewUpload = async (formData) => {
  const response = await api.post('/documents/upload/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// Semantic search
export const searchDocuments = async (query, topK = 5) => {
  try {
    const response = await api.post('/search/', { query, top_k: topK })
    return response.data
  } catch (error) {
    console.error('Error searching documents:', error)
    throw error
  }
}

// RAG Chat
export const askQuestion = async (question, topK = 5) => {
  try {
    const response = await api.post('/chat/', { question, top_k: topK })
    return response.data
  } catch (error) {
    console.error('Error asking question:', error)
    throw error
  }
}

// Summarize document
export const summarizeDocument = async (documentId, maxTokens = 500, temperature = 0.3) => {
  try {
    const response = await api.post('/summarize/', { 
      document_id: documentId, 
      max_tokens: maxTokens, 
      temperature 
    })
    return response.data
  } catch (error) {
    console.error('Error summarizing document:', error)
    throw error
  }
}

export const getDashboardSummary = async () => {
  const response = await api.get('/dashboard/summary')
  return response.data
}

export const getAdminDashboard = async (days = 30) => {
  const response = await api.get('/admin/dashboard', { params: { days } })
  return response.data
}

export const getAdminActivityLogs = async (date = null, startDate = null, endDate = null, limit = 200) => {
  const response = await api.get('/admin/activity', {
    params: { date, start_date: startDate, end_date: endDate, limit },
  })
  return response.data
}

export const getAdminActivityNotifications = async () => {
  const response = await api.get('/admin/activity/notifications')
  return response.data
}

export const markActivityReviewed = async (activityId) => {
  const response = await api.patch(`/admin/activity/${activityId}/review`)
  return response.data
}

export const exportAdminReport = async (date = null, startDate = null, endDate = null) => {
  const response = await api.get('/admin/activity/export-report', {
    params: { date, start_date: startDate, end_date: endDate },
    responseType: 'blob',
  })
  return response.data
}

export const listUsers = async () => {
  const response = await api.get('/admin/users')
  return response.data
}

export const createAdminUser = async (user) => {
  const response = await api.post('/admin/users', user)
  return response.data
}

export const updateUserRole = async (userId, role) => {
  const response = await api.patch(`/admin/users/${userId}/role`, { role })
  return response.data
}

export const updateUserStatus = async (userId, isActive) => {
  const response = await api.patch(`/admin/users/${userId}/status`, { is_active: isActive })
  return response.data
}

export const deleteUser = async (userId) => {
  const response = await api.delete(`/admin/users/${userId}`)
  return response.data
}

export const getCurrentUser = async () => {
  const token = localStorage.getItem('access_token')
  if (!token) return null

  const response = await api.get('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export const updateProfile = async (profile) => (await api.put('/auth/profile', profile)).data

export const login = async (username, password) => {
  const response = await api.post('/auth/login', { username, password })
  localStorage.setItem('access_token', response.data.access_token)
  return response.data
}

export const logout = async () => {
  try {
    await api.post('/auth/logout')
  } finally {
    localStorage.removeItem('access_token')
  }
}

export default api