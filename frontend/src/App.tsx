import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Firewall from './pages/Firewall'
import Network from './pages/Network'
import Ports from './pages/Ports'
import Docker from './pages/Docker'
import Users from './pages/Users'
import Audit from './pages/Audit'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/firewall" element={<Firewall />} />
                <Route path="/network" element={<Network />} />
                <Route path="/ports" element={<Ports />} />
                <Route path="/docker" element={<Docker />} />
                <Route path="/users" element={<Users />} />
                <Route path="/audit" element={<Audit />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
