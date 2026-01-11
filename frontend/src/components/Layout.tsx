import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  HomeIcon, 
  ShieldCheckIcon, 
  GlobeAltIcon, 
  ServerIcon,
  CubeIcon,
  UsersIcon,
  ClipboardDocumentListIcon,
  Bars3Icon,
  XMarkIcon,
  ArrowRightOnRectangleIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline'
import { Menu, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { useAuthStore } from '../stores/authStore'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Firewall', href: '/firewall', icon: ShieldCheckIcon },
  { name: 'Network', href: '/network', icon: GlobeAltIcon },
  { name: 'Ports', href: '/ports', icon: ServerIcon },
  { name: 'Docker', href: '/docker', icon: CubeIcon },
  { name: 'Users', href: '/users', icon: UsersIcon, adminOnly: true },
  { name: 'Audit Log', href: '/audit', icon: ClipboardDocumentListIcon, adminOnly: true },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuthStore()
  
  const isAdmin = user?.role === 'admin'
  const filteredNav = navigation.filter(item => !item.adminOnly || isAdmin)

  return (
    <div className="min-h-screen bg-dark-900">
      {/* Mobile sidebar */}
      <Transition.Root show={sidebarOpen} as={Fragment}>
        <div className="relative z-50 lg:hidden">
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-dark-950/80" onClick={() => setSidebarOpen(false)} />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <div className="relative mr-16 flex w-full max-w-xs flex-1">
                <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                  <button type="button" className="-m-2.5 p-2.5" onClick={() => setSidebarOpen(false)}>
                    <XMarkIcon className="h-6 w-6 text-white" />
                  </button>
                </div>
                <SidebarContent navigation={filteredNav} currentPath={location.pathname} />
              </div>
            </Transition.Child>
          </div>
        </div>
      </Transition.Root>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <SidebarContent navigation={filteredNav} currentPath={location.pathname} />
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-dark-700 bg-dark-800/80 backdrop-blur px-4 sm:gap-x-6 sm:px-6 lg:px-8">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-dark-400 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex flex-1 items-center">
              <h1 className="text-lg font-semibold text-white">
                {filteredNav.find(item => item.href === location.pathname)?.name || 'Firewall Manager'}
              </h1>
            </div>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              {/* User menu */}
              <Menu as="div" className="relative">
                <Menu.Button className="-m-1.5 flex items-center p-1.5">
                  <div className="flex items-center gap-x-3">
                    <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center">
                      <span className="text-sm font-medium text-white">
                        {user?.username?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <span className="hidden lg:flex lg:items-center">
                      <span className="text-sm font-medium text-white">
                        {user?.username}
                      </span>
                      <ChevronDownIcon className="ml-2 h-5 w-5 text-dark-400" />
                    </span>
                  </div>
                </Menu.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Menu.Items className="absolute right-0 z-10 mt-2.5 w-48 origin-top-right rounded-md bg-dark-800 py-2 shadow-lg ring-1 ring-dark-700 focus:outline-none">
                    <div className="px-4 py-2 border-b border-dark-700">
                      <p className="text-sm text-dark-400">Signed in as</p>
                      <p className="text-sm font-medium text-white">{user?.email}</p>
                      <span className="badge badge-info mt-1">{user?.role}</span>
                    </div>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={logout}
                          className={clsx(
                            'flex w-full items-center gap-x-2 px-4 py-2 text-sm text-dark-300',
                            active && 'bg-dark-700'
                          )}
                        >
                          <ArrowRightOnRectangleIcon className="h-5 w-5" />
                          Sign out
                        </button>
                      )}
                    </Menu.Item>
                  </Menu.Items>
                </Transition>
              </Menu>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-6 px-4 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  )
}

function SidebarContent({ 
  navigation, 
  currentPath 
}: { 
  navigation: Array<{ name: string; href: string; icon: React.ComponentType<{ className?: string }>; adminOnly?: boolean }>
  currentPath: string 
}) {
  return (
    <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-dark-800 border-r border-dark-700 px-6 pb-4">
      <div className="flex h-16 shrink-0 items-center">
        <ShieldCheckIcon className="h-8 w-8 text-primary-500" />
        <span className="ml-3 text-xl font-bold text-white">Firewall UI</span>
      </div>
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-7">
          <li>
            <ul role="list" className="-mx-2 space-y-1">
              {navigation.map((item: any) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={clsx(
                      'group flex gap-x-3 rounded-md p-2 text-sm font-medium leading-6 transition-colors',
                      currentPath === item.href
                        ? 'bg-dark-700 text-white'
                        : 'text-dark-400 hover:bg-dark-700/50 hover:text-white'
                    )}
                  >
                    <item.icon className="h-6 w-6 shrink-0" />
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </li>
        </ul>
      </nav>
    </div>
  )
}
