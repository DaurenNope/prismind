-- Create system_errors table for error tracking and dashboard
CREATE TABLE IF NOT EXISTS system_errors (
  id BIGSERIAL PRIMARY KEY,
  component TEXT NOT NULL,
  error_type TEXT NOT NULL,
  message TEXT NOT NULL,
  stack_trace TEXT,
  severity TEXT NOT NULL DEFAULT 'error' CHECK (severity IN ('critical', 'error', 'warning', 'info')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'ignored')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  resolution_notes TEXT,
  metadata JSONB,
  count INTEGER DEFAULT 1
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_system_errors_component ON system_errors(component);
CREATE INDEX IF NOT EXISTS idx_system_errors_severity ON system_errors(severity);
CREATE INDEX IF NOT EXISTS idx_system_errors_status ON system_errors(status);
CREATE INDEX IF NOT EXISTS idx_system_errors_created_at ON system_errors(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_errors_error_type ON system_errors(error_type);

-- Rollback (for reference):
-- DROP TABLE IF EXISTS system_errors;

