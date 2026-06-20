import { create } from 'zustand'
import { Alarm, Ticket, MigrationRequest, MDTRequest, AlarmStats, WSMessage } from '../types'

interface NOCStore {
  wsConnected: boolean
  setWsConnected: (v: boolean) => void
  alarms: Alarm[]
  stats: AlarmStats | null
  addAlarm: (alarm: Alarm) => void
  setAlarms: (alarms: Alarm[]) => void
  setStats: (stats: AlarmStats) => void
  updateAlarmStatus: (id: string, status: string) => void
  tickets: Ticket[]
  setTickets: (tickets: Ticket[]) => void
  addTicket: (ticket: Ticket) => void
  migrations: MigrationRequest[]
  setMigrations: (m: MigrationRequest[]) => void
  updateMigration: (id: string, updates: Partial<MigrationRequest>) => void
  mdts: MDTRequest[]
  setMdts: (m: MDTRequest[]) => void
  updateMdt: (id: string, updates: Partial<MDTRequest>) => void
  liveFeed: WSMessage[]
  addLiveFeedEntry: (msg: WSMessage) => void
  pendingApprovals: number
  setPendingApprovals: (n: number) => void
}

export const useNOCStore = create<NOCStore>((set) => ({
  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),
  alarms: [],
  stats: null,
  addAlarm: (alarm) => set((s) => ({ alarms: [alarm, ...s.alarms].slice(0, 200) })),
  setAlarms: (alarms) => set({ alarms }),
  setStats: (stats) => set({ stats }),
  updateAlarmStatus: (id, status) => set((s) => ({
    alarms: s.alarms.map((a) => a.id === id ? { ...a, status: status as any } : a)
  })),
  tickets: [],
  setTickets: (tickets) => set({ tickets }),
  addTicket: (ticket) => set((s) => ({ tickets: [ticket, ...s.tickets].slice(0, 100) })),
  migrations: [],
  setMigrations: (migrations) => set({ migrations }),
  updateMigration: (id, updates) => set((s) => ({
    migrations: s.migrations.map((m) => m.id === id ? { ...m, ...updates } : m)
  })),
  mdts: [],
  setMdts: (mdts) => set({ mdts }),
  updateMdt: (id, updates) => set((s) => ({
    mdts: s.mdts.map((m) => m.id === id ? { ...m, ...updates } : m)
  })),
  liveFeed: [],
  addLiveFeedEntry: (msg) => set((s) => ({ liveFeed: [msg, ...s.liveFeed].slice(0, 50) })),
  pendingApprovals: 0,
  setPendingApprovals: (n) => set({ pendingApprovals: n }),
}))
