-- backend/migrations/001_timescaledb_setup.sql
-- Create TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Drop existing tables if they exist (careful in production!)
DROP TABLE IF EXISTS sensor_readings_new;
DROP TABLE IF EXISTS anomalies_new;
DROP TABLE IF EXISTS ml_models_new;
DROP TABLE IF EXISTS alerts_new;

-- Sensor readings table optimized for time-series
CREATE TABLE sensor_readings_new (
    id BIGSERIAL,
    machine_id VARCHAR(100) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    temperature FLOAT,
    vibration FLOAT,
    power FLOAT,
    pressure FLOAT,
    speed FLOAT,
    efficiency FLOAT,
    custom_fields JSONB,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('sensor_readings_new', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- Create indexes for fast queries
CREATE INDEX idx_sensor_readings_machine_time ON sensor_readings_new (machine_id, timestamp DESC);
CREATE INDEX idx_sensor_readings_client_time ON sensor_readings_new (client_id, timestamp DESC);
CREATE INDEX idx_sensor_readings_type_time ON sensor_readings_new (sensor_type, timestamp DESC);
CREATE INDEX idx_sensor_readings_temp ON sensor_readings_new (temperature) WHERE temperature IS NOT NULL;
CREATE INDEX idx_sensor_readings_vibration ON sensor_readings_new (vibration) WHERE vibration IS NOT NULL;
CREATE INDEX idx_sensor_readings_power ON sensor_readings_new (power) WHERE power IS NOT NULL;

-- Anomalies table
CREATE TABLE anomalies_new (
    id BIGSERIAL PRIMARY KEY,
    machine_id VARCHAR(100) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    timestamp TIMESTAMPTZ NOT NULL,
    sensor_values JSONB,
    description TEXT,
    severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved', 'false_positive')),
    model_version VARCHAR(50),
    threshold_values JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(100)
);

-- Create indexes for anomalies
CREATE INDEX idx_anomalies_machine_time ON anomalies_new (machine_id, timestamp DESC);
CREATE INDEX idx_anomalies_client_status ON anomalies_new (client_id, status);
CREATE INDEX idx_anomalies_severity_time ON anomalies_new (severity, timestamp DESC);

-- ML Models metadata
CREATE TABLE ml_models_new (
    id BIGSERIAL PRIMARY KEY,
    machine_id VARCHAR(100) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    accuracy_score FLOAT CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    precision_score FLOAT CHECK (precision_score >= 0 AND precision_score <= 1),
    recall_score FLOAT CHECK (recall_score >= 0 AND recall_score <= 1),
    f1_score FLOAT CHECK (f1_score >= 0 AND f1_score <= 1),
    training_data_count INTEGER,
    model_file_path TEXT,
    model_size_mb FLOAT,
    hyperparameters JSONB,
    feature_importance JSONB,
    training_duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    deployed_at TIMESTAMPTZ,
    performance_metrics JSONB
);

-- Create indexes for ML models
CREATE INDEX idx_ml_models_machine ON ml_models_new (machine_id, is_active);
CREATE INDEX idx_ml_models_client ON ml_models_new (client_id, model_type);
CREATE UNIQUE INDEX idx_ml_models_active ON ml_models_new (machine_id, model_type) WHERE is_active = true;

-- Alerts table
CREATE TABLE alerts_new (
    id BIGSERIAL PRIMARY KEY,
    machine_id VARCHAR(100) NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    notification_sent BOOLEAN DEFAULT false,
    escalated BOOLEAN DEFAULT false,
    escalated_at TIMESTAMPTZ,
    related_anomaly_id BIGINT REFERENCES anomalies_new(id),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for alerts
CREATE INDEX idx_alerts_machine_time ON alerts_new (machine_id, timestamp DESC);
CREATE INDEX idx_alerts_client_status ON alerts_new (client_id, resolved, acknowledged);
CREATE INDEX idx_alerts_severity_time ON alerts_new (severity, timestamp DESC);
CREATE INDEX idx_alerts_unresolved ON alerts_new (resolved, acknowledged) WHERE resolved = false;

-- Clients table (multi-tenancy)
CREATE TABLE clients_new (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100),
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    subscription_tier VARCHAR(50) DEFAULT 'starter',
    max_machines INTEGER DEFAULT 25,
    api_key_hash VARCHAR(255),
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Create indexes for clients
CREATE INDEX idx_clients_active ON clients_new (is_active);
CREATE INDEX idx_clients_tier ON clients_new (subscription_tier);

-- Machines table
CREATE TABLE machines_new (
    id BIGSERIAL PRIMARY KEY,
    machine_id VARCHAR(100) UNIQUE NOT NULL,
    client_id VARCHAR(100) NOT NULL REFERENCES clients_new(client_id),
    machine_name VARCHAR(200) NOT NULL,
    machine_type VARCHAR(100),
    location VARCHAR(200),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    installation_date DATE,
    specifications JSONB,
    maintenance_schedule JSONB,
    is_active BOOLEAN DEFAULT true,
    last_maintenance DATE,
    next_maintenance DATE,
    criticality_level VARCHAR(20) DEFAULT 'medium' CHECK (criticality_level IN ('low', 'medium', 'high', 'critical')),
    operating_hours FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for machines
CREATE INDEX idx_machines_client ON machines_new (client_id, is_active);
CREATE INDEX idx_machines_type ON machines_new (machine_type);
CREATE INDEX idx_machines_criticality ON machines_new (criticality_level);

-- Users table (for authentication)
CREATE TABLE users_new (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    client_id VARCHAR(100) REFERENCES clients_new(client_id),
    role VARCHAR(50) DEFAULT 'operator' CHECK (role IN ('admin', 'client_admin', 'operator', 'viewer')),
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMPTZ,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for users
CREATE INDEX idx_users_client ON users_new (client_id, is_active);
CREATE INDEX idx_users_role ON users_new (role);
CREATE INDEX idx_users_email ON users_new (email) WHERE is_active = true;

-- Automatic data retention policies
-- Keep sensor readings for 2 years
SELECT add_retention_policy('sensor_readings_new', INTERVAL '2 years');

-- Keep anomalies for 5 years (important for analysis)
-- Note: Regular tables don't support retention policies, but we can create a cleanup job

-- Create materialized views for common queries
-- Daily aggregations for dashboard performance
CREATE MATERIALIZED VIEW daily_machine_stats AS
SELECT 
    machine_id,
    client_id,
    DATE(timestamp) as date,
    COUNT(*) as reading_count,
    AVG(temperature) as avg_temperature,
    MAX(temperature) as max_temperature,
    MIN(temperature) as min_temperature,
    AVG(vibration) as avg_vibration,
    MAX(vibration) as max_vibration,
    AVG(power) as avg_power,
    MAX(power) as max_power,
    COUNT(CASE WHEN temperature > 80 THEN 1 END) as high_temp_count,
    COUNT(CASE WHEN vibration > 5 THEN 1 END) as high_vibration_count
FROM sensor_readings_new 
GROUP BY machine_id, client_id, DATE(timestamp);

-- Create index on materialized view
CREATE INDEX idx_daily_stats_machine_date ON daily_machine_stats (machine_id, date DESC);

-- Hourly aggregations for real-time dashboards
CREATE MATERIALIZED VIEW hourly_machine_stats AS
SELECT 
    machine_id,
    client_id,
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as reading_count,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(power) as avg_power,
    STDDEV(temperature) as temp_stddev,
    STDDEV(vibration) as vibration_stddev,
    STDDEV(power) as power_stddev
FROM sensor_readings_new 
GROUP BY machine_id, client_id, DATE_TRUNC('hour', timestamp);

-- Create index on hourly stats
CREATE INDEX idx_hourly_stats_machine_hour ON hourly_machine_stats (machine_id, hour DESC);

-- Triggers for updating materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS TRIGGER AS $$
BEGIN
    -- Refresh views asynchronously to avoid blocking
    PERFORM pg_notify('refresh_views', NEW.machine_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on sensor_readings
CREATE TRIGGER trigger_refresh_views
    AFTER INSERT ON sensor_readings_new
    FOR EACH ROW
    EXECUTE FUNCTION refresh_materialized_views();

-- Create function to automatically refresh materialized views
CREATE OR REPLACE FUNCTION refresh_stats_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY hourly_machine_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_machine_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO aispark_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aispark_app;

COMMENT ON TABLE sensor_readings_new IS 'Time-series optimized sensor readings with TimescaleDB';
COMMENT ON TABLE anomalies_new IS 'ML-detected anomalies with confidence scores and metadata';
COMMENT ON TABLE ml_models_new IS 'Machine learning model metadata and performance metrics';
COMMENT ON TABLE alerts_new IS 'System alerts and notifications with escalation tracking';
COMMENT ON TABLE clients_new IS 'Multi-tenant client management with subscription tiers';
COMMENT ON TABLE machines_new IS 'Machine registry with maintenance scheduling';
COMMENT ON TABLE users_new IS 'User authentication and role-based access control';
