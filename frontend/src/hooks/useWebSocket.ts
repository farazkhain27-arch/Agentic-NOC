import { useEffect, useRef } from 'react'
import { useNOCStore } from '../store/nocStore'
import { WSMessage } from '../types'

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const { setWsConnected, addAlarm, addTicket, addLiveFeedEntry, setPendingApprovals, migrations, mdts } = useNOCStore()

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws`

    const connect = () => {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => setWsConnected(true)
      ws.current.onclose = () => {
        setWsConnected(false)
        setTimeout(connect, 3000) // Auto-reconnect
      }
      ws.current.onerror = () => ws.current?.close()

      ws.current.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          addLiveFeedEntry(msg)

          if (msg.type === 'alarm_processed' && msg.data?.alarm) {
            addAlarm(msg.data.alarm)
            if (msg.data.ticket) addTicket(msg.data.ticket)
          }

          // Count pending approvals
          const pendingMig = migrations.filter(m => m.status === 'PENDING_APPROVAL').length
          const pendingMdt = mdts.filter(m => m.status === 'PENDING').length
          setPendingApprovals(pendingMig + pendingMdt)
        } catch (e) {
          console.error('WS parse error', e)
        }
      }
    }

    connect()
    return () => ws.current?.close()
  }, [])
}
