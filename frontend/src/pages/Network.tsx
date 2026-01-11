import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  Node,
  Edge,
  MarkerType
} from 'reactflow'
import 'reactflow/dist/style.css'
import { 
  GlobeAltIcon,
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  SignalIcon
} from '@heroicons/react/24/outline'
import { Dialog } from '@headlessui/react'
import toast from 'react-hot-toast'
import { networkApi } from '../services/api'
import clsx from 'clsx'

export default function Network() {
  const [addRouteOpen, setAddRouteOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table')
  
  const { data: interfaces, isLoading: interfacesLoading } = useQuery({
    queryKey: ['interfaces'],
    queryFn: () => networkApi.getInterfaces().then(r => r.data)
  })

  const { data: routes, isLoading: routesLoading, refetch: refetchRoutes } = useQuery({
    queryKey: ['routes'],
    queryFn: () => networkApi.getRoutes().then(r => r.data)
  })

  const { data: ipRules, isLoading: ipRulesLoading } = useQuery({
    queryKey: ['ip-rules'],
    queryFn: () => networkApi.getIpRules().then(r => r.data)
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Network Interfaces */}
      <div className="card">
        <h2 className="card-header">Network Interfaces</h2>
        
        {interfacesLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-dark-700 rounded-lg"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {interfaces?.map((iface: any) => (
              <div 
                key={iface.name}
                className={clsx(
                  'rounded-lg p-4 border transition-colors',
                  iface.state === 'UP' 
                    ? 'bg-green-500/10 border-green-500/30' 
                    : 'bg-dark-700/50 border-dark-600'
                )}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={clsx(
                    'rounded-lg p-2',
                    iface.state === 'UP' ? 'bg-green-500/20' : 'bg-dark-600'
                  )}>
                    <SignalIcon className={clsx(
                      'h-5 w-5',
                      iface.state === 'UP' ? 'text-green-500' : 'text-dark-400'
                    )} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{iface.name}</h3>
                    <p className="text-xs text-dark-400">{iface.type || 'ethernet'}</p>
                  </div>
                  <span className={clsx(
                    'ml-auto text-xs font-medium px-2 py-1 rounded',
                    iface.state === 'UP' 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-dark-600 text-dark-400'
                  )}>
                    {iface.state}
                  </span>
                </div>
                
                <div className="space-y-1 text-sm">
                  {iface.addresses?.map((addr: any, idx: number) => (
                    <div key={idx} className="flex justify-between">
                      <span className="text-dark-400">{addr.family}</span>
                      <span className="font-mono text-white">{addr.address}/{addr.prefixlen}</span>
                    </div>
                  ))}
                  {iface.mac && (
                    <div className="flex justify-between">
                      <span className="text-dark-400">MAC</span>
                      <span className="font-mono text-dark-300">{iface.mac}</span>
                    </div>
                  )}
                  {iface.mtu && (
                    <div className="flex justify-between">
                      <span className="text-dark-400">MTU</span>
                      <span className="font-mono text-dark-300">{iface.mtu}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Routes Section */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h2 className="card-header mb-0">Routing Table</h2>
          
          <div className="flex gap-2">
            <div className="bg-dark-700 rounded-lg p-1 flex">
              <button
                onClick={() => setViewMode('table')}
                className={clsx(
                  'px-3 py-1 rounded text-sm font-medium transition-colors',
                  viewMode === 'table' 
                    ? 'bg-primary-600 text-white' 
                    : 'text-dark-400 hover:text-white'
                )}
              >
                Table
              </button>
              <button
                onClick={() => setViewMode('graph')}
                className={clsx(
                  'px-3 py-1 rounded text-sm font-medium transition-colors',
                  viewMode === 'graph' 
                    ? 'bg-primary-600 text-white' 
                    : 'text-dark-400 hover:text-white'
                )}
              >
                Graph
              </button>
            </div>
            
            <button 
              onClick={() => refetchRoutes()}
              className="btn btn-secondary"
            >
              <ArrowPathIcon className="h-4 w-4" />
            </button>
            
            <button 
              onClick={() => setAddRouteOpen(true)}
              className="btn btn-primary"
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Route
            </button>
          </div>
        </div>

        {routesLoading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 bg-dark-700 rounded"></div>
            ))}
          </div>
        ) : viewMode === 'table' ? (
          <RoutesTable routes={routes || []} />
        ) : (
          <RoutesGraph routes={routes || []} interfaces={interfaces || []} />
        )}
      </div>

      {/* IP Rules */}
      <div className="card">
        <h2 className="card-header">IP Rules (Policy Routing)</h2>
        
        {ipRulesLoading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-dark-700 rounded"></div>
            ))}
          </div>
        ) : ipRules?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>From</th>
                  <th>To</th>
                  <th>FWMark</th>
                  <th>Table</th>
                </tr>
              </thead>
              <tbody>
                {ipRules.map((rule: any, idx: number) => (
                  <tr key={idx}>
                    <td className="font-mono">{rule.priority}</td>
                    <td className="font-mono text-white">{rule.src || 'all'}</td>
                    <td className="font-mono">{rule.dst || 'all'}</td>
                    <td className="font-mono text-dark-400">{rule.fwmark || '-'}</td>
                    <td>
                      <span className="badge badge-info">{rule.table}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-dark-400">
            <GlobeAltIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No IP rules configured</p>
          </div>
        )}
      </div>

      {/* Add Route Modal */}
      <AddRouteModal open={addRouteOpen} onClose={() => setAddRouteOpen(false)} />
    </div>
  )
}

