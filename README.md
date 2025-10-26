# AI-Powered Content Moderation System

## 📋 Overview

A production-ready, end-to-end AI-powered content moderation system that automatically analyzes, classifies, and takes action on user-generated content. The system uses state-of-the-art transformer models for toxicity detection, spam classification, and sentiment analysis.

### Key Features

- ✅ **Real-time Content Analysis** - Instant classification using ML models
- 🎯 **Multi-Class Classification** - Toxicity, spam, and sentiment analysis
- 🔄 **Automated Workflow** - From ingestion to action without human intervention
- 📊 **Comprehensive Logging** - Full audit trail for compliance
- 🚀 **Social Media Integration** - Auto-post approved content to Facebook & X
- 🐳 **Containerized Deployment** - Docker-based for easy deployment
- 📈 **Model Drift Monitoring** - Track confidence scores over time
- 🧪 **Automated Testing** - Comprehensive test suite included

---

## 🏗️ System Architecture

```
┌─────────────────┐
│  User Content   │
│   (Webhook)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│         FastAPI Service                      │
│  ┌──────────────────────────────────────┐  │
│  │  1. Content Validation & Ingestion   │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ▼                           │
│  ┌──────────────────────────────────────┐  │
│  │  2. ML Classification Service        │  │
│  │     - Toxicity Detection (BERT)      │  │
│  │     - Spam Detection (Patterns)      │  │
│  │     - Sentiment Analysis             │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ▼                           │
│  ┌──────────────────────────────────────┐  │
│  │  3. Business Logic Engine            │  │
│  │     - Acceptable → Store & Post      │  │
│  │     - Needs Review → Queue           │  │
│  │     - Toxic/Spam → Flag & Notify     │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 ▼                           │
│  ┌──────────────────────────────────────┐  │
│  │  4. Storage & External Actions       │  │
│  │     - PostgreSQL Database            │  │
│  │     - Social Media APIs              │  │
│  │     - User Notifications             │  │
│  │     - Audit Logging                  │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Classification Flow

```
Content Input
     ↓
[Toxicity Score] → High (>0.8) → REJECT (Toxic)
     ↓
[Spam Score] → High (>0.7) → REJECT (Spam)
     ↓
[Confidence] → Low (<0.6) → REVIEW (Needs Human Review)
     ↓
Medium Scores → REVIEW (Needs Human Review)
     ↓
All Clear → ACCEPT (Approved)
     ↓
Post to Social Media
```

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended for ML models)
- (Optional) Facebook & Twitter API credentials for social media posting

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourorg/content-moderation-system.git
cd content-moderation-system
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

3. **Build and start services**
```bash
docker-compose up -d
```

4. **Verify deployment**
```bash
# Check service health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","timestamp":"2025-..."}
```

5. **View logs**
```bash
docker-compose logs -f api
```

### First Request

```bash
curl -X POST http://localhost:8000/api/v1/content/submit \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a great product! I love it!",
    "author_id": "user123",
    "platform": "web"
  }'
```

**Expected Response:**
```json
{
  "content_id": "a1b2c3d4-...",
  "classification": "acceptable",
  "confidence": 0.95,
  "toxicity_score": 0.05,
  "spam_score": 0.10,
  "sentiment": "positive",
  "action_taken": "approved_and_stored",
  "timestamp": "2025-10-26T12:00:00",
  "details": {
    "processing_time_seconds": 0.234,
    "model_version": "1.0.0"
  }
}
```

---

## 📚 API Reference

### Endpoints

#### 1. Submit Content (Main Webhook)
```http
POST /api/v1/content/submit
```

**Request Body:**
```json
{
  "content": "string (required, 1-5000 chars)",
  "author_id": "string (required)",
  "platform": "string (optional, default: web)",
  "metadata": {
    "key": "value"
  }
}
```

**Response:** Classification result with action taken

#### 2. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-26T12:00:00"
}
```

#### 3. Statistics Overview
```http
GET /api/v1/stats/overview
```

**Response:** Aggregated statistics for last 24 hours

#### 4. Model Drift Metrics
```http
GET /api/v1/stats/model-drift
```

**Response:** Confidence score trends for model monitoring

---

## 🧠 ML Model Details

### Models Used

