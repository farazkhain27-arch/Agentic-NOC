import React, { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Plus, Clock, RefreshCw, ShieldAlert } from 'lucide-react'
import { useNOCStore } from '../../store/nocStore'
import { api } from '../../api/client'
import { Card, CardHeader, StatusBadge, EmptyState, Spinner } from '../shared/ui'
import { formatDistanceToNow } from 'date-fns'
import { MDTRequest } from '../../types'

export default function MDTPage() {
  const { mdts, setMdts, updateMdt } = useNOCStore()
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<MDTRequest | null>(null)
  const [approvedBy, setApprovedBy] = useState('NOC Manager')
  const [notes, setNotes] = useState('')
  const [acting, setActing] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ node_name: '', shelf: '', slot: '', reason: '', scheduled_start: '', scheduled_end: '', requested_by: 'NOC Engineer' })

  const load = async () => {
    setLoading(true)
    try { const data = await api.mdt.list(); setMdts(data) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const approve = async (id: string, approved: boolean) => {
    setActing(true)
    try {
      const updated = (await api.mdt.approve(id, approved, approvedBy, notes)) as MDTRequest
      updateMdt(id, { status: updated.status, approved_by: updated.approved_by })
      if (selected?.id === id) setSelected({ ...selected, status: updated.status })
      setNotes('')
    } finally { setActing(false) }
  }

  const complete = async (id: string) => {
    setActing(true)
    try {
      await api.mdt.complete(id)
      updateMdt(id, { status: 'COMPLETED' })
      if (selected?.id === id) setSelected({ ...selected, status: 'COMPLETED' })
    } finally { setActing(false) }
  }

  const create = async () => {
    if (!form.node_name || !form.reason) return
    setActing(true)
    try {
      const created = (await api.mdt.create(form)) as MDTRequest
      setMdts([created, ...mdts])
      setShowCreate(false)
      setForm({ node_name: '', shelf: '', slot: '', reason: '', scheduled_start: '', scheduled_end: '', requested_by: 'NOC Engineer' })
    } finally { setActing(false) }
  }

  const pending = mdts.filter(m => m.status === 'PENDING')
  const approved = mdts.filter(m => m.status === 'APPROVED')
  const others = mdts.filter(m => !['PENDING', 'APPROVED'].includes(m.status))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">MDT — Maintenance Down Time</h1>
          <p className="text-sm text-gray-400">Card reset & maintenance workflow with approval gate</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 text-sm transition-colors">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 text-sm transition-colors">
            <Plus size={14} /> New MDT
          </button>
        </div>
      </div>

      {/* Create MDT form */}
      {showCreate && (
        <Card>
          <CardHeader title="Create MDT Request" />
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { label: 'Node Name *', key: 'node_name', placeholder: 'RIYADH-OTN-01' },
              { label: 'Shelf', key: 'shelf', placeholder: '1' },
              { label: 'Slot', key: 'slot', placeholder: '4' },
              { label: 'Requested By', key: 'requested_by', placeholder: 'NOC Engineer' },
              { label: 'Scheduled Start', key: 'scheduled_start', placeholder: '2024-01-15T22:00:00Z' },
              { label: 'Scheduled End', key: 'scheduled_end', placeholder: '2024-01-15T23:00:00Z' },
            ].map(f => (
              <div key={f.key}>
                <label className="text-xs text-gray-400 block mb-1">{f.label}</label>
                <input value={(form as any)[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                  placeholder={f.placeholder}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500" />
              </div>
            ))}
            <div className="md:col-span-2">
              <label className="text-xs text-gray-400 block mb-1">Reason *</label>
              <textarea value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} rows={3}
                placeholder="Describe reason for MDT and card reset..."
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 resize-none" />
            </div>
            <div className="md:col-span-2 flex gap-2 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
              <button onClick={create} disabled={acting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors disabled:opacity-50">
                Submit MDT Request
              </button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 space-y-4">
          {loading ? <Spinner /> : (
            <>
              {pending.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-yellow-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <Clock size={14} /> Pending Approval ({pending.length})
                  </h2>
                  {pending.map(m => <MDTCard key={m.id} mdt={m} onSelect={setSelected} selected={selected?.id === m.id} />)}
                </div>
              )}
              {approved.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-green-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <CheckCircle size={14} /> Approved — Ready to Execute ({approved.length})
                  </h2>
                  {approved.map(m => <MDTCard key={m.id} mdt={m} onSelect={setSelected} selected={selected?.id === m.id} />)}
                </div>
              )}
              {others.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wider">History</h2>
                  {others.map(m => <MDTCard key={m.id} mdt={m} onSelect={setSelected} selected={selected?.id === m.id} />)}
                </div>
              )}
              {mdts.length === 0 && <EmptyState message="No MDT requests yet — auto-generated when card faults are detected" />}
            </>
          )}
        </div>

        {/* Detail + approval */}
        <Card>
          <CardHeader title="MDT Detail" subtitle={selected?.mdt_title ?? selected?.node_name ?? 'Select MDT'} />
          {selected ? (
            <div className="p-4 space-y-4 text-xs">
              <StatusBadge status={selected.status} />

              <div className="space-y-1.5">
                {[
                  ['Node', selected.node_name],
                  ['Shelf / Slot', `${selected.shelf ?? '—'} / ${selected.slot ?? '—'}`],
                  ['Requested By', selected.requested_by ?? '—'],
                  ['Risk', selected.risk_assessment ?? '—'],
                  ['Est. Downtime', selected.estimated_downtime_minutes ? `${selected.estimated_downtime_minutes} min` : '—'],
                  ['Scheduled Start', selected.scheduled_start ? new Date(selected.scheduled_start).toLocaleString() : '—'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-500">{k}</span>
                    <span className="text-gray-200 font-medium">{v}</span>
                  </div>
                ))}
              </div>

              <div className="border-t border-gray-800 pt-3">
                <p className="text-gray-500 mb-1">Reason</p>
                <p className="text-gray-300 leading-relaxed">{selected.reason}</p>
              </div>

              {selected.pre_checks && (
                <div className="border-t border-gray-800 pt-3">
                  <p className="text-gray-500 mb-1.5">Pre-checks</p>
                  {selected.pre_checks.map((c, i) => (
                    <div key={i} className="flex gap-2 text-gray-300 mb-1"><span className="text-green-400">✓</span>{c}</div>
                  ))}
                </div>
              )}

              {selected.reset_procedure && (
                <div className="border-t border-gray-800 pt-3">
                  <p className="text-gray-500 mb-1.5">Reset Procedure</p>
                  {selected.reset_procedure.map((step, i) => (
                    <div key={i} className="flex gap-2 text-gray-300 mb-1">
                      <span className="text-blue-400 font-mono shrink-0">{i + 1}.</span>{step}
                    </div>
                  ))}
                </div>
              )}

              {selected.status === 'PENDING' && (
                <div className="border-t border-gray-800 pt-3 space-y-2">
                  <input value={approvedBy} onChange={e => setApprovedBy(e.target.value)} placeholder="Approved by..."
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500" />
                  <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Notes (optional)"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 resize-none" />
                  <div className="flex gap-2">
                    <button onClick={() => approve(selected.id, true)} disabled={acting}
                      className="flex-1 flex items-center justify-center gap-1 py-2 bg-green-900/40 border border-green-600 text-green-300 rounded-lg text-xs hover:bg-green-900/60 transition-colors disabled:opacity-50">
                      <CheckCircle size={12} /> Approve MDT
                    </button>
                    <button onClick={() => approve(selected.id, false)} disabled={acting}
                      className="flex-1 flex items-center justify-center gap-1 py-2 bg-red-900/40 border border-red-600 text-red-300 rounded-lg text-xs hover:bg-red-900/60 transition-colors disabled:opacity-50">
                      <XCircle size={12} /> Reject
                    </button>
                  </div>
                </div>
              )}

              {selected.status === 'APPROVED' && (
                <button onClick={() => complete(selected.id)} disabled={acting}
                  className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors disabled:opacity-50">
                  Mark as Completed
                </button>
              )}
            </div>
          ) : <EmptyState message="Select an MDT request to review" />}
        </Card>
      </div>
    </div>
  )
}

