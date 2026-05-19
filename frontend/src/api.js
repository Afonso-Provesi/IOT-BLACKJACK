import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const uploadImage = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/simulate/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadBase64 = (base64) =>
  api.post('/simulate/base64', { image: base64 })

export const getHistory = () => api.get('/history')

export const clearHistory = () => api.delete('/history')

export const getHealth = () => api.get('/health')

export default api