1. **Toxicity Detection**
   - Model: `unitary/toxic-bert`
   - Task: Binary classification (toxic/non-toxic)
   - Threshold: 0.8 (high), 0.6 (medium)

2. **Sentiment Analysis**
   - Model: `distilbert-base-uncased-finetuned-sst-2-english`
   - Task: Sentiment classification (positive/negative)
   - Used for context in final decision

3. **Spam Detection**
   - Approach: Pattern matching + heuristics
   - Features: URL count, keyword patterns, repetition, caps ratio
   - Threshold: 0.7 (high), 0.5 (medium)

### Classification Rules

| Condition | Classification | Action |
|-----------|----------------|---------|
| Toxicity ≥ 0.8 | `toxic` | Reject, flag, notify user |
| Spam ≥ 0.7 | `spam` | Reject, flag, notify user |
| Toxicity 0.6-0.8 OR Spam 0.5-0.7 | `needs_review` | Queue for human review |
| Confidence < 0.6 | `needs_review` | Queue for human review |
| All thresholds passed | `acceptable` | Store, post to social media |

---

## 📊 Database Schema

### Tables

1. **content** - All submitted content with classifications
2. **moderation_queue** - Content awaiting human review
3. **audit_log** - Complete audit trail of all actions
4. **user_notifications** - User notification history
5. **user_violations** - Violation counters per user
6. **model_metrics** - Model performance tracking
7. **social_media_posts** - Social media posting history

### Views

- `content_statistics` - Overall system statistics
- `daily_statistics` - Daily breakdown of classifications
- `model_drift_metrics` - Model confidence trends
- `top_violators` - Users with most violations
- `moderation_priority_queue` - Prioritized review queue

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `postgres` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `content_moderation` |
| `DB_USER` | Database user | `moderator` |
| `DB_PASSWORD` | Database password | (required) |
| `FACEBOOK_TOKEN` | Facebook API token | (optional) |
| `TWITTER_API_KEY` | Twitter API key | (optional) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `WORKERS` | Uvicorn workers | `2` |

### Threshold Tuning

Adjust classification thresholds in code (`ml_classifier.py`):

```python
self.thresholds = {
    'toxicity_high': 0.8,      # Decrease for stricter moderation
    'toxicity_medium': 0.6,
    'spam_high': 0.7,
    'confidence_low': 0.6
}
```

---

## 🧪 Testing

### Run Automated Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run full test suite
python test_moderation.py

# Run specific test class
pytest test_moderation.py::TestContentModerationAPI -v

# Run with coverage
pytest test_moderation.py --cov=. --cov-report=html
```

### Test Cases Included

- ✅ Health check and API availability
- ✅ Acceptable content classification
- ✅ Toxic content detection
- ✅ Spam detection
- ✅ Ambiguous content handling
- ✅ Input validation
- ✅ Concurrent request handling
- ✅ Statistics endpoints
- ✅ Model drift metrics
- ✅ Special characters and unicode
- ✅ Metadata handling
- ✅ Classification accuracy benchmarks

### Manual Testing

Use the included test script:

```bash
# Generate test requests
curl -X POST http://localhost:8000/api/v1/content/submit \
  -H "Content-Type: application/json" \
  -d @test_samples/toxic_content.json
```

---

## 📈 Monitoring & Observability

### Logging

All events are logged in structured JSON format:

```json
{
  "timestamp": "2025-10-26T12:00:00",
  "level": "INFO",
  "content_id": "abc123",
  "event": "content_classified",
  "classification": "acceptable",
  "confidence": 0.95
}
```

### Model Drift Monitoring

Track model confidence over time:

```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    classification,
    AVG(confidence_score) as avg_confidence,
    STDDEV(confidence_score) as std_confidence