function MDTCard({ mdt, onSelect, selected }: { mdt: MDTRequest; onSelect: (m: MDTRequest) => void; selected: boolean }) {
  return (
    <div onClick={() => onSelect(mdt)}
      className={`p-4 rounded-xl border cursor-pointer transition-all mb-2 ${
        selected ? 'border-blue-500 bg-blue-950/20' :
        mdt.status === 'PENDING' ? 'border-yellow-500/40 bg-yellow-950/10 hover:border-yellow-400' :
        mdt.status === 'APPROVED' ? 'border-green-500/40 bg-green-950/10 hover:border-green-400' :
        'border-gray-700 bg-gray-900/40 hover:border-gray-600'
      }`}>
      <div className="flex items-center justify-between mb-2">
        <StatusBadge status={mdt.status} />
        <span className="text-xs text-gray-500">{formatDistanceToNow(new Date(mdt.created_at), { addSuffix: true })}</span>
      </div>
      <p className="text-sm text-white font-medium">{mdt.mdt_title ?? mdt.node_name}</p>
      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
        <span>{mdt.node_name}</span>
        {mdt.shelf && <span>Shelf {mdt.shelf}</span>}
        {mdt.slot && <span>Slot {mdt.slot}</span>}
        {mdt.estimated_downtime_minutes && <span>~{mdt.estimated_downtime_minutes} min downtime</span>}
      </div>
    </div>
  )
}
