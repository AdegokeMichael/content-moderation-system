-- Content Moderation System Database Schema
-- PostgreSQL 15+

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Main content table
CREATE TABLE IF NOT EXISTS content (
    content_id UUID PRIMARY KEY,
    author_id VARCHAR(100) NOT NULL,
    content_text TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    classification VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    toxicity_score FLOAT NOT NULL,
    spam_score FLOAT NOT NULL,
    sentiment VARCHAR(50) NOT NULL,
    action_taken VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_content_author ON content(author_id);
CREATE INDEX idx_content_classification ON content(classification);
CREATE INDEX idx_content_created ON content(created_at DESC);
CREATE INDEX idx_content_platform ON content(platform);
CREATE INDEX idx_content_metadata ON content USING GIN(metadata);

-- Moderation queue table
CREATE TABLE IF NOT EXISTS moderation_queue (
    queue_id UUID PRIMARY KEY,
    content_id UUID NOT NULL REFERENCES content(content_id),
    author_id VARCHAR(100) NOT NULL,
    content_text TEXT NOT NULL,
    reason VARCHAR(200) NOT NULL,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    assigned_to VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_decision VARCHAR(50),
    review_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for moderation queue
CREATE INDEX idx_queue_status ON moderation_queue(status);
CREATE INDEX idx_queue_priority ON moderation_queue(priority DESC);
CREATE INDEX idx_queue_created ON moderation_queue(created_at DESC);
CREATE INDEX idx_queue_assigned ON moderation_queue(assigned_to);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    log_id UUID PRIMARY KEY,
    content_id UUID REFERENCES content(content_id),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for audit log
CREATE INDEX idx_audit_content ON audit_log(content_id);
CREATE INDEX idx_audit_event ON audit_log(event_type);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);

-- User notifications table
CREATE TABLE IF NOT EXISTS user_notifications (
    notification_id UUID PRIMARY KEY,
    author_id VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'sent',
    read_at TIMESTAMP
);

-- Indexes for notifications
CREATE INDEX idx_notifications_author ON user_notifications(author_id);
CREATE INDEX idx_notifications_type ON user_notifications(notification_type);
CREATE INDEX idx_notifications_sent ON user_notifications(sent_at DESC);

-- User violations tracking
CREATE TABLE IF NOT EXISTS user_violations (
    author_id VARCHAR(100) NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    last_violation TIMESTAMP NOT NULL,
    first_violation TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (author_id, violation_type)
);

-- Index for violations
CREATE INDEX idx_violations_author ON user_violations(author_id);
CREATE INDEX idx_violations_count ON user_violations(count DESC);

-- Model metrics for drift monitoring
CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id UUID PRIMARY KEY,
    content_id UUID REFERENCES content(content_id),
    confidence_score FLOAT NOT NULL,
    classification VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for metrics
CREATE INDEX idx_metrics_timestamp ON model_metrics(timestamp DESC);
CREATE INDEX idx_metrics_classification ON model_metrics(classification);
CREATE INDEX idx_metrics_confidence ON model_metrics(confidence_score);

-- Social media posts tracking
CREATE TABLE IF NOT EXISTS social_media_posts (
    post_id UUID PRIMARY KEY,
    content_id UUID NOT NULL REFERENCES content(content_id),
    platforms JSONB NOT NULL,
    results JSONB NOT NULL,
    posted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for social media posts
CREATE INDEX idx_social_content ON social_media_posts(content_id);
CREATE INDEX idx_social_posted ON social_media_posts(posted_at DESC);

-- Create views for analytics

-- Overall statistics view
CREATE OR REPLACE VIEW content_statistics AS
SELECT 
    COUNT(*) as total_submissions,
    COUNT(*) FILTER (WHERE classification = 'acceptable') as acceptable_count,
    COUNT(*) FILTER (WHERE classification = 'needs_review') as review_count,
    COUNT(*) FILTER (WHERE classification = 'toxic') as toxic_count,
    COUNT(*) FILTER (WHERE classification = 'spam') as spam_count,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
    ROUND(AVG(toxicity_score)::numeric, 3) as avg_toxicity,
    ROUND(AVG(spam_score)::numeric, 3) as avg_spam,
    DATE_TRUNC('day', MIN(created_at)) as first_submission,
    DATE_TRUNC('day', MAX(created_at)) as last_submission
FROM content;

-- Daily statistics view
CREATE OR REPLACE VIEW daily_statistics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE classification = 'acceptable') as acceptable,
    COUNT(*) FILTER (WHERE classification = 'needs_review') as needs_review,
    COUNT(*) FILTER (WHERE classification = 'toxic') as toxic,
    COUNT(*) FILTER (WHERE classification = 'spam') as spam,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence
FROM content
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Model drift monitoring view
CREATE OR REPLACE VIEW model_drift_metrics AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    classification,
    COUNT(*) as prediction_count,
    ROUND(AVG(confidence_score)::numeric, 4) as avg_confidence,
    ROUND(STDDEV(confidence_score)::numeric, 4) as std_confidence,
    ROUND(MIN(confidence_score)::numeric, 4) as min_confidence,
    ROUND(MAX(confidence_score)::numeric, 4) as max_confidence
FROM model_metrics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', timestamp), classification
ORDER BY hour DESC, classification;

-- Top violators view
CREATE OR REPLACE VIEW top_violators AS
SELECT 
    author_id,
    SUM(count) as total_violations,
    COUNT(DISTINCT violation_type) as violation_types,
    MAX(last_violation) as most_recent_violation,
    MIN(first_violation) as first_violation_date
FROM user_violations
GROUP BY author_id
ORDER BY total_violations DESC
LIMIT 100;

-- Moderation queue priority view
CREATE OR REPLACE VIEW moderation_priority_queue AS
SELECT 
    q.queue_id,
    q.content_id,
    q.author_id,
    q.content_text,
    q.reason,
    q.priority,
    q.status,
    q.created_at,
    c.toxicity_score,
    c.confidence,
    COALESCE(v.total_violations, 0) as author_violation_count
FROM moderation_queue q
LEFT JOIN content c ON q.content_id = c.content_id
LEFT JOIN (
    SELECT author_id, SUM(count) as total_violations
    FROM user_violations
    GROUP BY author_id
) v ON q.author_id = v.author_id
WHERE q.status = 'pending'
ORDER BY q.priority DESC, q.created_at ASC;

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_content_timestamp
    BEFORE UPDATE ON content
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_moderation_queue_timestamp
    BEFORE UPDATE ON moderation_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Function to clean old audit logs (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get classification distribution
CREATE OR REPLACE FUNCTION get_classification_distribution(days INTEGER DEFAULT 7)
RETURNS TABLE(
    classification VARCHAR,
    count BIGINT,
    percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.classification,
        COUNT(*) as count,
        ROUND((COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER ()) * 100, 2) as percentage
    FROM content c
    WHERE c.created_at > NOW() - (days || ' days')::INTERVAL
    GROUP BY c.classification
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data for testing (optional)
-- Uncomment to populate with test data

/*
INSERT INTO content (content_id, author_id, content_text, platform, classification, confidence, toxicity_score, spam_score, sentiment, action_taken)
VALUES 
    (uuid_generate_v4(), 'user001', 'This is a great product! Highly recommended.', 'web', 'acceptable', 0.95, 0.05, 0.1, 'positive', 'approved_and_stored'),
    (uuid_generate_v4(), 'user002', 'You are completely stupid and worthless!', 'mobile', 'toxic', 0.98, 0.95, 0.15, 'negative', 'rejected_toxic'),
    (uuid_generate_v4(), 'user003', 'Click here NOW! Buy now! Limited time offer!!!', 'web', 'spam', 0.92, 0.2, 0.85, 'neutral', 'rejected_spam'),
    (uuid_generate_v4(), 'user004', 'I am not sure about this policy change.', 'web', 'needs_review', 0.65, 0.45, 0.2, 'neutral', 'queued_for_review');
*/

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO moderator_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO moderator_user;

-- Create indices for full-text search (optional)
CREATE INDEX idx_content_text_search ON content USING GIN(to_tsvector('english', content_text));

-- Performance optimization: analyze tables
ANALYZE content;
ANALYZE moderation_queue;
ANALYZE audit_log;
ANALYZE model_metrics;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema creation with all tables, indexes, views, and functions')
ON CONFLICT (version) DO NOTHING;

-- Log schema initialization
DO $$
BEGIN
    RAISE NOTICE 'Content Moderation Database Schema initialized successfully';
    RAISE NOTICE 'Schema version: 1';
    RAISE NOTICE 'Tables created: content, moderation_queue, audit_log, user_notifications, user_violations, model_metrics, social_media_posts';
    RAISE NOTICE 'Views created: content_statistics, daily_statistics, model_drift_metrics, top_violators, moderation_priority_queue';
END $$;