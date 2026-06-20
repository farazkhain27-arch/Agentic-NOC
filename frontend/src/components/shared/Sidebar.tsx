import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Bell, Ticket, ArrowLeftRight,
  Wrench, BarChart3, Radio, AlertTriangle
} from 'lucide-react'
import { useNOCStore } from '../../store/nocStore'
import { clsx } from 'clsx'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/alarms', label: 'Alarms', icon: Bell },
  { to: '/tickets', label: 'Tickets', icon: Ticket },
  { to: '/migration', label: 'Migration', icon: ArrowLeftRight, badge: 'migration' },
  { to: '/mdt', label: 'MDT', icon: Wrench, badge: 'mdt' },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
]

export default function Sidebar() {
  const { wsConnected, alarms, migrations, mdts } = useNOCStore()
  const criticalCount = alarms.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE').length
  const pendingMig = migrations.filter(m => m.status === 'PENDING_APPROVAL').length
  const pendingMdt = mdts.filter(m => m.status === 'PENDING').length

  const getBadge = (badge?: string) => {
    if (badge === 'migration') return pendingMig
    if (badge === 'mdt') return pendingMdt
    return 0
  }

  return (
    <aside className="w-60 shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col min-h-screen">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <Radio size={18} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">NOC Agentic AI</p>
            <p className="text-gray-500 text-xs">Network Operations</p>
          </div>
        </div>
      </div>

      {/* Critical alert banner */}
      {criticalCount > 0 && (
        <div className="mx-3 mt-3 px-3 py-2 rounded-lg bg-red-950/40 border border-red-500/40 flex items-center gap-2">
          <AlertTriangle size={13} className="text-red-400 shrink-0 animate-pulse" />
          <span className="text-red-300 text-xs font-medium">{criticalCount} Critical Active</span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ to, label, icon: Icon, exact, badge }) => {
          const badgeCount = getBadge(badge)
          return (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all group',
                isActive
                  ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              )}
            >
              <Icon size={16} className="shrink-0" />
              <span className="flex-1">{label}</span>
              {badgeCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-orange-500 text-white min-w-[20px] text-center">
                  {badgeCount}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Connection status */}
      <div className="px-4 py-4 border-t border-gray-800">
        <div className="flex items-center gap-2 text-xs">
          <div className={clsx(
            'w-2 h-2 rounded-full shrink-0',
            wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          )} />
          <span className={wsConnected ? 'text-green-400' : 'text-red-400'}>
            {wsConnected ? 'Live Stream Active' : 'Reconnecting...'}
          </span>
        </div>
        <p className="text-gray-600 text-xs mt-1">LangGraph + Claude Sonnet</p>
      </div>
    </aside>
  )
}
