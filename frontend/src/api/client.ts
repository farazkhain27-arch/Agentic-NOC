import { MigrationRequest, MDTRequest } from '../types'

const BASE = '/api/v1'

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
    ...opts,
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = {
  alarms: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : ''
      return req<any[]>(`/alarms/${qs}`)
    },
    stats: () => req<any>('/alarms/stats'),
    acknowledge: (id: string) => req<any>(`/alarms/${id}/acknowledge`, { method: 'POST' }),
    resolve: (id: string) => req<any>(`/alarms/${id}/resolve`, { method: 'POST' }),
  },
  tickets: {
    list: () => req<any[]>('/tickets/'),
    stats: () => req<any>('/tickets/stats'),
    updateStatus: (id: string, status: string) =>
      req<any>(`/tickets/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  },
  migration: {
    list: () => req<MigrationRequest[]>('/migration/'),
    pending: () => req<MigrationRequest[]>('/migration/pending'),
    approve: (id: string, approved: boolean, approvedBy: string, notes?: string) =>
      req<MigrationRequest>(`/migration/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved, approved_by: approvedBy, notes }),
      }),
  },
  mdt: {
    list: () => req<MDTRequest[]>('/mdt/'),
    create: (data: any) => req<MDTRequest>('/mdt/', { method: 'POST', body: JSON.stringify(data) }),
    approve: (id: string, approved: boolean, approvedBy: string, notes?: string) =>
      req<MDTRequest>(`/mdt/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved, approved_by: approvedBy, notes }),
      }),
    complete: (id: string) => req<MDTRequest>(`/mdt/${id}/complete`, { method: 'POST' }),
  },
  reports: {
    daily: () => req<any>('/reports/daily'),
    trend: () => req<any[]>('/reports/trend'),
  },
}
