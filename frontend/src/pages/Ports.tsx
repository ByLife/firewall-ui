import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ServerStackIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  GlobeAltIcon,
  LockClosedIcon,
  LockOpenIcon,
  ShieldExclamationIcon,
  NoSymbolIcon,
  SignalIcon
} from '@heroicons/react/24/outline'
import { Dialog } from '@headlessui/react'
import toast from 'react-hot-toast'
import { portsApi, networkApi } from '../services/api'
import clsx from 'clsx'

interface PortInfo {
  port: number
  protocol: string
  address?: string
  ip?: string
  process?: string
  program?: string
  pid?: number
  interface?: string
  is_public?: boolean
  state?: string
}

interface InterfaceGroup {
  interface: string
  state?: string
  ipv4?: Array<{ address: string; prefix: number }>
  ipv6?: Array<{ address: string; prefix: number }>
  ports: PortInfo[]
  port_count: number
}

export default function Ports() {
  const [scanModalOpen, setScanModalOpen] = useState(false)
  const [blockModalOpen, setBlockModalOpen] = useState(false)
  const [selectedPort, setSelectedPort] = useState<PortInfo | null>(null)
  const [viewMode, setViewMode] = useState<'list' | 'interface'>('list')
  const queryClient = useQueryClient()

  const { data: listeningPorts, isLoading: portsLoading, refetch } = useQuery({
    queryKey: ['listening-ports'],
    queryFn: () => portsApi.getListening().then(r => r.data)
  })

  const { data: portsByInterface, isLoading: interfaceLoading } = useQuery({
    queryKey: ['ports-by-interface'],
    queryFn: () => portsApi.getByInterface().then(r => r.data),
    enabled: viewMode === 'interface'
  })

  const { data: interfaces } = useQuery({
    queryKey: ['network-interfaces'],
    queryFn: () => networkApi.getInterfaces().then(r => r.data)
  })

  const blockMutation = useMutation({
    mutationFn: ({ port, protocol, iface }: { port: number; protocol: string; iface?: string }) =>
      portsApi.blockPort(port, protocol, iface),
    onSuccess: () => {
      toast.success('Port blocked successfully')
      setBlockModalOpen(false)
      setSelectedPort(null)
      queryClient.invalidateQueries({ queryKey: ['listening-ports'] })
      queryClient.invalidateQueries({ queryKey: ['ports-by-interface'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to block port')
    }
  })

  const stats = {
    total: listeningPorts?.length || 0,
    tcp: listeningPorts?.filter((p: PortInfo) => p.protocol === 'tcp').length || 0,
    udp: listeningPorts?.filter((p: PortInfo) => p.protocol === 'udp').length || 0,
    public: listeningPorts?.filter((p: PortInfo) => 
      p.address === '0.0.0.0' || p.address === '::' || p.address === '*' || p.is_public
    ).length || 0
  }

  const handleBlockPort = (port: PortInfo) => {
    setSelectedPort(port)
    setBlockModalOpen(true)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary-500/20 p-2">
              <ServerStackIcon className="h-6 w-6 text-primary-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-sm text-dark-400">Total Ports</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/20 p-2">
              <LockClosedIcon className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.tcp}</p>
              <p className="text-sm text-dark-400">TCP Ports</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-green-500/20 p-2">
              <GlobeAltIcon className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.udp}</p>
              <p className="text-sm text-dark-400">UDP Ports</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-yellow-500/20 p-2">
              <LockOpenIcon className="h-6 w-6 text-yellow-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.public}</p>
              <p className="text-sm text-dark-400">Public Listening</p>
            </div>
          </div>
        </div>
      </div>

      {/* Listening Ports Table */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h2 className="card-header mb-0">Listening Ports</h2>
          
          <div className="flex gap-2">
            {/* View Mode Toggle */}
            <div className="flex bg-dark-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('list')}
                className={clsx(
                  'px-3 py-1 text-sm rounded transition-colors',
                  viewMode === 'list' 
                    ? 'bg-primary-600 text-white' 
                    : 'text-dark-300 hover:text-white'
                )}
              >
                List
              </button>
              <button
                onClick={() => setViewMode('interface')}
                className={clsx(
                  'px-3 py-1 text-sm rounded transition-colors',
                  viewMode === 'interface' 
                    ? 'bg-primary-600 text-white' 
                    : 'text-dark-300 hover:text-white'
                )}
              >
                By Interface
              </button>
            </div>
            
            <button 
              onClick={() => refetch()}
              className="btn btn-secondary"
            >
              <ArrowPathIcon className="h-4 w-4" />
            </button>
            <button 
              onClick={() => setScanModalOpen(true)}
              className="btn btn-primary"
            >
              <MagnifyingGlassIcon className="h-4 w-4 mr-1" />
              Port Scan
            </button>
          </div>
        </div>

        {viewMode === 'list' ? (
          // List View
          portsLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-dark-700 rounded"></div>
              ))}
            </div>
          ) : listeningPorts?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>Port</th>
                    <th>Protocol</th>
                    <th>Address</th>
                    <th>Interface</th>
                    <th>Process</th>
                    <th>PID</th>
                    <th>State</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {listeningPorts.map((port: PortInfo, idx: number) => (
                    <tr key={idx}>
                      <td className="font-mono text-white font-semibold">
                        {port.port}
                      </td>
                      <td>
                        <span className={clsx(
                          'badge',
                          port.protocol === 'tcp' ? 'badge-primary' : 'badge-info'
                        )}>
                          {port.protocol?.toUpperCase()}
                        </span>
                      </td>
                      <td className="font-mono">
                        <span className={clsx(
                          port.address === '0.0.0.0' || port.address === '::' || port.address === '*' || port.is_public
                            ? 'text-yellow-400'
                            : 'text-dark-300'
                        )}>
                          {port.address || port.ip || '*'}
                        </span>
                      </td>
                      <td>
                        <span className={clsx(
                          'badge',
                          port.interface === 'all' ? 'badge-warning' : 'badge-secondary'
                        )}>
                          {port.interface || 'unknown'}
                        </span>
                      </td>
                      <td className="text-white">
                        {port.process || port.program || '-'}
                      </td>
                      <td className="font-mono text-dark-400">
                        {port.pid || '-'}
                      </td>
                      <td>
                        <span className="badge badge-success">
                          {port.state || 'LISTEN'}
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => handleBlockPort(port)}
                          className="btn btn-sm btn-danger"
                          title="Block this port"
                        >
                          <NoSymbolIcon className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-dark-400">
              <ServerStackIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No listening ports found</p>
            </div>
          )
        ) : (
          // Interface View
          interfaceLoading ? (
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-dark-700 rounded"></div>
              ))}
            </div>
          ) : portsByInterface?.length > 0 ? (
            <div className="space-y-4">
              {portsByInterface.map((group: InterfaceGroup) => (
                <div key={group.interface} className="border border-dark-600 rounded-lg overflow-hidden">
                  {/* Interface Header */}
                  <div className="bg-dark-700 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <SignalIcon className={clsx(
                        'h-5 w-5',
                        group.state === 'UP' ? 'text-green-400' : 'text-dark-400'
                      )} />
                      <div>
                        <span className="font-semibold text-white">{group.interface}</span>
                        {group.state && (
                          <span className={clsx(
                            'ml-2 text-xs',
                            group.state === 'UP' ? 'text-green-400' : 'text-dark-400'
                          )}>
                            ({group.state})
                          </span>
                        )}
                      </div>
                      {group.ipv4?.map((ip, i) => (
                        <span key={i} className="text-xs font-mono text-dark-400">
                          {ip.address}/{ip.prefix}
                        </span>
                      ))}
                    </div>
                    <span className="badge badge-primary">
                      {group.port_count} port{group.port_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                  
                  {/* Ports List */}
                  {group.ports.length > 0 ? (
                    <div className="divide-y divide-dark-700">
                      {group.ports.map((port: PortInfo, idx: number) => (
                        <div key={idx} className="px-4 py-2 flex items-center justify-between hover:bg-dark-700/50">
                          <div className="flex items-center gap-4">
                            <span className="font-mono font-bold text-white w-16">{port.port}</span>
                            <span className={clsx(
                              'badge',
                              port.protocol === 'tcp' ? 'badge-primary' : 'badge-info'
                            )}>
                              {port.protocol?.toUpperCase()}
                            </span>
                            <span className="text-sm text-dark-300">
                              {port.process || port.program || 'unknown process'}
                            </span>
                            {port.pid && (
                              <span className="text-xs font-mono text-dark-500">PID: {port.pid}</span>
                            )}
                          </div>
                          <button
                            onClick={() => handleBlockPort({ ...port, interface: group.interface })}
                            className="btn btn-sm btn-danger"
                            title={`Block port ${port.port} on ${group.interface}`}
                          >
                            <NoSymbolIcon className="h-4 w-4 mr-1" />
                            Block
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="px-4 py-6 text-center text-dark-500">
                      No ports listening on this interface
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-dark-400">
              <ServerStackIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No listening ports found</p>
            </div>
          )
        )}
      </div>

      {/* Well-Known Ports Reference */}
      <div className="card">
        <h2 className="card-header">Well-Known Ports Reference</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {[
            { port: 22, name: 'SSH' },
            { port: 80, name: 'HTTP' },
            { port: 443, name: 'HTTPS' },
            { port: 3306, name: 'MySQL' },
            { port: 5432, name: 'PostgreSQL' },
            { port: 6379, name: 'Redis' },
            { port: 27017, name: 'MongoDB' },
            { port: 8080, name: 'Alt HTTP' },
            { port: 3000, name: 'Node.js' },
            { port: 5000, name: 'Flask' },
            { port: 8000, name: 'Django' },
            { port: 9000, name: 'PHP-FPM' },
          ].map(({ port, name }) => {
            const isListening = listeningPorts?.some((p: any) => p.port === port)
            return (
              <div 
                key={port}
                className={clsx(
                  'rounded-lg p-2 text-center text-sm transition-colors',
                  isListening 
                    ? 'bg-green-500/20 border border-green-500/30' 
                    : 'bg-dark-700/50'
                )}
              >
                <span className="font-mono font-bold text-white">{port}</span>
                <span className="text-dark-400 ml-1">({name})</span>
                {isListening && (
                  <span className="ml-1 text-green-400">●</span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Port Scan Modal */}
      <PortScanModal open={scanModalOpen} onClose={() => setScanModalOpen(false)} />
      
      {/* Block Port Modal */}
      <BlockPortModal 
        open={blockModalOpen} 
        onClose={() => { setBlockModalOpen(false); setSelectedPort(null); }}
        port={selectedPort}
        interfaces={interfaces || []}
        onBlock={(port, protocol, iface) => blockMutation.mutate({ port, protocol, iface })}
        isBlocking={blockMutation.isPending}
      />
    </div>
  )
}

function PortScanModal({ open, onClose }: { open: boolean, onClose: () => void }) {
  const [target, setTarget] = useState('')
  const [portRange, setPortRange] = useState('1-1000')
  const [scanResults, setScanResults] = useState<any>(null)

  const scanMutation = useMutation({
    mutationFn: ({ target, port_range }: { target: string, port_range: string }) => 
      portsApi.scanPorts(target, port_range),
    onSuccess: (response) => {
      setScanResults(response.data)
      toast.success('Port scan completed')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Port scan failed')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!target) {
      toast.error('Target IP is required')
      return
    }

    setScanResults(null)
    scanMutation.mutate({ target, port_range: portRange })
  }

  const handleClose = () => {
    onClose()
    setScanResults(null)
  }

  return (
    <Dialog open={open} onClose={handleClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-lg card max-h-[80vh] overflow-y-auto">
          <Dialog.Title className="text-lg font-semibold text-white mb-4">
            Port Scanner
          </Dialog.Title>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Target IP Address</label>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="input"
                placeholder="e.g., 192.168.1.1 or localhost"
              />
            </div>

            <div>
              <label className="label">Port Range</label>
              <input
                type="text"
                value={portRange}
                onChange={(e) => setPortRange(e.target.value)}
                className="input"
                placeholder="e.g., 1-1000 or 80,443,8080"
              />
              <p className="text-xs text-dark-400 mt-1">
                Format: start-end or comma-separated ports
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button type="button" onClick={handleClose} className="btn btn-secondary">
                Close
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={scanMutation.isPending}
              >
                {scanMutation.isPending ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  'Start Scan'
                )}
              </button>
            </div>
          </form>

          {/* Scan Results */}
          {scanResults && (
            <div className="mt-6 border-t border-dark-700 pt-4">
              <h3 className="text-sm font-semibold text-white mb-3">
                Scan Results for {scanResults.target}
              </h3>
              
              {scanResults.open_ports?.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-sm text-dark-400 mb-2">
                    Found {scanResults.open_ports.length} open ports
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {scanResults.open_ports.map((port: any) => (
                      <div 
                        key={port.port}
                        className="bg-green-500/20 rounded-lg p-2 text-center"
                      >
                        <span className="font-mono font-bold text-white">
                          {port.port}
                        </span>
                        {port.service && (
                          <span className="text-xs text-dark-400 block">
                            {port.service}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-dark-400">
                  No open ports found in the specified range
                </p>
              )}
              
              {scanResults.scan_time && (
                <p className="text-xs text-dark-500 mt-3">
                  Scan completed in {scanResults.scan_time}s
                </p>
              )}
            </div>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}

interface BlockPortModalProps {
  open: boolean
  onClose: () => void
  port: PortInfo | null
  interfaces: Array<{ name: string; state?: string }>
  onBlock: (port: number, protocol: string, iface?: string) => void
  isBlocking: boolean
}

function BlockPortModal({ open, onClose, port, interfaces, onBlock, isBlocking }: BlockPortModalProps) {
  const [selectedInterface, setSelectedInterface] = useState<string>('all')
  const [protocol, setProtocol] = useState<string>('tcp')

  // Update state when port changes
  useState(() => {
    if (port) {
      setProtocol(port.protocol || 'tcp')
      setSelectedInterface(port.interface || 'all')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!port) return
    
    onBlock(
      port.port,
      protocol,
      selectedInterface !== 'all' ? selectedInterface : undefined
    )
  }

  if (!port) return null

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md card">
          <Dialog.Title className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <ShieldExclamationIcon className="h-6 w-6 text-red-500" />
            Block Port {port.port}
          </Dialog.Title>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="bg-dark-700 rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-dark-400">Port</span>
                <span className="font-mono text-white font-bold">{port.port}</span>
              </div>
              {port.process && (
                <div className="flex justify-between">
                  <span className="text-dark-400">Process</span>
                  <span className="text-white">{port.process}</span>
                </div>
              )}
              {port.pid && (
                <div className="flex justify-between">
                  <span className="text-dark-400">PID</span>
                  <span className="font-mono text-dark-300">{port.pid}</span>
                </div>
              )}
            </div>

            <div>
              <label className="label">Protocol</label>
              <select
                value={protocol}
                onChange={(e) => setProtocol(e.target.value)}
                className="input"
              >
                <option value="tcp">TCP</option>
                <option value="udp">UDP</option>
              </select>
            </div>

            <div>
              <label className="label">Interface</label>
              <select
                value={selectedInterface}
                onChange={(e) => setSelectedInterface(e.target.value)}
                className="input"
              >
                <option value="all">All Interfaces</option>
                {interfaces
                  .filter(iface => iface.name !== 'lo')
                  .map(iface => (
                    <option key={iface.name} value={iface.name}>
                      {iface.name} {iface.state ? `(${iface.state})` : ''}
                    </option>
                  ))
                }
              </select>
              <p className="text-xs text-dark-400 mt-1">
                Block only on a specific interface or all interfaces
              </p>
            </div>

            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">
                <strong>Warning:</strong> Blocking this port will prevent incoming connections.
                {port.process && ` This may affect the "${port.process}" service.`}
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-danger"
                disabled={isBlocking}
              >
                {isBlocking ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
                    Blocking...
                  </>
                ) : (
                  <>
                    <NoSymbolIcon className="h-4 w-4 mr-1" />
                    Block Port
                  </>
                )}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}