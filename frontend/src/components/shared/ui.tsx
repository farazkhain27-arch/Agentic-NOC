import React from 'react'
import { clsx } from 'clsx'
import { Severity } from '../../types'

export const severityConfig = {
  CRITICAL: { bg: 'bg-red-900/40', border: 'border-red-500', text: 'text-red-400', dot: 'bg-red-500', label: 'CRITICAL' },
  HIGH:     { bg: 'bg-orange-900/40', border: 'border-orange-500', text: 'text-orange-400', dot: 'bg-orange-500', label: 'HIGH' },
  MEMO:     { bg: 'bg-yellow-900/40', border: 'border-yellow-500', text: 'text-yellow-400', dot: 'bg-yellow-500', label: 'MEMO' },
  INFO:     { bg: 'bg-blue-900/40', border: 'border-blue-500', text: 'text-blue-400', dot: 'bg-blue-500', label: 'INFO' },
}

export function SeverityBadge({ severity }: { severity: string }) {
  const cfg = severityConfig[severity as Severity] ?? severityConfig.INFO
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border', cfg.bg, cfg.border, cfg.text)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, string> = {
    ACTIVE: 'bg-red-900/30 border-red-600 text-red-300',
    ACKNOWLEDGED: 'bg-blue-900/30 border-blue-600 text-blue-300',
    RESOLVED: 'bg-green-900/30 border-green-600 text-green-300',
    SUPPRESSED: 'bg-gray-800 border-gray-600 text-gray-400',
    PENDING: 'bg-yellow-900/30 border-yellow-600 text-yellow-300',
    PENDING_APPROVAL: 'bg-orange-900/30 border-orange-600 text-orange-300',
    APPROVED: 'bg-green-900/30 border-green-600 text-green-300',
    REJECTED: 'bg-red-900/30 border-red-600 text-red-300',
    COMPLETED: 'bg-gray-800 border-gray-600 text-gray-300',
    Open: 'bg-blue-900/30 border-blue-600 text-blue-300',
    'In Progress': 'bg-purple-900/30 border-purple-600 text-purple-300',
    Resolved: 'bg-green-900/30 border-green-600 text-green-300',
  }
  return (
    <span className={clsx('inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border', cfg[status] ?? 'bg-gray-800 border-gray-600 text-gray-400')}>
      {status}
    </span>
  )
}

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray'
  icon?: React.ReactNode
}

export function StatCard({ label, value, sub, color = 'gray', icon }: StatCardProps) {
  const colorMap = {
    red: 'border-red-500/30 bg-red-950/20',
    orange: 'border-orange-500/30 bg-orange-950/20',
    yellow: 'border-yellow-500/30 bg-yellow-950/20',
    green: 'border-green-500/30 bg-green-950/20',
    blue: 'border-blue-500/30 bg-blue-950/20',
    gray: 'border-gray-700 bg-gray-900/50',
  }
  const valueColor = {
    red: 'text-red-400', orange: 'text-orange-400', yellow: 'text-yellow-400',
    green: 'text-green-400', blue: 'text-blue-400', gray: 'text-white',
  }
  return (
    <div className={clsx('rounded-xl border p-4 flex flex-col gap-1', colorMap[color])}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">{label}</span>
        {icon && <span className="text-gray-500">{icon}</span>}
      </div>
      <span className={clsx('text-3xl font-bold tabular-nums', valueColor[color])}>{value}</span>
      {sub && <span className="text-xs text-gray-500">{sub}</span>}
    </div>
  )
}

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx('rounded-xl border border-gray-800 bg-gray-900/60 backdrop-blur-sm', className)}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-800">
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-600">
      <svg className="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p className="text-sm">{message}</p>
    </div>
  )
}

export function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}
