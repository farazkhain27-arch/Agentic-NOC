import React, { useEffect, useState } from 'react'
import { Search, Filter, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { useNOCStore } from '../../store/nocStore'
import { api } from '../../api/client'
import { SeverityBadge, StatusBadge, Card, CardHeader, EmptyState, Spinner } from '../shared/ui'
import { formatDistanceToNow } from 'date-fns'
import { Alarm } from '../../types'

export default function AlarmsPage() {
  const { alarms, setAlarms, updateAlarmStatus } = useNOCStore()
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filterSev, setFilterSev] = useState('ALL')
  const [filterStatus, setFilterStatus] = useState('ACTIVE')
  const [selected, setSelected] = useState<Alarm | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.alarms.list()
      setAlarms(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = alarms.filter(a => {
    if (filterSev !== 'ALL' && a.severity !== filterSev) return false
    if (filterStatus !== 'ALL' && a.status !== filterStatus) return false
    if (search && !`${a.node_name} ${a.alarm_type} ${a.alarm_message}`.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const acknowledge = async (id: string) => {
    await api.alarms.acknowledge(id)
    updateAlarmStatus(id, 'ACKNOWLEDGED')
  }

  const resolve = async (id: string) => {
    await api.alarms.resolve(id)
    updateAlarmStatus(id, 'RESOLVED')
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Active Alarms</h1>
          <p className="text-sm text-gray-400">{filtered.length} alarms matching filters</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 text-sm transition-colors">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-2.5 text-gray-500" size={14} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search node, type, message..."
            className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <select value={filterSev} onChange={e => setFilterSev(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none">
          <option value="ALL">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEMO">Memo</option>
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none">
          <option value="ALL">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="RESOLVED">Resolved</option>
        </select>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Alarm table */}
        <div className="xl:col-span-2">
          <Card>
            {loading ? <Spinner /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      {['Severity', 'Type', 'Node / Port', 'Message', 'Age', 'Status', 'Actions'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {filtered.map(alarm => (
                      <tr key={alarm.id}
                        onClick={() => setSelected(alarm)}
                        className="hover:bg-gray-800/30 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3"><SeverityBadge severity={alarm.severity} /></td>
                        <td className="px-4 py-3 font-mono text-xs font-bold text-white">{alarm.alarm_type}</td>
                        <td className="px-4 py-3">
                          <div className="text-xs text-white font-medium">{alarm.node_name}</div>
                          <div className="text-xs text-gray-500">{alarm.shelf}/{alarm.slot}/{alarm.port}</div>
                        </td>
                        <td className="px-4 py-3 max-w-48">
                          <p className="text-xs text-gray-300 truncate">{alarm.alarm_message}</p>
                          <p className="text-xs text-gray-600">{alarm.equipment_type}</p>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                          {formatDistanceToNow(new Date(alarm.detected_at), { addSuffix: true })}
                        </td>
                        <td className="px-4 py-3"><StatusBadge status={alarm.status} /></td>
                        <td className="px-4 py-3">
                          {alarm.status === 'ACTIVE' && (
                            <div className="flex gap-1">
                              <button onClick={e => { e.stopPropagation(); acknowledge(alarm.id) }}
                                className="p-1 rounded hover:bg-blue-900/40 text-blue-400 transition-colors" title="Acknowledge">
                                <CheckCircle size={14} />
                              </button>
                              <button onClick={e => { e.stopPropagation(); resolve(alarm.id) }}
                                className="p-1 rounded hover:bg-green-900/40 text-green-400 transition-colors" title="Resolve">
                                <XCircle size={14} />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 && <EmptyState message="No alarms match your filters" />}
              </div>
            )}
          </Card>
        </div>

        {/* Alarm detail panel */}
        <div>
          <Card>
            <CardHeader title="Alarm Detail" subtitle={selected ? selected.id.slice(0, 8) + '...' : 'Select an alarm'} />
            {selected ? (
              <div className="p-4 space-y-4">
                <div>
                  <SeverityBadge severity={selected.severity} />
                  <h3 className="text-white font-bold text-lg mt-2">{selected.alarm_type}</h3>
                  <p className="text-gray-400 text-sm mt-1">{selected.alarm_message}</p>
                </div>
                <div className="space-y-2">
                  {[
                    ['Node', selected.node_name],
                    ['IP', selected.node_ip ?? '—'],
                    ['Equipment', selected.equipment_type ?? '—'],
                    ['Port', `${selected.shelf}/${selected.slot}/${selected.port}`],
                    ['Wavelength', selected.wavelength ?? '—'],
                    ['Status', selected.status],
                    ['NMS Source', selected.nms_source ?? '—'],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-gray-500">{k}</span>
                      <span className="text-gray-200 font-medium">{v}</span>
                    </div>
                  ))}
                </div>
                <div className="border-t border-gray-800 pt-3">
                  <p className="text-xs text-gray-500 mb-1">Optical PM Values</p>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      ['Rx Power', selected.rx_power != null ? `${selected.rx_power} dBm` : '—'],
                      ['BER', selected.ber_value != null ? selected.ber_value.toExponential(1) : '—'],
                      ['OSNR', selected.osnr != null ? `${selected.osnr} dB` : '—'],
                    ].map(([k, v]) => (
                      <div key={k} className="bg-gray-800 rounded p-2 text-center">
                        <div className="text-xs text-gray-500">{k}</div>
                        <div className="text-xs font-mono text-white mt-0.5">{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {selected.circuit_ids && (
                  <div className="border-t border-gray-800 pt-3">
                    <p className="text-xs text-gray-500 mb-1">Affected Circuits</p>
                    <div className="flex flex-wrap gap-1">
                      {JSON.parse(selected.circuit_ids).map((c: string) => (
                        <span key={c} className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-xs font-mono">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="border-t border-gray-800 pt-3 text-xs text-gray-500">
                  Detected: {new Date(selected.detected_at).toLocaleString()}
                </div>
                <div className="flex gap-2 pt-1">
                  {selected.status === 'ACTIVE' && (
                    <>
                      <button onClick={() => acknowledge(selected.id)}
                        className="flex-1 py-2 bg-blue-900/40 border border-blue-600 text-blue-300 rounded-lg text-xs hover:bg-blue-900/60 transition-colors">
                        Acknowledge
                      </button>
                      <button onClick={() => resolve(selected.id)}
                        className="flex-1 py-2 bg-green-900/40 border border-green-600 text-green-300 rounded-lg text-xs hover:bg-green-900/60 transition-colors">
                        Resolve
                      </button>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState message="Click an alarm row to view details" />
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
