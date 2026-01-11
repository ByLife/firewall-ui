import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ShieldCheckIcon, 
  PlusIcon, 
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'
import { Dialog } from '@headlessui/react'
import toast from 'react-hot-toast'
import { firewallApi } from '../services/api'
import clsx from 'clsx'

type FirewallBackend = 'ufw' | 'iptables' | 'firewalld' | 'nftables'

export default function Firewall() {
  const [selectedBackend, setSelectedBackend] = useState<FirewallBackend>('ufw')
  const [addRuleOpen, setAddRuleOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: backends } = useQuery({
    queryKey: ['firewall-backends'],
    queryFn: () => firewallApi.getBackends().then(r => r.data)
  })

  const { data: status } = useQuery({
    queryKey: ['firewall-status'],
    queryFn: () => firewallApi.getStatus().then(r => r.data)
  })

  const { data: ufwRules, isLoading: rulesLoading } = useQuery({
    queryKey: ['ufw-rules'],
    queryFn: () => firewallApi.getUfwRules().then(r => r.data),
    enabled: selectedBackend === 'ufw'
  })

  const { data: iptablesRules } = useQuery({
    queryKey: ['iptables-rules'],
    queryFn: () => firewallApi.getIptablesRules().then(r => r.data),
    enabled: selectedBackend === 'iptables'
  })

  const enableMutation = useMutation({
    mutationFn: () => firewallApi.enableUfw(),
    onSuccess: () => {
      toast.success('Firewall enabled')
      queryClient.invalidateQueries({ queryKey: ['firewall-status'] })
    },
    onError: () => toast.error('Failed to enable firewall')
  })

  const disableMutation = useMutation({
    mutationFn: () => firewallApi.disableUfw(),
    onSuccess: () => {
      toast.success('Firewall disabled')
      queryClient.invalidateQueries({ queryKey: ['firewall-status'] })
    },
    onError: () => toast.error('Failed to disable firewall')
  })

  const deleteRuleMutation = useMutation({
    mutationFn: (ruleId: string) => firewallApi.deleteUfwRule(ruleId),
    onSuccess: () => {
      toast.success('Rule deleted')
      queryClient.invalidateQueries({ queryKey: ['ufw-rules'] })
    },
    onError: () => toast.error('Failed to delete rule')
  })

  const ufwStatus = status?.find((s: any) => s.backend === 'ufw')

  const rules = selectedBackend === 'ufw' ? ufwRules : iptablesRules

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Backend Selection */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Firewall Backend</h2>
            <p className="text-sm text-dark-400">
              Preferred: {backends?.preferred || 'None detected'}
            </p>
          </div>
          
          <div className="flex gap-2">
            {['ufw', 'iptables', 'firewalld', 'nftables'].map((backend) => {
              const isAvailable = backends?.available?.includes(backend)
              return (
                <button
                  key={backend}
                  onClick={() => setSelectedBackend(backend as FirewallBackend)}
                  disabled={!isAvailable}
                  className={clsx(
                    'px-4 py-2 rounded-lg font-medium text-sm transition-colors',
                    selectedBackend === backend
                      ? 'bg-primary-600 text-white'
                      : isAvailable
                        ? 'bg-dark-700 text-white hover:bg-dark-600'
                        : 'bg-dark-800 text-dark-500 cursor-not-allowed'
                  )}
                >
                  {backend.toUpperCase()}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* UFW Status & Controls */}
      {selectedBackend === 'ufw' && ufwStatus?.available && (
        <div className="card">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={clsx(
                'rounded-full p-3',
                ufwStatus.status?.enabled ? 'bg-green-500/20' : 'bg-red-500/20'
              )}>
                <ShieldCheckIcon className={clsx(
                  'h-8 w-8',
                  ufwStatus.status?.enabled ? 'text-green-500' : 'text-red-500'
                )} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  UFW Firewall
                </h3>
                <div className="flex items-center gap-2 text-sm">
                  {ufwStatus.status?.enabled ? (
                    <>
                      <CheckCircleIcon className="h-4 w-4 text-green-500" />
                      <span className="text-green-500">Active</span>
                    </>
                  ) : (
                    <>
                      <XCircleIcon className="h-4 w-4 text-red-500" />
                      <span className="text-red-500">Inactive</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex gap-2">
              {ufwStatus.status?.enabled ? (
                <button
                  onClick={() => disableMutation.mutate()}
                  disabled={disableMutation.isPending}
                  className="btn btn-danger"
                >
                  Disable Firewall
                </button>
              ) : (
                <button
                  onClick={() => enableMutation.mutate()}
                  disabled={enableMutation.isPending}
                  className="btn btn-success"
                >
                  Enable Firewall
                </button>
              )}
              <button
                onClick={() => setAddRuleOpen(true)}
                className="btn btn-primary"
              >
                <PlusIcon className="h-5 w-5 mr-1" />
                Add Rule
              </button>
            </div>
          </div>

          {/* UFW Info */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-700/50 rounded-lg p-3">
              <p className="text-xs text-dark-400">Default Incoming</p>
              <p className="text-sm font-medium text-white capitalize">
                {ufwStatus.status?.default_incoming || 'deny'}
              </p>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-3">
              <p className="text-xs text-dark-400">Default Outgoing</p>
              <p className="text-sm font-medium text-white capitalize">
                {ufwStatus.status?.default_outgoing || 'allow'}
              </p>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-3">
              <p className="text-xs text-dark-400">Logging</p>
              <p className="text-sm font-medium text-white capitalize">
                {ufwStatus.status?.logging || 'off'}
              </p>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-3">
              <p className="text-xs text-dark-400">Total Rules</p>
              <p className="text-sm font-medium text-white">
                {ufwRules?.length || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Rules Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="card-header mb-0">Firewall Rules</h2>
        </div>

        {rulesLoading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-dark-700 rounded"></div>
            ))}
          </div>
        ) : rules?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Action</th>
                  <th>Direction</th>
                  <th>Port/App</th>
                  <th>From</th>
                  <th>Protocol</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule: any) => (
                  <tr key={rule.id}>
                    <td className="font-mono text-dark-400">{rule.id}</td>
                    <td>
                      <span className={clsx(
                        'badge',
                        rule.action === 'allow' ? 'badge-success' :
                        rule.action === 'deny' ? 'badge-danger' :
                        rule.action === 'reject' ? 'badge-warning' :
                        'badge-info'
                      )}>
                        {rule.action?.toUpperCase()}
                      </span>
                    </td>
                    <td className="capitalize">{rule.direction || 'in'}</td>
                    <td className="font-mono">
                      {rule.port || rule.app || rule.to || 'any'}
                    </td>
                    <td className="font-mono text-dark-400">
                      {rule.from || 'Anywhere'}
                    </td>
                    <td className="uppercase text-dark-400">
                      {rule.protocol || 'any'}
                    </td>
                    <td>
                      <button
                        onClick={() => deleteRuleMutation.mutate(rule.id)}
                        disabled={deleteRuleMutation.isPending}
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
        ) : (
          <div className="text-center py-12 text-dark-400">
            <ShieldCheckIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No firewall rules configured</p>
          </div>
        )}
      </div>

      {/* Add Rule Modal */}
      <AddRuleModal 
        open={addRuleOpen} 
        onClose={() => setAddRuleOpen(false)} 
        backend={selectedBackend}
      />
    </div>
  )
}

function AddRuleModal({ 
  open, 
  onClose, 
  backend: _backend 
}: { 
  open: boolean
  onClose: () => void
  backend: FirewallBackend 
}) {
  const [action, setAction] = useState('allow')
  const [direction, setDirection] = useState('in')
  const [port, setPort] = useState('')
  const [protocol, setProtocol] = useState('tcp')
  const [fromIp, setFromIp] = useState('')
  const [comment, setComment] = useState('')
  
  const queryClient = useQueryClient()

  const addRuleMutation = useMutation({
    mutationFn: (rule: any) => firewallApi.addUfwRule(rule),
    onSuccess: () => {
      toast.success('Rule added successfully')
      queryClient.invalidateQueries({ queryKey: ['ufw-rules'] })
      onClose()
      resetForm()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add rule')
    }
  })

  const resetForm = () => {
    setAction('allow')
    setDirection('in')
    setPort('')
    setProtocol('tcp')
    setFromIp('')
    setComment('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!port) {
      toast.error('Port is required')
      return
    }

    addRuleMutation.mutate({
      action,
      direction,
      port,
      protocol,
      from_ip: fromIp || 'any',
      comment: comment || undefined
    })
  }

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md card">
          <Dialog.Title className="text-lg font-semibold text-white mb-4">
            Add Firewall Rule
          </Dialog.Title>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Action</label>
                <select 
                  value={action} 
                  onChange={(e) => setAction(e.target.value)}
                  className="input"
                >
                  <option value="allow">Allow</option>
                  <option value="deny">Deny</option>
                  <option value="reject">Reject</option>
                  <option value="limit">Limit</option>
                </select>
              </div>
              
              <div>
                <label className="label">Direction</label>
                <select 
                  value={direction} 
                  onChange={(e) => setDirection(e.target.value)}
                  className="input"
                >
                  <option value="in">Incoming</option>
                  <option value="out">Outgoing</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Port</label>
                <input
                  type="text"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  className="input"
                  placeholder="e.g., 80, 443, 8080:8090"
                />
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
                  <option value="any">Any</option>
                </select>
              </div>
            </div>

            <div>
              <label className="label">From IP (optional)</label>
              <input
                type="text"
                value={fromIp}
                onChange={(e) => setFromIp(e.target.value)}
                className="input"
                placeholder="e.g., 192.168.1.0/24"
              />
            </div>

            <div>
              <label className="label">Comment (optional)</label>
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="input"
                placeholder="Rule description"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={addRuleMutation.isPending}
              >
                {addRuleMutation.isPending ? 'Adding...' : 'Add Rule'}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