function RoutesTable({ routes }: { routes: any[] }) {
  const queryClient = useQueryClient()

  const deleteRouteMutation = useMutation({
    mutationFn: (route: any) => networkApi.deleteRoute(route),
    onSuccess: () => {
      toast.success('Route deleted')
      queryClient.invalidateQueries({ queryKey: ['routes'] })
    },
    onError: () => toast.error('Failed to delete route')
  })

  if (!routes.length) {
    return (
      <div className="text-center py-8 text-dark-400">
        <GlobeAltIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No routes found</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>Destination</th>
            <th>Gateway</th>
            <th>Interface</th>
            <th>Protocol</th>
            <th>Scope</th>
            <th>Metric</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {routes.map((route: any, idx: number) => (
            <tr key={idx}>
              <td className="font-mono text-white">
                {route.dst || route.destination || 'default'}
              </td>
              <td className="font-mono">
                {route.gateway || route.via || '-'}
              </td>
              <td>
                <span className="badge badge-primary">{route.dev || route.interface}</span>
              </td>
              <td className="text-dark-400">{route.protocol || '-'}</td>
              <td className="text-dark-400">{route.scope || '-'}</td>
              <td className="font-mono text-dark-400">{route.metric || '-'}</td>
              <td>
                <button
                  onClick={() => deleteRouteMutation.mutate({
                    destination: route.dst || route.destination,
                    gateway: route.gateway || route.via,
                    interface: route.dev || route.interface
                  })}
                  disabled={deleteRouteMutation.isPending}
                  className="text-dark-400 hover:text-red-500 transition-colors"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RoutesGraph({ routes, interfaces }: { routes: any[], interfaces: any[] }) {
  const { nodes, edges } = useMemo(() => {
    const nodeList: Node[] = []
    const edgeList: Edge[] = []
    
    // Add host node at center
    nodeList.push({
      id: 'host',
      data: { label: 'This Host' },
      position: { x: 400, y: 200 },
      style: {
        background: '#3b82f6',
        color: 'white',
        border: '2px solid #1d4ed8',
        borderRadius: '8px',
        padding: '10px 20px',
        fontWeight: 'bold'
      }
    })

    // Add interface nodes
    interfaces.forEach((iface: any, idx: number) => {
      const angle = (idx / interfaces.length) * Math.PI * 2
      const radius = 150
      
      nodeList.push({
        id: `iface-${iface.name}`,
        data: { 
          label: (
            <div className="text-center">
              <div className="font-bold">{iface.name}</div>
              <div className="text-xs opacity-75">{iface.state}</div>
            </div>
          )
        },
        position: { 
          x: 400 + Math.cos(angle) * radius, 
          y: 200 + Math.sin(angle) * radius 
        },
        style: {
          background: iface.state === 'UP' ? '#10b981' : '#6b7280',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '8px 12px'
        }
      })

      edgeList.push({
        id: `host-to-${iface.name}`,
        source: 'host',
        target: `iface-${iface.name}`,
        animated: iface.state === 'UP',
        style: { stroke: iface.state === 'UP' ? '#10b981' : '#6b7280' }
      })
    })

    // Add gateway/destination nodes from routes
    const gateways = new Set<string>()
    routes.forEach((route: any) => {
      const gw = route.gateway || route.via
      if (gw && gw !== '-') {
        gateways.add(gw)
      }
    })

    Array.from(gateways).forEach((gw: string, idx: number) => {
      const angle = (idx / gateways.size) * Math.PI * 2
      const radius = 300
      
      nodeList.push({
        id: `gw-${gw}`,
        data: { label: gw },
        position: { 
          x: 400 + Math.cos(angle) * radius, 
          y: 200 + Math.sin(angle) * radius 
        },
        style: {
          background: '#8b5cf6',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '8px 12px'
        }
      })

      // Connect gateway to interface
      routes.forEach((route: any) => {
        if ((route.gateway || route.via) === gw) {
          const iface = route.dev || route.interface
          edgeList.push({
            id: `${iface}-to-${gw}`,
            source: `iface-${iface}`,
            target: `gw-${gw}`,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#8b5cf6' },
            label: route.dst || route.destination || 'default'
          })
        }
      })
    })

    return { nodes: nodeList, edges: edgeList }
  }, [routes, interfaces])

  return (
    <div className="h-96 bg-dark-800 rounded-lg border border-dark-700">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#374151" gap={16} />
        <Controls className="bg-dark-700 border-dark-600 fill-white" />
        <MiniMap 
          nodeColor={(n) => n.style?.background as string || '#6b7280'} 
          className="bg-dark-800 border-dark-700"
        />
      </ReactFlow>
    </div>
  )
}

function AddRouteModal({ open, onClose }: { open: boolean, onClose: () => void }) {
  const [destination, setDestination] = useState('')
  const [gateway, setGateway] = useState('')
  const [iface, setIface] = useState('')
  const [metric, setMetric] = useState('')
  
  const queryClient = useQueryClient()

  const { data: interfaces } = useQuery({
    queryKey: ['interfaces'],
    queryFn: () => networkApi.getInterfaces().then(r => r.data)
  })

  const addRouteMutation = useMutation({
    mutationFn: (route: any) => networkApi.addRoute(route),
    onSuccess: () => {
      toast.success('Route added successfully')
      queryClient.invalidateQueries({ queryKey: ['routes'] })
      onClose()
      resetForm()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add route')
    }
  })

  const resetForm = () => {
    setDestination('')
    setGateway('')
    setIface('')
    setMetric('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!destination || !iface) {
      toast.error('Destination and interface are required')
      return
    }

    addRouteMutation.mutate({
      destination,
      gateway: gateway || undefined,
      interface: iface,
      metric: metric ? parseInt(metric) : undefined
    })
  }

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md card">
          <Dialog.Title className="text-lg font-semibold text-white mb-4">
            Add Route
          </Dialog.Title>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Destination (CIDR)</label>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="input"
                placeholder="e.g., 10.0.0.0/8 or default"
              />
            </div>

            <div>
              <label className="label">Gateway (optional)</label>
              <input
                type="text"
                value={gateway}
                onChange={(e) => setGateway(e.target.value)}
                className="input"
                placeholder="e.g., 192.168.1.1"
              />
            </div>

            <div>
              <label className="label">Interface</label>
              <select 
                value={iface} 
                onChange={(e) => setIface(e.target.value)}
                className="input"
              >
                <option value="">Select interface...</option>
                {interfaces?.map((i: any) => (
                  <option key={i.name} value={i.name}>{i.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Metric (optional)</label>
              <input
                type="number"
                value={metric}
                onChange={(e) => setMetric(e.target.value)}
                className="input"
                placeholder="e.g., 100"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={addRouteMutation.isPending}
              >
                {addRouteMutation.isPending ? 'Adding...' : 'Add Route'}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
