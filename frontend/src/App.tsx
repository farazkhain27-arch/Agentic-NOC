import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/shared/Sidebar'
import Dashboard from './components/dashboard/Dashboard'
import AlarmsPage from './components/alarms/AlarmsPage'
import TicketsPage from './components/tickets/TicketsPage'
import MigrationPage from './components/migration/MigrationPage'
import MDTPage from './components/mdt/MDTPage'
import ReportsPage from './components/reports/ReportsPage'
import { useWebSocket } from './hooks/useWebSocket'
import { useNOCStore } from './store/nocStore'
import { api } from './api/client'

function AppInner() {
  useWebSocket()
  const { setAlarms, setStats, setTickets, setMigrations, setMdts } = useNOCStore()

  // Initial data load
  useEffect(() => {
    api.alarms.list().then(setAlarms).catch(() => {})
    api.alarms.stats().then(setStats).catch(() => {})
    api.tickets.list().then(setTickets).catch(() => {})
    api.migration.list().then(setMigrations).catch(() => {})
    api.mdt.list().then(setMdts).catch(() => {})

    // Periodic refresh every 60s
    const id = setInterval(() => {
      api.alarms.stats().then(setStats).catch(() => {})
      api.migration.list().then(setMigrations).catch(() => {})
      api.mdt.list().then(setMdts).catch(() => {})
    }, 60_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex min-h-screen bg-noc-dark">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-[1400px] mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/alarms" element={<AlarmsPage />} />
            <Route path="/tickets" element={<TicketsPage />} />
            <Route path="/migration" element={<MigrationPage />} />
            <Route path="/mdt" element={<MDTPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  )
}
