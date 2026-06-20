-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Alarm severity enum
CREATE TYPE alarm_severity AS ENUM ('CRITICAL', 'HIGH', 'MEMO', 'LOW');
CREATE TYPE alarm_status AS ENUM ('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'SUPPRESSED');
CREATE TYPE ticket_status AS ENUM ('OPEN', 'IN_PROGRESS', 'PENDING_FIELD', 'RESOLVED', 'CLOSED');
CREATE TYPE ticket_type AS ENUM ('CRITICAL', 'HIGH', 'MEMO', 'CHANGE');
CREATE TYPE mdt_status AS ENUM ('REQUESTED', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE migration_status AS ENUM ('PROPOSED', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED');

-- Network elements (nodes/equipment)
CREATE TABLE network_elements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ne_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    ip_address VARCHAR(45),
    ne_type VARCHAR(32) NOT NULL,  -- SDH, OTN, DWDM
    vendor VARCHAR(64),
    site_name VARCHAR(128),
    region VARCHAR(64),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    status VARCHAR(32) DEFAULT 'UP',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ports
CREATE TABLE ports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ne_id UUID REFERENCES network_elements(id),
    shelf INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    port INTEGER NOT NULL,
    port_label VARCHAR(64),
    port_type VARCHAR(32),  -- STM-64, OTU4, 100G-DWDM
    speed_gbps DECIMAL(10,2),
    wavelength_nm DECIMAL(8,2),
    status VARCHAR(32) DEFAULT 'UP',
    is_free BOOLEAN DEFAULT FALSE,
    circuit_id VARCHAR(128),
    rx_power_dbm DECIMAL(8,2),
    tx_power_dbm DECIMAL(8,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alarms
CREATE TABLE alarms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alarm_id VARCHAR(128) UNIQUE NOT NULL,
    ne_id UUID REFERENCES network_elements(id),
    port_id UUID REFERENCES ports(id),
    alarm_code VARCHAR(64) NOT NULL,  -- LOS, LOF, AIS, BER-EXC, EQ-FAIL
    alarm_type VARCHAR(64),
    severity alarm_severity NOT NULL,
    status alarm_status DEFAULT 'ACTIVE',
    description TEXT,
    affected_circuits JSONB DEFAULT '[]',
    pm_data JSONB DEFAULT '{}',       -- rx_power, ber, osnr, q_factor
    raw_nms_data JSONB DEFAULT '{}',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    ticket_id VARCHAR(64),
    agent_rca TEXT,
    agent_confidence DECIMAL(5,2),
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tickets
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_number VARCHAR(64) UNIQUE NOT NULL,
    jira_key VARCHAR(64),
    alarm_id UUID REFERENCES alarms(id),
    ticket_type ticket_type NOT NULL,
    status ticket_status DEFAULT 'OPEN',
    title VARCHAR(256) NOT NULL,
    description TEXT,
    impact_statement TEXT,
    rfo TEXT,  -- Reason for outage
    resolution TEXT,
    assignee VARCHAR(128),
    reporter VARCHAR(128),
    steps_taken JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Traffic migrations
CREATE TABLE migrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(id),
    alarm_id UUID REFERENCES alarms(id),
    source_port_id UUID REFERENCES ports(id),
    target_port_id UUID REFERENCES ports(id),
    affected_circuits JSONB DEFAULT '[]',
    migration_plan TEXT,
    status migration_status DEFAULT 'PROPOSED',
    proposed_by VARCHAR(128) DEFAULT 'AI-Agent',
    approved_by VARCHAR(128),
    approval_notes TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    pre_migration_pm JSONB DEFAULT '{}',
    post_migration_pm JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MDT (Maintenance Down Time)
CREATE TABLE mdts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mdt_number VARCHAR(64) UNIQUE NOT NULL,
    ticket_id UUID REFERENCES tickets(id),
    alarm_id UUID REFERENCES alarms(id),
    ne_id UUID REFERENCES network_elements(id),
    port_id UUID REFERENCES ports(id),
    title VARCHAR(256) NOT NULL,
    description TEXT,
    maintenance_type VARCHAR(64),  -- CARD_RESET, PORT_RESET, UPGRADE, REPLACEMENT
    affected_services JSONB DEFAULT '[]',
    status mdt_status DEFAULT 'REQUESTED',
    requested_by VARCHAR(128),
    approved_by VARCHAR(128),
    approval_notes TEXT,
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    commands_executed JSONB DEFAULT '[]',
    post_mdt_verification TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily reports
CREATE TABLE daily_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_date DATE NOT NULL UNIQUE,
    total_alarms INTEGER DEFAULT 0,
    critical_alarms INTEGER DEFAULT 0,
    high_alarms INTEGER DEFAULT 0,
    memo_alarms INTEGER DEFAULT 0,
    tickets_opened INTEGER DEFAULT 0,
    tickets_resolved INTEGER DEFAULT 0,
    migrations_performed INTEGER DEFAULT 0,
    mdts_performed INTEGER DEFAULT 0,
    avg_mttr_minutes DECIMAL(10,2),
    top_issues JSONB DEFAULT '[]',
    report_content TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent event log
CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alarm_id UUID REFERENCES alarms(id),
    agent_name VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    langsmith_run_id VARCHAR(128),
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RCA knowledge base (for pgvector similarity search)
CREATE TABLE rca_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alarm_pattern VARCHAR(256) NOT NULL,
    root_cause TEXT NOT NULL,
    resolution_steps TEXT NOT NULL,
    ne_type VARCHAR(32),
    alarm_codes JSONB DEFAULT '[]',
    success_rate DECIMAL(5,2) DEFAULT 100.0,
    use_count INTEGER DEFAULT 0,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_alarms_status ON alarms(status);
CREATE INDEX idx_alarms_severity ON alarms(severity);
CREATE INDEX idx_alarms_detected_at ON alarms(detected_at DESC);
CREATE INDEX idx_alarms_ne_id ON alarms(ne_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_agent_events_alarm ON agent_events(alarm_id);
CREATE INDEX idx_rca_embedding ON rca_knowledge USING ivfflat (embedding vector_cosine_ops);

-- Seed network elements
INSERT INTO network_elements (ne_id, name, ip_address, ne_type, vendor, site_name, region) VALUES
('NE-JED-001', 'JED-CORE-SDH-01', '10.10.1.1', 'SDH', 'Ciena', 'Jeddah Core', 'West'),
('NE-JED-002', 'JED-CORE-OTN-01', '10.10.1.2', 'OTN', 'Nokia', 'Jeddah Core', 'West'),
('NE-JED-003', 'JED-DWDM-01', '10.10.1.3', 'DWDM', 'Ciena', 'Jeddah Exchange', 'West'),
('NE-RUH-001', 'RUH-CORE-SDH-01', '10.20.1.1', 'SDH', 'Huawei', 'Riyadh Core', 'Central'),
('NE-RUH-002', 'RUH-CORE-OTN-01', '10.20.1.2', 'OTN', 'Nokia', 'Riyadh Core', 'Central'),
('NE-RUH-003', 'RUH-DWDM-01', '10.20.1.3', 'DWDM', 'Infinera', 'Riyadh Exchange', 'Central'),
('NE-DAM-001', 'DAM-CORE-OTN-01', '10.30.1.1', 'OTN', 'Ciena', 'Dammam Core', 'East'),
('NE-MED-001', 'MED-SDH-01', '10.40.1.1', 'SDH', 'Huawei', 'Madinah Site', 'West');

-- Seed ports
INSERT INTO ports (ne_id, shelf, slot, port, port_label, port_type, speed_gbps, status, is_free, rx_power_dbm, tx_power_dbm)
SELECT ne.id, shelf, slot, port, 
    format('%s/%s/%s', shelf, slot, port),
    CASE WHEN ne.ne_type = 'DWDM' THEN '100G-DWDM' WHEN ne.ne_type = 'OTN' THEN 'OTU4' ELSE 'STM-64' END,
    CASE WHEN ne.ne_type = 'DWDM' THEN 100 WHEN ne.ne_type = 'OTN' THEN 100 ELSE 10 END,
    'UP', FALSE,
    -15.0 + (random() * 5)::decimal(8,2),
    0.0 + (random() * 2)::decimal(8,2)
FROM network_elements ne,
    generate_series(1, 2) shelf,
    generate_series(1, 4) slot,
    generate_series(1, 4) port;

-- Seed RCA knowledge base
INSERT INTO rca_knowledge (alarm_pattern, root_cause, resolution_steps, ne_type, alarm_codes) VALUES
('LOS on SDH port after sudden drop in Rx power', 'Fibre cut or connector failure on the upstream span. Physical layer loss of light reaching the receiver.', '1. Check optical Rx power on NMS\n2. OTDR test on affected span\n3. Dispatch field team for fibre inspection\n4. Replace connector or repair fibre splice', 'SDH', '["LOS"]'),
('BER-EXC with degraded OSNR on DWDM channel', 'EDFA gain tilt or amplifier saturation causing noise accumulation on specific wavelengths.', '1. Check EDFA output power on each span\n2. Review OSNR per channel via OSA\n3. Adjust EDFA gain settings\n4. Check for channel count changes', 'DWDM', '["BER-EXC"]'),
('EQ-FAIL on OTN line card with port stuck', 'Card hardware fault — possible memory corruption or firmware crash on the line card.', '1. Confirm no live traffic on card ports\n2. If traffic present: migrate to free ports first\n3. Raise MDT for card reset\n4. Execute card reset via NMS CLI\n5. Monitor post-reset port recovery', 'OTN', '["EQ-FAIL"]'),
('LOF following maintenance window on SDH node', 'Framing mismatch introduced during configuration change — SDH overhead bytes not aligned.', '1. Check SDH section overhead config\n2. Verify J0/J1 trace bytes match end-to-end\n3. Check synchronization source\n4. Re-apply factory framing config if needed', 'SDH', '["LOF"]'),
('AIS cascade from single upstream LOS', 'Downstream propagation of upstream LOS — AIS is inserted by intermediate nodes indicating upstream failure.', '1. Trace alarm source upstream to root LOS\n2. Do not act on AIS alarms independently\n3. Resolve root LOS — AIS will clear automatically', NULL, '["AIS", "LOS"]');
