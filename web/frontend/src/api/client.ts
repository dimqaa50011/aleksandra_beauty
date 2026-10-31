import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/client/cabinet/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Access-токен хранится в памяти (в Pinia), не в localStorage
let accessToken: string | null = null
let refreshPromise: Promise<string> | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        // Если несколько запросов упали одновременно — обновляем только раз
        if (!refreshPromise) {
          refreshPromise = axios
            .post('/api/client/cabinet/v1/auth/refresh/', {}, { withCredentials: true })
            .then((res) => {
              const newToken = res.data.access
              setAccessToken(newToken)
              return newToken
            })
            .finally(() => {
              refreshPromise = null
            })
        }
        const newToken = await refreshPromise
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      } catch (refreshError) {
        setAccessToken(null)
        
        // ИСПРАВЛЕНО: Используем BASE_URL для правильного редиректа внутри /cabinet/
        const loginPath = `${import.meta.env.BASE_URL}login`
        if (window.location.pathname !== loginPath) {
          window.location.href = loginPath
        }
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient