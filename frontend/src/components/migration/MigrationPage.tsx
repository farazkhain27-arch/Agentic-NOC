import React, { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react'
import { useNOCStore } from '../../store/nocStore'
import { api } from '../../api/client'
import { Card, CardHeader, StatusBadge, EmptyState, Spinner } from '../shared/ui'
import { formatDistanceToNow } from 'date-fns'
import { MigrationRequest } from '../../types'

export default function MigrationPage() {
  const { migrations, setMigrations, updateMigration } = useNOCStore()
  const [loading, setLoading] = useState(false)
  const [approvedBy, setApprovedBy] = useState('NOC Engineer')
  const [notes, setNotes] = useState('')
  const [selected, setSelected] = useState<MigrationRequest | null>(null)
  const [acting, setActing] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.migration.list()
      setMigrations(data)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const pending = migrations.filter(m => m.status === 'PENDING_APPROVAL')
  const historical = migrations.filter(m => m.status !== 'PENDING_APPROVAL')

  const approve = async (id: string, approved: boolean) => {
    if (!approvedBy.trim()) return
    setActing(true)
    try {
      const updated = (await api.migration.approve(id, approved, approvedBy, notes)) as MigrationRequest
      updateMigration(id, { status: updated.status, approved_by: updated.approved_by })
      if (selected?.id === id) setSelected({ ...selected, status: updated.status })
      setNotes('')
    } finally { setActing(false) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Traffic Migration</h1>
          <p className="text-sm text-gray-400">Human-in-the-loop approval for AI-proposed migrations</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 text-sm transition-colors">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {pending.length > 0 && (
        <div className="rounded-xl border border-orange-500/40 bg-orange-950/10 p-4 flex items-center gap-3">
          <AlertTriangle className="text-orange-400 shrink-0" size={20} />
          <p className="text-orange-300 text-sm font-medium">
            {pending.length} migration plan{pending.length > 1 ? 's' : ''} awaiting your approval
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* List */}
        <div className="xl:col-span-2 space-y-3">
          {loading ? <Spinner /> : (
            <>
              {pending.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-orange-400 mb-2 uppercase tracking-wider">Pending Approval</h2>
                  {pending.map(m => (
                    <MigrationCard key={m.id} migration={m} onSelect={setSelected} selected={selected?.id === m.id} />
                  ))}
                </div>
              )}
              {historical.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wider">History</h2>
                  {historical.map(m => (
                    <MigrationCard key={m.id} migration={m} onSelect={setSelected} selected={selected?.id === m.id} />
                  ))}
                </div>
              )}
              {migrations.length === 0 && <EmptyState message="No migration requests yet — generated automatically by AI Migration Agent when hardware failures detected" />}
            </>
          )}
        </div>

        {/* Approval panel */}
        <Card>
          <CardHeader title="Approval Panel" subtitle={selected ? `${selected.source_port} → ${selected.target_port}` : 'Select a migration'} />
          {selected ? (
            <div className="p-4 space-y-4">
              <StatusBadge status={selected.status} />

              <div className="space-y-2 text-xs">
                {[
                  ['Risk Level', selected.risk_level ?? '—'],
                  ['Optical Margin', selected.optical_budget_margin_db != null ? `${selected.optical_budget_margin_db} dB` : '—'],
                  ['Est. Restoration', `${selected.estimated_restoration_minutes} min`],
                  ['Requested By', selected.requested_by ?? '—'],
                  ['Created', formatDistanceToNow(new Date(selected.created_at), { addSuffix: true })],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-gray-500">{k}</span>
                    <span className={`font-medium ${k === 'Risk Level' && v === 'HIGH' ? 'text-red-400' : k === 'Risk Level' && v === 'MEDIUM' ? 'text-orange-400' : 'text-gray-200'}`}>{v}</span>
                  </div>
                ))}
              </div>

              {selected.affected_circuits && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Affected Circuits</p>
                  <div className="flex flex-wrap gap-1">
                    {(Array.isArray(selected.affected_circuits) ? selected.affected_circuits : []).map((c: string) => (
                      <span key={c} className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-xs font-mono">{c}</span>
                    ))}
                  </div>
                </div>
              )}

              {selected.migration_steps && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Migration Steps</p>
                  <ol className="space-y-1">
                    {selected.migration_steps.map((step, i) => (
                      <li key={i} className="flex gap-2 text-xs text-gray-300">
                        <span className="text-blue-400 font-mono shrink-0">{i + 1}.</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {selected.status === 'PENDING_APPROVAL' && (
                <div className="border-t border-gray-800 pt-4 space-y-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Approved by *</label>
                    <input value={approvedBy} onChange={e => setApprovedBy(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Notes (optional)</label>
                    <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 resize-none" />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => approve(selected.id, true)} disabled={acting}
                      className="flex-1 flex items-center justify-center gap-2 py-2 bg-green-900/40 border border-green-600 text-green-300 rounded-lg text-sm hover:bg-green-900/60 transition-colors disabled:opacity-50">
                      <CheckCircle size={14} /> Approve
                    </button>
                    <button onClick={() => approve(selected.id, false)} disabled={acting}
                      className="flex-1 flex items-center justify-center gap-2 py-2 bg-red-900/40 border border-red-600 text-red-300 rounded-lg text-sm hover:bg-red-900/60 transition-colors disabled:opacity-50">
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                </div>
              )}
              {selected.approved_by && (
                <p className="text-xs text-gray-500 border-t border-gray-800 pt-3">
                  {selected.status === 'APPROVED' ? '✓ Approved' : '✗ Rejected'} by {selected.approved_by}
                </p>
              )}
            </div>
          ) : <EmptyState message="Select a migration request to review and approve" />}
        </Card>
      </div>
    </div>
  )
}

function MigrationCard({ migration, onSelect, selected }: { migration: MigrationRequest; onSelect: (m: MigrationRequest) => void; selected: boolean }) {
  return (
    <div onClick={() => onSelect(migration)}
      className={`p-4 rounded-xl border cursor-pointer transition-all mb-2 ${
        selected ? 'border-blue-500 bg-blue-950/20' :
        migration.status === 'PENDING_APPROVAL' ? 'border-orange-500/40 bg-orange-950/10 hover:border-orange-400' :
        'border-gray-700 bg-gray-900/40 hover:border-gray-600'
      }`}>
      <div className="flex items-center justify-between mb-2">
        <StatusBadge status={migration.status} />
        <span className="text-xs text-gray-500">{formatDistanceToNow(new Date(migration.created_at), { addSuffix: true })}</span>
      </div>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded text-gray-300">{migration.source_port ?? '—'}</span>
        <ArrowRight size={14} className="text-gray-500 shrink-0" />
        <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded text-gray-300">{migration.target_port ?? '—'}</span>
      </div>
      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
        <span>{migration.target_node}</span>
        <span>Risk: <span className={migration.risk_level === 'HIGH' ? 'text-red-400' : migration.risk_level === 'MEDIUM' ? 'text-orange-400' : 'text-green-400'}>{migration.risk_level}</span></span>
        <span>~{migration.estimated_restoration_minutes} min</span>
      </div>
    </div>
  )
}