FROM model_metrics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour, classification;
```

**Warning Signs:**
- Decreasing average confidence
- Increasing standard deviation
- Shift in classification distribution

### Prometheus Metrics (Optional)

Start with monitoring profile:
```bash
docker-compose --profile monitoring up -d
```

Access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

---

## 🔄 Social Media Integration

### Supported Platforms

1. **Facebook**
   - Requires: Page Access Token
   - API: Graph API v18.0
   - Posts to page feed

2. **X (Twitter)**
   - Requires: API v2 credentials
   - OAuth 1.0a authentication
   - 280 character limit enforced

### Configuration

Add credentials to `.env`:

```bash
FACEBOOK_TOKEN=your_facebook_page_token
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
```

### Mock Mode (Testing)

If credentials are not provided, the system uses a mock poster:
- Simulates successful posts
- Logs to database without API calls
- Useful for development and testing

---

## 🛠️ Error Handling

### Error Response Format

```json
{
  "error": "error_type",
  "message": "Human-readable description",
  "request_id": "uuid",
  "timestamp": "2025-10-26T12:00:00"
}
```

### Common Errors

| Status Code | Error | Solution |
|-------------|-------|----------|
| 422 | Validation Error | Check request payload format |
| 500 | Internal Server Error | Check logs for details |
| 503 | Service Unhealthy | Database connection issue |

### Retry Strategy

- **Transient Errors:** Retry with exponential backoff
- **Validation Errors:** Do not retry, fix payload
- **Rate Limits:** Implement client-side rate limiting

---

## 📦 Deployment

### Production Checklist

- [ ] Change default passwords in `.env`
- [ ] Configure proper database backup
- [ ] Set up log aggregation
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring alerts
- [ ] Review and adjust thresholds
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Configure auto-scaling (if applicable)

### Docker Compose Profiles

```bash
# Minimal deployment (API + DB only)
docker-compose up -d

# With database UI
docker-compose --profile tools up -d

# With monitoring stack
docker-compose --profile monitoring up -d

# Full deployment
docker-compose --profile tools --profile monitoring up -d
```

### Scaling

Increase API workers:

```yaml
# docker-compose.yml
api:
  environment:
    WORKERS: 4  # Increase based on CPU cores
  deploy:
    replicas: 3  # Multiple containers
```

### Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| API | 1-2 cores | 2-4GB | 1GB |
| Database | 1 core | 1-2GB | 10GB+ |
| ML Models | - | 1-2GB | 2GB |

---

## 🔒 Security Considerations

1. **Input Validation**
   - All inputs validated with Pydantic
   - SQL injection protection via parameterized queries
   - XSS prevention through sanitization

2. **Authentication** (Recommended additions)
   - Add API key authentication
   - Implement rate limiting per user
   - Use JWT tokens for sessions

3. **Data Privacy**
   - PII detection before classification
   - Data retention policies
   - GDPR compliance considerations

4. **Network Security**
   - Run behind reverse proxy (nginx)
   - Enable HTTPS only
   - Restrict database access

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Port already in use
docker-compose down
lsof -i :8000
kill -9 <PID>

# 2. Database connection failed
docker-compose logs postgres
docker-compose restart postgres
```

### ML Model Loading Issues

```bash
# Clear model cache
docker-compose down
docker volume rm content_moderation_model_cache
docker-compose up -d

# Check available disk space
df -h
```

### Database Issues

```bash
# Connect to database
docker-compose exec postgres psql -U moderator -d content_moderation

# Check tables
\dt

# View recent content
SELECT * FROM content ORDER BY created_at DESC LIMIT 10;
```

---

## 📄 File Structure

```
content-moderation-system/
├── main.py                 # FastAPI application
├── ml_classifier.py        # ML classification service
├── social_media.py         # Social media integration
├── init.sql                # Database schema
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── test_moderation.py      # Automated test suite
├── README.md               # This file
└── docs/
    ├── API.md              # Detailed API docs
    ├── DEPLOYMENT.md       # Deployment guide
    └── ARCHITECTURE.md     # Technical architecture
```

---

## 📞 Support & Contributing

### Getting Help

- **Issues:** Open a GitHub issue
- **Discussions:** GitHub Discussions
- **Email:** support@yourcompany.com

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📜 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Hugging Face Transformers** - ML models
- **FastAPI** - Web framework
- **PostgreSQL** - Database
- **Docker** - Containerization

---

## 📊 Performance Benchmarks

| Metric | Value |
|--------|-------|
| Average Response Time | < 500ms |
| Throughput | 100+ req/sec |
| Model Inference | < 200ms |
| Database Query | < 50ms |
| 99th Percentile | < 1s |

---

**Built with ❤️ for safer online communities**