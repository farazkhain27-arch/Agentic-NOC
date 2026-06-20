import React, { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle, Clock, Cpu, Wifi, WifiOff, Zap } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import { useNOCStore } from '../../store/nocStore'
import { api } from '../../api/client'
import { StatCard, Card, CardHeader, SeverityBadge } from '../shared/ui'
import { formatDistanceToNow } from 'date-fns'

export default function Dashboard() {
  const { alarms, stats, setStats, wsConnected, liveFeed, setAlarms, tickets, setTickets } = useNOCStore()
  const [trend, setTrend] = useState<any[]>([])

  useEffect(() => {
    api.alarms.list({ limit: '50' }).then(setAlarms).catch(() => {})
    api.alarms.stats().then(setStats).catch(() => {})
    api.tickets.list().then(setTickets).catch(() => {})
    api.reports.trend().then(setTrend).catch(() => {})
  }, [])

  const activeAlarms = alarms.filter(a => a.status === 'ACTIVE')
  const criticalAlarms = alarms.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">NOC Operations Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Real-time optical transport network monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
            wsConnected ? 'border-green-500/50 bg-green-950/30 text-green-400' : 'border-red-500/50 bg-red-950/30 text-red-400'
          }`}>
            {wsConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {wsConnected ? 'Live Feed Active' : 'Connecting...'}
          </div>
          <div className="text-xs text-gray-500">{new Date().toUTCString().slice(0, 25)}</div>
        </div>
      </div>

      {/* Critical banner */}
      {criticalAlarms.length > 0 && (
        <div className="rounded-xl border border-red-500/50 bg-red-950/20 p-4 flex items-center gap-4 animate-pulse">
          <AlertTriangle className="text-red-400 shrink-0" size={24} />
          <div>
            <p className="text-red-300 font-semibold">{criticalAlarms.length} CRITICAL alarm{criticalAlarms.length > 1 ? 's' : ''} require immediate attention</p>
            <p className="text-red-400/70 text-sm">{criticalAlarms.map(a => a.node_name).join(' • ')}</p>
          </div>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Critical Active" value={stats?.critical ?? 0} color="red" icon={<AlertTriangle size={16} />} sub="Immediate action" />
        <StatCard label="High Active" value={stats?.high ?? 0} color="orange" icon={<Zap size={16} />} sub="< 30 min response" />
        <StatCard label="Memo Active" value={stats?.memo ?? 0} color="yellow" icon={<Clock size={16} />} sub="< 4 hr response" />
        <StatCard label="Resolved Today" value={stats?.resolved ?? 0} color="green" icon={<CheckCircle size={16} />} sub="Total resolved" />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="OTN Alarms" value={stats?.by_equipment?.OTN ?? 0} color="blue" icon={<Cpu size={16} />} />
        <StatCard label="SDH Alarms" value={stats?.by_equipment?.SDH ?? 0} color="blue" icon={<Cpu size={16} />} />
        <StatCard label="DWDM Alarms" value={stats?.by_equipment?.DWDM ?? 0} color="blue" icon={<Activity size={16} />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 7-day trend */}
        <Card>
          <CardHeader title="7-Day Alarm Trend" subtitle="Historical alarm volume by severity" />
          <div className="p-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="critical" stroke="#EF4444" strokeWidth={2} dot={false} name="Critical" />
                <Line type="monotone" dataKey="high" stroke="#F97316" strokeWidth={2} dot={false} name="High" />
                <Line type="monotone" dataKey="memo" stroke="#EAB308" strokeWidth={2} dot={false} name="Memo" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Equipment breakdown */}
        <Card>
          <CardHeader title="Alarms by Equipment Type" subtitle="Active alarm distribution" />
          <div className="p-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: 'OTN', count: stats?.by_equipment?.OTN ?? 0, fill: '#3B82F6' },
                { name: 'SDH', count: stats?.by_equipment?.SDH ?? 0, fill: '#8B5CF6' },
                { name: 'DWDM', count: stats?.by_equipment?.DWDM ?? 0, fill: '#06B6D4' },
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6B7280' }} />
                <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" name="Alarms" radius={[4, 4, 0, 0]}>
                  {[0,1,2].map(i => <React.Fragment key={i} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent alarms */}
        <Card>
          <CardHeader title="Recent Alarms" subtitle="Latest network events" />
          <div className="divide-y divide-gray-800">
            {activeAlarms.slice(0, 6).map(alarm => (
              <div key={alarm.id} className="flex items-start gap-3 p-3 hover:bg-gray-800/30 transition-colors">
                <div className="mt-0.5 shrink-0"><SeverityBadge severity={alarm.severity} /></div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white">{alarm.alarm_type}</span>
                    <span className="text-xs text-gray-500">{alarm.node_name}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{alarm.alarm_message}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{formatDistanceToNow(new Date(alarm.detected_at), { addSuffix: true })}</p>
                </div>
              </div>
            ))}
            {activeAlarms.length === 0 && (
              <div className="flex items-center justify-center py-12 text-gray-600 text-sm">
                No active alarms — network nominal
              </div>
            )}
          </div>
        </Card>

        {/* Live agent feed */}
        <Card>
          <CardHeader title="AI Agent Live Feed" subtitle="Real-time agent activity log" />
          <div className="p-3 space-y-2 h-72 overflow-y-auto">
            {liveFeed.slice(0, 15).map((msg, i) => (
              <div key={i} className="flex gap-2 text-xs">
                <span className="text-gray-600 shrink-0 font-mono">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                <span className={`shrink-0 font-medium ${
                  msg.type === 'alarm_processed' ? 'text-blue-400' :
                  msg.type === 'alarm_error' ? 'text-red-400' : 'text-gray-400'
                }`}>[{msg.type}]</span>
                <span className="text-gray-300 truncate">
                  {msg.type === 'alarm_processed' ? `Processed ${msg.data?.alarm?.alarm_type} on ${msg.data?.alarm?.node_name} → ${msg.data?.ticket?.jira_key ?? 'queued'}` :
                   msg.type === 'connected' ? msg.data?.message :
                   JSON.stringify(msg.data).slice(0, 60)}
                </span>
              </div>
            ))}
            {liveFeed.length === 0 && (
              <div className="text-center text-gray-600 text-xs pt-8">Waiting for agent events...</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
