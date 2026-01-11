import axios from 'axios'
import toast from 'react-hot-toast'

// API URL configurable via environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Get token from localStorage (zustand persist)
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        if (state?.token) {
          config.headers.Authorization = `Bearer ${state.token}`
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - only redirect if not on login page
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('auth-storage')
        window.location.href = '/login'
        toast.error('Session expired. Please login again.')
      }
    } else if (error.response?.status === 403) {
      toast.error('Access denied')
    } else if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.')
    }
    
    return Promise.reject(error)
  }
)

// ============ Auth API ============
export const authApi = {
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  getMe: () => api.get('/auth/me'),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
}

// ============ Dashboard API ============
export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
  getConnectors: () => api.get('/dashboard/connectors'),
  getOverview: () => api.get('/dashboard/overview')
}

// ============ Firewall API ============
export const firewallApi = {
  getStatus: () => api.get('/firewall/status'),
  getBackends: () => api.get('/firewall/backends'),
  
  // UFW
  getUfwStatus: () => api.get('/firewall/ufw/status'),
  getUfwRules: () => api.get('/firewall/ufw/rules'),
  addUfwRule: (rule: any) => api.post('/firewall/ufw/rules', rule),
  deleteUfwRule: (ruleId: string) => api.delete(`/firewall/ufw/rules/${ruleId}`),
  enableUfw: () => api.post('/firewall/ufw/enable'),
  disableUfw: () => api.post('/firewall/ufw/disable'),
  getUfwApps: () => api.get('/firewall/ufw/apps'),
  
  // iptables
  getIptablesStatus: () => api.get('/firewall/iptables/status'),
  getIptablesRules: (table?: string) => api.get('/firewall/iptables/rules', { params: { table } }),
  addIptablesRule: (rule: any) => api.post('/firewall/iptables/rules', rule),
  deleteIptablesRule: (ruleId: string) => api.delete(`/firewall/iptables/rules/${encodeURIComponent(ruleId)}`),
  
  // firewalld
  getFirewalldStatus: () => api.get('/firewall/firewalld/status'),
  getFirewalldZones: () => api.get('/firewall/firewalld/zones'),
  getFirewalldRules: () => api.get('/firewall/firewalld/rules'),
  addFirewalldRule: (rule: any) => api.post('/firewall/firewalld/rules', rule),
  
  // nftables
  getNftablesStatus: () => api.get('/firewall/nftables/status'),
  getNftablesRules: () => api.get('/firewall/nftables/rules'),
  getNftablesTables: () => api.get('/firewall/nftables/tables')
}

// ============ Network API ============
export const networkApi = {
  getStatus: () => api.get('/network/status'),
  getInterfaces: () => api.get('/network/interfaces'),
  getInterfaceStats: (name: string) => api.get(`/network/interfaces/${name}/stats`),
  getRoutes: (table?: string) => api.get('/network/routes', { params: { table } }),
  addRoute: (route: any) => api.post('/network/routes', route),
  deleteRoute: (route: any) =>
    api.delete('/network/routes', { params: route }),
  getIpRules: () => api.get('/network/rules'),
  getRules: () => api.get('/network/rules'),
  addRule: (rule: any) => api.post('/network/rules', rule),
  deleteRule: (priority?: number, fromAddr?: string, toAddr?: string, table?: string) =>
    api.delete('/network/rules', { params: { priority, from_addr: fromAddr, to_addr: toAddr, table } }),
  getArp: () => api.get('/network/arp'),
  getGraph: () => api.get('/network/graph')
}

// ============ Ports API ============
export const portsApi = {
  getListening: () => api.get('/ports/listening'),
  getPublicIp: () => api.get('/ports/public-ip'),
  scanPorts: (target: string, portRange: string) => api.post('/ports/scan', { target, port_range: portRange }),
  scanPublicPorts: (ports?: number[]) => api.post('/ports/scan-public', { ports }),
  getExposed: () => api.get('/ports/exposed'),
  getSummary: () => api.get('/ports/summary'),
  getByInterface: () => api.get('/ports/by-interface'),
  blockPort: (port: number, protocol: string = 'tcp', iface?: string) => 
    api.post('/ports/block', null, { params: { port, protocol, interface: iface } })
}

// ============ Docker API ============
export const dockerApi = {
  getStatus: () => api.get('/docker/status'),
  getContainers: (all?: boolean) => api.get('/docker/containers', { params: { all } }),
  getContainer: (id: string) => api.get(`/docker/containers/${id}`),
  getContainerLogs: (id: string, tail?: number) => api.get(`/docker/containers/${id}/logs`, { params: { tail } }),
  getContainerPorts: (id: string) => api.get(`/docker/containers/${id}/ports`),
  getNetworks: () => api.get('/docker/networks'),
  getPorts: () => api.get('/docker/ports')
}

// ============ NPM API ============
export const npmApi = {
  getStatus: () => api.get('/npm/status'),
  getProxyHosts: () => api.get('/npm/proxy-hosts'),
  getProxyHost: (id: number) => api.get(`/npm/proxy-hosts/${id}`),
  createProxyHost: (host: any) => api.post('/npm/proxy-hosts', host),
  deleteProxyHost: (id: number) => api.delete(`/npm/proxy-hosts/${id}`),
  getStreams: () => api.get('/npm/streams'),
  createStream: (stream: any) => api.post('/npm/streams', stream),
  getCertificates: () => api.get('/npm/certificates'),
  getPorts: () => api.get('/npm/ports')
}

// ============ Users API ============
export const usersApi = {
  getAll: () => api.get('/users'),
  getUsers: () => api.get('/users'),
  get: (id: number) => api.get(`/users/${id}`),
  getUser: (id: number) => api.get(`/users/${id}`),
  create: (user: any) => api.post('/users', user),
  createUser: (user: any) => api.post('/users', user),
  update: (id: number, user: any) => api.put(`/users/${id}`, user),
  updateUser: (id: number, user: any) => api.put(`/users/${id}`, user),
  delete: (id: number) => api.delete(`/users/${id}`),
  deleteUser: (id: number) => api.delete(`/users/${id}`),
  resetPassword: (id: number, newPassword: string) => api.post(`/users/${id}/reset-password`, null, { params: { new_password: newPassword } })
}

// ============ Audit API ============
export const auditApi = {
  getLogs: (params?: any) => api.get('/audit', { params }),
  getActions: () => api.get('/audit/actions'),
  getResourceTypes: () => api.get('/audit/resource-types'),
  getSummary: (days?: number) => api.get('/audit/summary', { params: { days } })
}
