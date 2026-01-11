import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../services/api'

interface User {
  id: number
  username: string
  email: string
  role: string
  full_name?: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      
      login: async (username: string, password: string) => {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)
        
        const response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        
        const { access_token } = response.data
        
        // Set token in API headers
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        
        // Get user info with explicit auth header
        const userResponse = await api.get('/auth/me', {
          headers: { 'Authorization': `Bearer ${access_token}` }
        })
        
        set({
          token: access_token,
          user: userResponse.data,
          isAuthenticated: true
        })
      },
      
      logout: () => {
        delete api.defaults.headers.common['Authorization']
        set({
          token: null,
          user: null,
          isAuthenticated: false
        })
      },
      
      setUser: (user: User) => {
        set({ user })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
      onRehydrateStorage: () => (state) => {
        // Restore API token after rehydration
        if (state?.token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      }
    }
  )
)
