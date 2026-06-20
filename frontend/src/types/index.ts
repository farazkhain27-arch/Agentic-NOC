export type Severity = 'CRITICAL' | 'HIGH' | 'MEMO' | 'INFO'
export type AlarmStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'SUPPRESSED'

export interface Alarm {
  id: string
  alarm_type: string
  severity: Severity
  status: AlarmStatus
  node_name: string
  node_ip?: string
  shelf?: number
  slot?: number
  port?: number
  wavelength?: string
  circuit_ids?: string
  alarm_message?: string
  rx_power?: number
  ber_value?: number
  osnr?: number
  detected_at: string
  acknowledged_at?: string
  resolved_at?: string
  jira_ticket_id?: string
  rca_summary?: string
  acknowledged_by?: string
  nms_source?: string
  equipment_type?: string
}

export interface Ticket {
  id?: string
  jira_key: string
  alarm_id?: string
  title: string
  description?: string
  priority: string
  status: string
  assignee?: string
  reporter?: string
  created_at: string
  updated_at?: string
}

export interface MigrationRequest {
  id: string
  alarm_id?: string
  source_port?: string
  target_port?: string
  target_node?: string
  affected_circuits?: string[]
  status: string
  requested_by?: string
  approved_by?: string
  estimated_restoration_minutes?: string | number
  created_at: string
  migration_steps?: string[]
  risk_level?: string
  optical_budget_margin_db?: number
}

export interface MDTRequest {
  id: string
  alarm_id?: string
  node_name: string
  shelf?: string
  slot?: string
  reason: string
  requested_by?: string
  approved_by?: string
  status: string
  scheduled_start?: string
  scheduled_end?: string
  affected_circuits?: string[]
  notes?: string
  created_at: string
  estimated_downtime_minutes?: number
  pre_checks?: string[]
  reset_procedure?: string[]
  post_checks?: string[]
  risk_assessment?: string
  mdt_title?: string
}

export interface AlarmStats {
  total: number
  active: number
  critical: number
  high: number
  memo: number
  resolved: number
  by_equipment: { OTN: number; SDH: number; DWDM: number }
}

export interface WSMessage {
  type: string
  data: any
  timestamp: string
}

export interface DailyReport {
  report_date: string
  generated_at: string
  shift_summary: {
    total_alarms: number
    critical: number
    high: number
    memo: number
    resolved: number
    pending: number
  }
  mttr_minutes: number
  mttd_seconds: number
  tickets_created: number
  migrations_executed: number
  mdts_completed: number
  top_affected_nodes: { node: string; alarm_count: number }[]
  alarm_type_breakdown: Record<string, number>
}
