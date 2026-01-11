import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  CubeIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  ServerStackIcon,
  GlobeAltIcon
} from '@heroicons/react/24/outline'
import { dockerApi, npmApi } from '../services/api'
import clsx from 'clsx'

export default function Docker() {
  const [activeTab, setActiveTab] = useState<'containers' | 'networks' | 'npm'>('containers')

  const { data: containers, isLoading: containersLoading, refetch: refetchContainers } = useQuery({
    queryKey: ['docker-containers'],
    queryFn: () => dockerApi.getContainers().then(r => r.data)
  })

  const { data: networks, isLoading: networksLoading } = useQuery({
    queryKey: ['docker-networks'],
    queryFn: () => dockerApi.getNetworks().then(r => r.data)
  })

  const { data: npmHosts, isLoading: npmLoading } = useQuery({
    queryKey: ['npm-hosts'],
    queryFn: () => npmApi.getProxyHosts().then(r => r.data),
    enabled: activeTab === 'npm'
  })

  const stats = {
    running: containers?.filter((c: any) => c.status?.includes('Up') || c.state === 'running').length || 0,
    stopped: containers?.filter((c: any) => !c.status?.includes('Up') && c.state !== 'running').length || 0,
    total: containers?.length || 0,
    networks: networks?.length || 0
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary-500/20 p-2">
              <CubeIcon className="h-6 w-6 text-primary-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-sm text-dark-400">Total Containers</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-500/20 p-2">
              <PlayIcon className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.running}</p>
              <p className="text-sm text-dark-400">Running</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-500/20 p-2">
              <StopIcon className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.stopped}</p>
              <p className="text-sm text-dark-400">Stopped</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-500/20 p-2">
              <ServerStackIcon className="h-6 w-6 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.networks}</p>
              <p className="text-sm text-dark-400">Networks</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <div className="bg-dark-700 rounded-lg p-1 flex">
            {[
              { key: 'containers', label: 'Containers', icon: CubeIcon },
              { key: 'networks', label: 'Networks', icon: ServerStackIcon },
              { key: 'npm', label: 'Nginx Proxy Manager', icon: GlobeAltIcon },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeTab === key 
                    ? 'bg-primary-600 text-white' 
                    : 'text-dark-400 hover:text-white'
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
          
          <button 
            onClick={() => refetchContainers()}
            className="btn btn-secondary ml-auto"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </button>
        </div>

        {/* Containers Tab */}
        {activeTab === 'containers' && (
          containersLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-dark-700 rounded-lg"></div>
              ))}
            </div>
          ) : containers?.length > 0 ? (
            <div className="space-y-3">
              {containers.map((container: any) => {
                const isRunning = container.status?.includes('Up') || container.state === 'running'
                return (
                  <div 
                    key={container.id}
                    className={clsx(
                      'rounded-lg p-4 border transition-colors',
                      isRunning 
                        ? 'bg-green-500/10 border-green-500/30' 
                        : 'bg-dark-700/50 border-dark-600'
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div className={clsx(
                          'rounded-lg p-2',
                          isRunning ? 'bg-green-500/20' : 'bg-dark-600'
                        )}>
                          <CubeIcon className={clsx(
                            'h-6 w-6',
                            isRunning ? 'text-green-500' : 'text-dark-400'
                          )} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">
                            {container.name || container.names?.[0]?.replace('/', '')}
                          </h3>
                          <p className="text-xs text-dark-400 font-mono">
                            {container.image}
                          </p>
                        </div>
                      </div>
                      
                      <span className={clsx(
                        'text-xs font-medium px-2 py-1 rounded',
                        isRunning 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      )}>
                        {container.status || container.state}
                      </span>
                    </div>

                    {/* Port Mappings */}
                    {container.ports && container.ports.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-dark-600">
                        <p className="text-xs text-dark-400 mb-2">Port Mappings</p>
                        <div className="flex flex-wrap gap-2">
                          {container.ports.map((port: any, idx: number) => (
                            port.PublicPort && (
                              <span 
                                key={idx}
                                className="text-xs font-mono bg-dark-600 px-2 py-1 rounded"
                              >
                                {port.IP || '0.0.0.0'}:{port.PublicPort} → {port.PrivatePort}/{port.Type}
                              </span>
                            )
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Networks */}
                    {container.network_settings?.Networks && (
                      <div className="mt-2">
                        <div className="flex flex-wrap gap-2">
                          {Object.keys(container.network_settings.Networks).map((network) => (
                            <span 
                              key={network}
                              className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded"
                            >
                              {network}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-dark-400">
              <CubeIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No containers found</p>
              <p className="text-sm mt-1">Docker may not be running or accessible</p>
            </div>
          )
        )}

        {/* Networks Tab */}
        {activeTab === 'networks' && (
          networksLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-dark-700 rounded-lg"></div>
              ))}
            </div>
          ) : networks?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Driver</th>
                    <th>Scope</th>
                    <th>Subnet</th>
                    <th>Gateway</th>
                  </tr>
                </thead>
                <tbody>
                  {networks.map((network: any) => (
                    <tr key={network.id || network.Id}>
                      <td className="font-semibold text-white">
                        {network.name || network.Name}
                      </td>
                      <td>
                        <span className="badge badge-info">
                          {network.driver || network.Driver}
                        </span>
                      </td>
                      <td className="text-dark-400">
                        {network.scope || network.Scope}
                      </td>
                      <td className="font-mono text-dark-300">
                        {network.ipam?.config?.[0]?.subnet || 
                         network.IPAM?.Config?.[0]?.Subnet || '-'}
                      </td>
                      <td className="font-mono text-dark-300">
                        {network.ipam?.config?.[0]?.gateway || 
                         network.IPAM?.Config?.[0]?.Gateway || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-dark-400">
              <ServerStackIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No Docker networks found</p>
            </div>
          )
        )}

        {/* NPM Tab */}
        {activeTab === 'npm' && (
          npmLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-dark-700 rounded-lg"></div>
              ))}
            </div>
          ) : npmHosts?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Forward Host</th>
                    <th>Forward Port</th>
                    <th>SSL</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {npmHosts.map((host: any) => (
                    <tr key={host.id}>
                      <td className="font-semibold text-white">
                        {host.domain_names?.join(', ') || host.domain}
                      </td>
                      <td className="font-mono">
                        {host.forward_host}
                      </td>
                      <td className="font-mono">
                        {host.forward_port}
                      </td>
                      <td>
                        {host.ssl_forced || host.certificate_id ? (
                          <span className="badge badge-success">HTTPS</span>
                        ) : (
                          <span className="badge badge-warning">HTTP</span>
                        )}
                      </td>
                      <td>
                        <span className={clsx(
                          'badge',
                          host.enabled ? 'badge-success' : 'badge-danger'
                        )}>
                          {host.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-dark-400">
              <GlobeAltIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No Nginx Proxy Manager hosts found</p>
              <p className="text-sm mt-1">
                Configure NPM connection in settings or NPM may not be accessible
              </p>
            </div>
          )
        )}
      </div>
    </div>
  )
}
