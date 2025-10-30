import axios, { AxiosInstance, AxiosError } from 'axios'
import { 
  UserProfile, 
  Group, 
  Student, 
  AttendanceSession, 
  AttendanceBatch,
  SessionStats 
} from '../types'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/webapp',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor to include Telegram initData
    this.api.interceptors.request.use((config) => {
      const initData = this.getTelegramInitData()
      if (initData) {
        config.headers['X-Telegram-Init-Data'] = initData
      }
      return config
    })

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message)
        
        if (error.response?.status === 401) {
          // Unauthorized - invalid Telegram data
          window.location.href = '/groups'
        }
        
        return Promise.reject(error)
      }
    )
  }

  private getTelegramInitData(): string {
    if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
      return window.Telegram.WebApp.initData || ''
    }
    
    // Fallback for development
    return 'dev_mode=true&user=%7B%22id%22%3A733455161%2C%22first_name%22%3A%22Test%22%2C%22last_name%22%3A%22User%22%7D'
  }

  // Auth endpoints
  async getUserProfile(): Promise<UserProfile> {
    const response = await this.api.get('/me')
    return response.data
  }

  // Groups endpoints
  async getGroups(): Promise<Group[]> {
    const response = await this.api.get('/groups')
    return response.data
  }

  async getGroup(groupId: number): Promise<Group> {
    const response = await this.api.get(`/groups/${groupId}`)
    return response.data
  }

  async getGroupStudents(groupId: number): Promise<Student[]> {
    const response = await this.api.get(`/groups/${groupId}/students`)
    return response.data
  }

  // Sessions endpoints
  async createSession(data: { group_id: number }): Promise<AttendanceSession> {
    const response = await this.api.post('/sessions', data)
    return response.data
  }

  async endSession(sessionId: number): Promise<void> {
    await this.api.put(`/sessions/${sessionId}/end`)
  }

  async getSessionStats(sessionId: number): Promise<SessionStats> {
    const response = await this.api.get(`/sessions/${sessionId}/stats`)
    return response.data
  }

  // Attendance endpoints
  async submitAttendance(batch: AttendanceBatch): Promise<void> {
    await this.api.post('/attendance/batch', batch)
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.api.get('/health')
    return response.data
  }
}

export const apiService = new ApiService()
export default apiService
