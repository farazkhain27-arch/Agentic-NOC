import React, { useEffect, useState } from 'react'
import { RefreshCw, FileText, TrendingDown, Clock, Zap } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, CartesianGrid
} from 'recharts'
import { api } from '../../api/client'
import { Card, CardHeader, StatCard, Spinner } from '../shared/ui'
import { DailyReport } from '../../types'

const PIE_COLORS = ['#EF4444', '#F97316', '#EAB308', '#3B82F6', '#8B5CF6', '#06B6D4']

export default function ReportsPage() {
  const [report, setReport] = useState<DailyReport | null>(null)
  const [trend, setTrend] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [r, t] = await Promise.all([api.reports.daily(), api.reports.trend()])
      setReport(r)
      setTrend(t)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  if (loading) return <Spinner />

  const alarmTypePieData = report
    ? Object.entries(report.alarm_type_breakdown).map(([name, value]) => ({ name, value }))
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Daily Shift Report</h1>
          <p className="text-sm text-gray-400">
            {report ? `Generated: ${new Date(report.generated_at).toLocaleString()}` : 'Loading report...'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 text-sm transition-colors">
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm transition-colors">
            <FileText size={14} /> Export
          </button>
        </div>
      </div>

      {report && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Alarms" value={report.shift_summary.total_alarms} color="gray" icon={<Zap size={16} />} />
            <StatCard label="MTTR" value={`${report.mttr_minutes} min`} sub="Mean Time to Restore" color="blue" icon={<Clock size={16} />} />
            <StatCard label="MTTD" value={`${report.mttd_seconds}s`} sub="Mean Time to Detect" color="green" icon={<TrendingDown size={16} />} />
            <StatCard label="Tickets Created" value={report.tickets_created} color="gray" icon={<FileText size={16} />} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Critical" value={report.shift_summary.critical} color="red" />
            <StatCard label="High" value={report.shift_summary.high} color="orange" />
            <StatCard label="Memo" value={report.shift_summary.memo} color="yellow" />
            <StatCard label="Resolved" value={report.shift_summary.resolved} color="green" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard label="Migrations Executed" value={report.migrations_executed} color="blue" />
            <StatCard label="MDTs Completed" value={report.mdts_completed} color="blue" />
            <StatCard label="Pending" value={report.shift_summary.pending} color="orange" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 7-day trend */}
            <Card>
              <CardHeader title="7-Day Alarm Trend" subtitle="Historical volume by severity" />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trend} barGap={2}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }}
                      tickFormatter={d => d.slice(5)} />
                    <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#9CA3AF' }} />
                    <Bar dataKey="critical" name="Critical" fill="#EF4444" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="high" name="High" fill="#F97316" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="memo" name="Memo" fill="#EAB308" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Alarm type breakdown */}
            <Card>
              <CardHeader title="Alarm Type Breakdown" subtitle="Distribution by alarm code" />
              <div className="p-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={alarmTypePieData}
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {alarmTypePieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          {/* Top affected nodes */}
          <Card>
            <CardHeader title="Top Affected Nodes" subtitle="Ranked by alarm count this shift" />
            <div className="p-4 space-y-3">
              {report.top_affected_nodes.map((node, i) => {
                const maxCount = Math.max(...report.top_affected_nodes.map(n => n.alarm_count))
                const pct = maxCount > 0 ? (node.alarm_count / maxCount) * 100 : 0
                return (
                  <div key={node.node} className="flex items-center gap-4">
                    <span className="text-gray-500 text-xs w-4 text-right">{i + 1}</span>
                    <span className="text-gray-200 text-sm font-mono w-44 shrink-0">{node.node}</span>
                    <div className="flex-1 bg-gray-800 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-gray-300 text-sm font-bold w-8 text-right">{node.alarm_count}</span>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Summary text */}
          <Card>
            <CardHeader title="Shift Summary Narrative" subtitle="Auto-generated by NOC Report Agent" />
            <div className="p-4">
              <p className="text-gray-300 text-sm leading-relaxed">
                During the shift on <strong className="text-white">{report.report_date}</strong>, the NOC
                Agentic AI system processed a total of{' '}
                <strong className="text-white">{report.shift_summary.total_alarms}</strong> alarms across
                all optical transport network elements (SDH, OTN, DWDM).
                {report.shift_summary.critical > 0
                  ? ` ${report.shift_summary.critical} CRITICAL alarm(s) were detected and escalated to management within 60 seconds of detection.`
                  : ' No CRITICAL alarms were observed this shift.'}
                {' '}Mean time to detect (MTTD) was{' '}
                <strong className="text-white">{report.mttd_seconds} seconds</strong>, compared to the
                legacy 30-minute polling interval. Mean time to restore (MTTR) was{' '}
                <strong className="text-white">{report.mttr_minutes} minutes</strong>.{' '}
                {report.migrations_executed > 0
                  ? `${report.migrations_executed} emergency traffic migration(s) were executed via the HITL approval workflow. `
                  : ''}
                {report.mdts_completed > 0
                  ? `${report.mdts_completed} MDT(s) were completed successfully. `
                  : ''}
                {report.shift_summary.resolved} of {report.shift_summary.total_alarms} alarms were
                resolved during the shift.{' '}
                {report.shift_summary.pending > 0
                  ? `${report.shift_summary.pending} alarm(s) remain open and have been handed over to the next shift.`
                  : 'All alarms have been resolved.'}
              </p>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
