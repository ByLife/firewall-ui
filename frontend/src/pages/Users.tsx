import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  UserIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ShieldCheckIcon,
  KeyIcon
} from '@heroicons/react/24/outline'
import { Dialog } from '@headlessui/react'
import toast from 'react-hot-toast'
import { usersApi } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import clsx from 'clsx'

export default function Users() {
  const [addUserOpen, setAddUserOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<any>(null)
  const { user: currentUser } = useAuthStore()
  const queryClient = useQueryClient()

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.getAll().then(r => r.data)
  })

  const deleteUserMutation = useMutation({
    mutationFn: (userId: number) => usersApi.delete(userId),
    onSuccess: () => {
      toast.success('User deleted')
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete user')
    }
  })

  const handleDelete = (user: any) => {
    if (user.id === currentUser?.id) {
      toast.error("You cannot delete your own account")
      return
    }
    if (confirm(`Are you sure you want to delete user "${user.username}"?`)) {
      deleteUserMutation.mutate(user.id)
    }
  }

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return <span className="badge badge-danger">Admin</span>
      case 'operator':
        return <span className="badge badge-warning">Operator</span>
      case 'viewer':
        return <span className="badge badge-info">Viewer</span>
      default:
        return <span className="badge">{role}</span>
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">User Management</h2>
            <p className="text-sm text-dark-400">
              Manage user accounts and permissions
            </p>
          </div>
          
          <button 
            onClick={() => setAddUserOpen(true)}
            className="btn btn-primary"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add User
          </button>
        </div>
      </div>

      {/* Roles Explanation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card bg-red-500/10 border border-red-500/30">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheckIcon className="h-6 w-6 text-red-500" />
            <h3 className="font-semibold text-white">Admin</h3>
          </div>
          <p className="text-sm text-dark-300">
            Full access to all features including user management, firewall rules, 
            and system configuration.
          </p>
        </div>
        
        <div className="card bg-yellow-500/10 border border-yellow-500/30">
          <div className="flex items-center gap-3 mb-2">
            <KeyIcon className="h-6 w-6 text-yellow-500" />
            <h3 className="font-semibold text-white">Operator</h3>
          </div>
          <p className="text-sm text-dark-300">
            Can view and modify firewall rules, network settings, and ports. 
            Cannot manage users.
          </p>
        </div>
        
        <div className="card bg-blue-500/10 border border-blue-500/30">
          <div className="flex items-center gap-3 mb-2">
            <UserIcon className="h-6 w-6 text-blue-500" />
            <h3 className="font-semibold text-white">Viewer</h3>
          </div>
          <p className="text-sm text-dark-300">
            Read-only access. Can view all information but cannot make any changes.
          </p>
        </div>
      </div>

      {/* Users Table */}
      <div className="card">
        <h2 className="card-header">All Users</h2>
        
        {isLoading ? (
          <div className="animate-pulse space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-dark-700 rounded-lg"></div>
            ))}
          </div>
        ) : users?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((user: any) => (
                  <tr key={user.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="bg-primary-500/20 rounded-full p-2">
                          <UserIcon className="h-5 w-5 text-primary-500" />
                        </div>
                        <div>
                          <p className="font-semibold text-white">
                            {user.username}
                            {user.id === currentUser?.id && (
                              <span className="ml-2 text-xs text-primary-400">(You)</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="text-dark-300">{user.email || '-'}</td>
                    <td>{getRoleBadge(user.role)}</td>
                    <td>
                      <span className={clsx(
                        'badge',
                        user.is_active ? 'badge-success' : 'badge-danger'
                      )}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="text-dark-400 text-sm">
                      {user.created_at 
                        ? new Date(user.created_at).toLocaleDateString() 
                        : '-'}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setEditingUser(user)}
                          className="text-dark-400 hover:text-primary-500 transition-colors"
                          title="Edit user"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          disabled={user.id === currentUser?.id || deleteUserMutation.isPending}
                          className={clsx(
                            'transition-colors',
                            user.id === currentUser?.id
                              ? 'text-dark-600 cursor-not-allowed'
                              : 'text-dark-400 hover:text-red-500'
                          )}
                          title="Delete user"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-dark-400">
            <UserIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No users found</p>
          </div>
        )}
      </div>

      {/* Add/Edit User Modal */}
      <UserModal 
        open={addUserOpen || !!editingUser} 
        onClose={() => {
          setAddUserOpen(false)
          setEditingUser(null)
        }}
        user={editingUser}
      />
    </div>
  )
}

function UserModal({ 
  open, 
  onClose, 
  user 
}: { 
  open: boolean
  onClose: () => void
  user?: any 
}) {
  const [username, setUsername] = useState(user?.username || '')
  const [email, setEmail] = useState(user?.email || '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(user?.role || 'viewer')
  const [isActive, setIsActive] = useState(user?.is_active ?? true)
  
  const queryClient = useQueryClient()
  const isEditing = !!user

  // Reset form when user changes
  useState(() => {
    setUsername(user?.username || '')
    setEmail(user?.email || '')
    setPassword('')
    setRole(user?.role || 'viewer')
    setIsActive(user?.is_active ?? true)
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => usersApi.create(data),
    onSuccess: () => {
      toast.success('User created successfully')
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onClose()
      resetForm()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create user')
    }
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => usersApi.update(user.id, data),
    onSuccess: () => {
      toast.success('User updated successfully')
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update user')
    }
  })

  const resetForm = () => {
    setUsername('')
    setEmail('')
    setPassword('')
    setRole('viewer')
    setIsActive(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!username) {
      toast.error('Username is required')
      return
    }
    
    if (!isEditing && !password) {
      toast.error('Password is required for new users')
      return
    }

    const data: any = {
      username,
      email: email || undefined,
      role,
      is_active: isActive
    }

    if (password) {
      data.password = password
    }

    if (isEditing) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md card">
          <Dialog.Title className="text-lg font-semibold text-white mb-4">
            {isEditing ? 'Edit User' : 'Add New User'}
          </Dialog.Title>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input"
                placeholder="Enter username"
              />
            </div>

            <div>
              <label className="label">Email (optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="user@example.com"
              />
            </div>

            <div>
              <label className="label">
                Password {isEditing && '(leave blank to keep current)'}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder={isEditing ? '••••••••' : 'Enter password'}
              />
            </div>

            <div>
              <label className="label">Role</label>
              <select 
                value={role} 
                onChange={(e) => setRole(e.target.value)}
                className="input"
              >
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="isActive"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded border-dark-600 bg-dark-700 text-primary-500 
                         focus:ring-primary-500 focus:ring-offset-dark-800"
              />
              <label htmlFor="isActive" className="text-sm text-dark-300">
                User is active
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <button type="button" onClick={onClose} className="btn btn-secondary">
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending 
                  ? 'Saving...' 
                  : isEditing ? 'Save Changes' : 'Create User'}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  )
}
