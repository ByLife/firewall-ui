import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  ClipboardDocumentListIcon,
  FunnelIcon,
  ArrowPathIcon,
  UserIcon,
  ShieldCheckIcon,
  ServerIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'
import { auditApi } from '../services/api'
import clsx from 'clsx'

export default function Audit() {
  const [actionFilter, setActionFilter] = useState<string>('')
  const [userFilter, setUserFilter] = useState<string>('')

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['audit-logs', actionFilter, userFilter],
    queryFn: () => auditApi.getLogs({
      action: actionFilter || undefined,
      user_id: userFilter ? parseInt(userFilter) : undefined,
      limit: 100
    }).then(r => r.data)
  })

  const getActionIcon = (action: string) => {
    if (action.includes('login') || action.includes('auth')) {
      return <UserIcon className="h-5 w-5" />
    }
    if (action.includes('firewall') || action.includes('rule')) {
      return <ShieldCheckIcon className="h-5 w-5" />
    }
    if (action.includes('route') || action.includes('network')) {
      return <ServerIcon className="h-5 w-5" />
    }
    return <Cog6ToothIcon className="h-5 w-5" />
  }

  const getActionColor = (action: string) => {
    if (action.includes('create') || action.includes('add') || action.includes('enable')) {
      return 'text-green-500 bg-green-500/20'
    }
    if (action.includes('delete') || action.includes('remove') || action.includes('disable')) {
      return 'text-red-500 bg-red-500/20'
    }
    if (action.includes('update') || action.includes('modify')) {
      return 'text-yellow-500 bg-yellow-500/20'
    }
    if (action.includes('login') || action.includes('logout')) {
      return 'text-blue-500 bg-blue-500/20'
    }
    return 'text-dark-400 bg-dark-600'
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString()
    }
  }

  // Get unique actions for filter
  const uniqueActions: string[] = Array.from(new Set(logs?.map((log: any) => String(log.action)) || []))

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Audit Log</h2>
            <p className="text-sm text-dark-400">
              Track all actions performed in the system
            </p>
          </div>
          
          <button 
            onClick={() => refetch()}
            className="btn btn-secondary"
          >
            <ArrowPathIcon className="h-4 w-4 mr-1" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <FunnelIcon className="h-5 w-5 text-dark-400" />
          <h3 className="font-medium text-white">Filters</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Action Type</label>
            <select 
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="input"
            >
              <option value="">All Actions</option>
              {uniqueActions.map((action: string) => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="label">User ID</label>
            <input
              type="text"
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="input"
              placeholder="Filter by user ID"
            />
          </div>
          
          <div className="flex items-end">
            <button 
              onClick={() => {
                setActionFilter('')
                setUserFilter('')
              }}
              className="btn btn-secondary"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="card">
        <h2 className="card-header">Recent Activity</h2>
        
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-dark-700 rounded-lg"></div>
            ))}
          </div>
        ) : logs?.length > 0 ? (
          <div className="space-y-2">
            {logs.map((log: any) => {
              const { date, time } = formatTimestamp(log.created_at || log.timestamp)
              return (
                <div 
                  key={log.id}
                  className="flex items-start gap-4 p-4 rounded-lg bg-dark-700/50 hover:bg-dark-700 transition-colors"
                >
                  <div className={clsx(
                    'rounded-lg p-2 flex-shrink-0',
                    getActionColor(log.action)
                  )}>
                    {getActionIcon(log.action)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">
                        {log.action}
                      </span>
                      {log.resource && (
                        <span className="badge badge-info">{log.resource}</span>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-3 mt-1 text-sm text-dark-400">
                      {log.user_id && (
                        <span className="flex items-center gap-1">
                          <UserIcon className="h-3 w-3" />
                          User #{log.user_id}
                        </span>
                      )}
                      {log.username && (
                        <span className="flex items-center gap-1">
                          <UserIcon className="h-3 w-3" />
                          {log.username}
                        </span>
                      )}
                      {log.ip_address && (
                        <span className="font-mono text-xs">
                          {log.ip_address}
                        </span>
                      )}
                    </div>
                    
                    {log.details && (
                      <div className="mt-2 text-sm text-dark-300 bg-dark-800 rounded p-2 font-mono text-xs overflow-x-auto">
                        {typeof log.details === 'object' 
                          ? JSON.stringify(log.details, null, 2)
                          : log.details}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm text-white">{time}</p>
                    <p className="text-xs text-dark-500">{date}</p>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-center py-12 text-dark-400">
            <ClipboardDocumentListIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No audit logs found</p>
            <p className="text-sm mt-1">Actions will be logged here</p>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      {logs && logs.length > 0 && (
        <div className="card">
          <h3 className="card-header">Activity Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-700/50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-white">{logs.length}</p>
              <p className="text-sm text-dark-400">Total Events</p>
            </div>
            <div className="bg-green-500/10 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-green-400">
                {logs.filter((l: any) => 
                  l.action.includes('create') || 
                  l.action.includes('add') ||
                  l.action.includes('enable')
                ).length}
              </p>
              <p className="text-sm text-dark-400">Create Actions</p>
            </div>
            <div className="bg-yellow-500/10 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-yellow-400">
                {logs.filter((l: any) => 
                  l.action.includes('update') || 
                  l.action.includes('modify')
                ).length}
              </p>
              <p className="text-sm text-dark-400">Update Actions</p>
            </div>
            <div className="bg-red-500/10 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-red-400">
                {logs.filter((l: any) => 
                  l.action.includes('delete') || 
                  l.action.includes('remove') ||
                  l.action.includes('disable')
                ).length}
              </p>
              <p className="text-sm text-dark-400">Delete Actions</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
