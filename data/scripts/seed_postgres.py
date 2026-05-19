#!/usr/bin/env python3
"""
Seed PostgreSQL with initial schema for incident reports.
"""

import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("psycopg2 not installed. Install with: pip install psycopg2-binary")
    exit(1)


def get_connection():
    """Create PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        user=os.getenv('POSTGRES_USER', 'aerorisk'),
        password=os.getenv('POSTGRES_PASSWORD', 'aerorisk_password'),
        database=os.getenv('POSTGRES_DB', 'aerorisk_incidents')
    )


def create_schema(conn):
    """Create database schema."""
    cursor = conn.cursor()
    
    # Incident reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_reports (
            id SERIAL PRIMARY KEY,
            incident_id VARCHAR(50) UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- Event information
            event_id VARCHAR(100) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            event_timestamp TIMESTAMPTZ NOT NULL,
            
            -- User information
            user_id VARCHAR(50) NOT NULL,
            user_name VARCHAR(255),
            account_type VARCHAR(50),
            
            -- Risk assessment
            anomaly_score DECIMAL(5, 4),
            risk_score DECIMAL(5, 4) NOT NULL,
            risk_level VARCHAR(20) NOT NULL,
            
            -- Decision
            decision VARCHAR(20) NOT NULL,
            decision_reason TEXT,
            circuit_breaker_action VARCHAR(50),
            
            -- Agent outputs
            agent1_anomaly_details JSONB,
            agent2_context_bundle JSONB,
            agent3_llm_response JSONB,
            
            -- Compliance flags
            sanctions_match BOOLEAN DEFAULT FALSE,
            sanctions_matched_entity VARCHAR(255),
            compliance_violations TEXT[],
            
            -- Trade details
            symbol VARCHAR(50),
            side VARCHAR(10),
            quantity DECIMAL(20, 8),
            price DECIMAL(20, 8),
            order_value_usd DECIMAL(20, 2),
            
            -- Status
            status VARCHAR(20) DEFAULT 'OPEN',
            reviewed_by VARCHAR(100),
            reviewed_at TIMESTAMPTZ,
            resolution_notes TEXT,
            
            -- Audit
            metadata JSONB
        );
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incident_reports_created_at 
        ON incident_reports(created_at DESC);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incident_reports_user_id 
        ON incident_reports(user_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incident_reports_risk_level 
        ON incident_reports(risk_level);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incident_reports_status 
        ON incident_reports(status);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incident_reports_sanctions_match 
        ON incident_reports(sanctions_match) WHERE sanctions_match = TRUE;
    """)
    
    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            event_type VARCHAR(50) NOT NULL,
            actor_id VARCHAR(100),
            actor_type VARCHAR(50),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(100),
            old_values JSONB,
            new_values JSONB,
            ip_address INET,
            user_agent TEXT,
            metadata JSONB
        );
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp 
        ON audit_logs(timestamp DESC);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type 
        ON audit_logs(event_type);
    """)
    
    # Circuit breaker state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS circuit_breaker_state (
            id SERIAL PRIMARY KEY,
            breaker_name VARCHAR(100) UNIQUE NOT NULL,
            state VARCHAR(20) NOT NULL DEFAULT 'CLOSED',
            failure_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            last_failure_at TIMESTAMPTZ,
            last_success_at TIMESTAMPTZ,
            opened_at TIMESTAMPTZ,
            closed_at TIMESTAMPTZ,
            metadata JSONB,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    
    # Risk thresholds configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_thresholds (
            id SERIAL PRIMARY KEY,
            threshold_name VARCHAR(100) UNIQUE NOT NULL,
            threshold_value DECIMAL(5, 4) NOT NULL,
            description TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    
    # Insert default thresholds
    cursor.execute("""
        INSERT INTO risk_thresholds (threshold_name, threshold_value, description)
        VALUES 
            ('risk_threshold_low', 0.30, 'Low risk threshold - below this is ALLOW'),
            ('risk_threshold_medium', 0.60, 'Medium risk threshold - FLAG between low and high'),
            ('risk_threshold_high', 0.80, 'High risk threshold - above this is BLOCK')
        ON CONFLICT (threshold_name) DO NOTHING;
    """)
    
    conn.commit()
    cursor.close()
    print("✅ Database schema created successfully")


def main():
    """Main entry point."""
    print("Connecting to PostgreSQL...")
    
    try:
        conn = get_connection()
        print(f"Connected to {os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}")
        
        create_schema(conn)
        
        conn.close()
        print("✅ PostgreSQL seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
