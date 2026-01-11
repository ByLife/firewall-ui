import { useQuery } from '@tanstack/react-query'
import { 
  ShieldCheckIcon, 
  GlobeAltIcon, 
  ServerIcon, 
  CubeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline'
import { dashboardApi } from '../services/api'
import clsx from 'clsx'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats().then(r => r.data)
  })

  const { data: connectors, isLoading: connectorsLoading } = useQuery({
    queryKey: ['dashboard-connectors'],
    queryFn: () => dashboardApi.getConnectors().then(r => r.data)
  })

  const statCards = [
    {
      name: 'Firewall Rules',
      value: stats?.total_firewall_rules ?? '-',
      icon: ShieldCheckIcon,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10'
    },
    {
      name: 'Network Routes',
      value: stats?.total_routes ?? '-',
      icon: GlobeAltIcon,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10'
    },
    {
      name: 'Listening Ports',
      value: stats?.listening_ports ?? '-',
      icon: ServerIcon,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10'
    },
    {
      name: 'Docker Containers',
      value: stats?.docker_containers ?? '-',
      icon: CubeIcon,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10'
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'available':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'unavailable':
        return <XCircleIcon className="h-5 w-5 text-dark-500" />
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
      default:
        return <XCircleIcon className="h-5 w-5 text-dark-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <span className="badge badge-success">Available</span>
      case 'unavailable':
        return <span className="badge badge-gray">Unavailable</span>
      case 'error':
        return <span className="badge badge-danger">Error</span>
      default:
        return <span className="badge badge-gray">Unknown</span>
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center">
              <div className={clsx('rounded-lg p-3', stat.bgColor)}>
                <stat.icon className={clsx('h-6 w-6', stat.color)} />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-dark-400">{stat.name}</p>
                <p className="text-2xl font-semibold text-white">
                  {statsLoading ? (
                    <span className="animate-pulse">...</span>
                  ) : (
                    stat.value
                  )}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Connectors Status */}
      <div className="card">
        <h2 className="card-header">System Connectors</h2>
        
        {connectorsLoading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-dark-700 rounded"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {connectors?.map((connector: any) => (
              <div
                key={connector.name}
                className={clsx(
                  'flex items-center justify-between p-4 rounded-lg border',
                  connector.status === 'available'
                    ? 'border-green-900/50 bg-green-900/10'
                    : 'border-dark-700 bg-dark-800'
                )}
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(connector.status)}
                  <div>
                    <p className="font-medium text-white capitalize">{connector.name}</p>
                    <p className="text-xs text-dark-400">
                      {connector.type}
                      {connector.version && ` • v${connector.version}`}
                    </p>
                  </div>
                </div>
                {getStatusBadge(connector.status)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="card-header">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-4">
            <a href="/firewall" className="btn btn-secondary text-center">
              Manage Firewall
            </a>
            <a href="/network" className="btn btn-secondary text-center">
              View Routes
            </a>
            <a href="/ports" className="btn btn-secondary text-center">
              Scan Ports
            </a>
            <a href="/docker" className="btn btn-secondary text-center">
              Docker Status
            </a>
          </div>
        </div>

        <div className="card">
          <h2 className="card-header">System Information</h2>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-dark-400">Firewall Backend</span>
              <span className="text-white">
                {connectors?.find((c: any) => c.type === 'firewall' && c.status === 'available')?.name || 'None'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-dark-400">Docker</span>
              <span className="text-white">
                {connectors?.find((c: any) => c.name === 'docker')?.status === 'available' 
                  ? 'Connected' 
                  : 'Not Available'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-dark-400">Nginx Proxy Manager</span>
              <span className="text-white">
                {connectors?.find((c: any) => c.name === 'nginx-proxy-manager')?.status === 'available' 
                  ? 'Connected' 
                  : 'Not Configured'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
