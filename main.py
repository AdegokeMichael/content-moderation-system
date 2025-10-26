"""
Content Moderation API Service
Main application entry point with webhook endpoints and business logic
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import json
import uuid
import asyncpg
import os
from contextlib import asynccontextmanager

# ML Model Service
from ml_classifier import ContentClassifier

# Social Media Integration
from social_media import SocialMediaPoster

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic Models
class ContentSubmission(BaseModel):
    """Schema for incoming content submissions"""
    content: str = Field(..., min_length=1, max_length=5000)
    author_id: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(default="web", max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('content')
    def sanitize_content(cls, v):
        """Basic sanitization"""
        return v.strip()
    
    @validator('author_id')
    def validate_author(cls, v):
        """Validate author ID format"""
        if not v or v.isspace():
            raise ValueError("Author ID cannot be empty")
        return v.strip()


class ClassificationResult(BaseModel):
    """Classification output schema"""
    content_id: str
    classification: str
    confidence: float
    toxicity_score: float
    spam_score: float
    sentiment: str
    action_taken: str
    timestamp: datetime
    details: Dict[str, Any]


# Database connection pool
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db_pool
    
    # Startup: Initialize database pool
    logger.info("Initializing database connection pool...")
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "moderator"),
        password=os.getenv("DB_PASSWORD", "secure_password"),
        database=os.getenv("DB_NAME", "content_moderation"),
        min_size=5,
        max_size=20
    )
    logger.info("Database pool initialized")
    
    # Initialize ML classifier
    app.state.classifier = ContentClassifier()
    logger.info("ML classifier initialized")
    
    # Initialize social media poster
    app.state.social_poster = SocialMediaPoster(
        facebook_token=os.getenv("FACEBOOK_TOKEN"),
        twitter_api_key=os.getenv("TWITTER_API_KEY"),
        twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
        twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        twitter_access_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )
    logger.info("Social media integrations initialized")
    
    yield
    
    # Shutdown: Close database pool
    logger.info("Closing database connection pool...")
    await db_pool.close()
    logger.info("Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="AI Content Moderation System",
    description="Automated content analysis, classification, and moderation",
    version="1.0.0",
    lifespan=lifespan
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with logging"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": str(uuid.uuid4())
        }
    )


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "operational",
        "service": "content-moderation-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.post("/api/v1/content/submit", response_model=ClassificationResult)
async def submit_content(
    submission: ContentSubmission,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Main webhook endpoint for content submission
    
    Flow:
    1. Validate input
    2. Generate unique content ID
    3. Classify content using ML model
    4. Apply business logic based on classification
    5. Store in database
    6. Log audit trail
    7. Return classification result
    """
    content_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    logger.info(f"Processing content submission: {content_id}")
    
    try:
        # Step 1: ML Classification
        classifier = request.app.state.classifier
        classification_result = await classifier.classify(submission.content)
        
        logger.info(f"Content {content_id} classified as: {classification_result['classification']}")
        
        # Step 2: Determine action based on classification
        action_result = await apply_business_logic(
            content_id=content_id,
            submission=submission,
            classification=classification_result
        )
        
        # Step 3: Store content and audit log
        await store_content(
            content_id=content_id,
            submission=submission,
            classification=classification_result,
            action=action_result
        )
        
        # Step 4: If acceptable, post to social media (background task)
        if classification_result['classification'] == 'acceptable':
            background_tasks.add_task(
                post_to_social_media,
                content_id=content_id,
                content=submission.content,
                social_poster=request.app.state.social_poster
            )
        
        # Step 5: Log metrics for model drift monitoring
        await log_classification_metrics(
            content_id=content_id,
            confidence=classification_result['confidence'],
            classification=classification_result['classification']
        )
        
        # Prepare response
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        response = ClassificationResult(
            content_id=content_id,
            classification=classification_result['classification'],
            confidence=classification_result['confidence'],
            toxicity_score=classification_result['toxicity_score'],
            spam_score=classification_result['spam_score'],
            sentiment=classification_result['sentiment'],
            action_taken=action_result['action'],
            timestamp=start_time,
            details={
                "processing_time_seconds": processing_time,
                "model_version": classifier.model_version,
                "threshold_used": classification_result.get('threshold'),
                "notification_sent": action_result.get('notification_sent', False)
            }
        )
        
        logger.info(f"Content {content_id} processed successfully in {processing_time:.3f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing content {content_id}: {e}", exc_info=True)
        
        # Store error in audit log
        await log_error(content_id, str(e), submission.dict())
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process content: {str(e)}"
        )


async def apply_business_logic(
    content_id: str,
    submission: ContentSubmission,
    classification: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply business logic based on classification
    
    Rules:
    - acceptable: Store in approved_content table
    - needs_review: Add to moderation_queue
    - toxic: Flag and notify user
    - spam: Increment spam counter, flag
    """
    category = classification['classification']
    result = {"action": category}
    
    if category == "acceptable":
        logger.info(f"Content {content_id}: Approved for publication")
        result["action"] = "approved_and_stored"
        result["notification_sent"] = False
        
    elif category == "needs_review":
        logger.info(f"Content {content_id}: Queued for human review")
        result["action"] = "queued_for_review"
        result["notification_sent"] = False
        # Add to moderation queue
        await add_to_moderation_queue(content_id, submission, classification)
        
    elif category == "toxic":
        logger.warning(f"Content {content_id}: Flagged as toxic")
        result["action"] = "rejected_toxic"
        result["notification_sent"] = True
        # Notify user
        await notify_user(
            submission.author_id,
            "toxic",
            f"Your content was flagged as toxic and has been rejected."
        )
        # Increment user violation counter
        await increment_violation_counter(submission.author_id, "toxic")
        
    elif category == "spam":
        logger.warning(f"Content {content_id}: Flagged as spam")
        result["action"] = "rejected_spam"
        result["notification_sent"] = True
        await notify_user(
            submission.author_id,
            "spam",
            f"Your content was identified as spam and has been rejected."
        )
        await increment_violation_counter(submission.author_id, "spam")
    
    return result


async def store_content(
    content_id: str,
    submission: ContentSubmission,
    classification: Dict[str, Any],
    action: Dict[str, Any]
):
    """Store content and create audit log entry"""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Insert into content table
            await conn.execute("""
                INSERT INTO content (
                    content_id, author_id, content_text, platform,
                    classification, confidence, toxicity_score,
                    spam_score, sentiment, action_taken,
                    metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                content_id, submission.author_id, submission.content,
                submission.platform, classification['classification'],
                classification['confidence'], classification['toxicity_score'],
                classification['spam_score'], classification['sentiment'],
                action['action'], json.dumps(submission.metadata),
                datetime.utcnow()
            )
            
            # Insert audit log
            await conn.execute("""
                INSERT INTO audit_log (
                    log_id, content_id, event_type, event_data, timestamp
                ) VALUES ($1, $2, $3, $4, $5)
            """,
                str(uuid.uuid4()), content_id, "content_classified",
                json.dumps({
                    "classification": classification,
                    "action": action
                }),
                datetime.utcnow()
            )


async def add_to_moderation_queue(
    content_id: str,
    submission: ContentSubmission,
    classification: Dict[str, Any]
):
    """Add content to moderation queue for human review"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO moderation_queue (
                queue_id, content_id, author_id, content_text,
                reason, priority, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            str(uuid.uuid4()), content_id, submission.author_id,
            submission.content, "needs_human_review",
            calculate_priority(classification), "pending",
            datetime.utcnow()
        )


def calculate_priority(classification: Dict[str, Any]) -> int:
    """Calculate priority for moderation queue (1-5, 5 being highest)"""
    toxicity = classification['toxicity_score']
    confidence = classification['confidence']
    
    if toxicity > 0.7 or confidence < 0.6:
        return 5
    elif toxicity > 0.5 or confidence < 0.7:
        return 4
    elif toxicity > 0.3:
        return 3
    else:
        return 2


async def notify_user(author_id: str, reason: str, message: str):
    """Send notification to user (simulated)"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_notifications (
                notification_id, author_id, notification_type,
                message, sent_at, status
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
            str(uuid.uuid4()), author_id, reason, message,
            datetime.utcnow(), "sent"
        )
    
    logger.info(f"Notification sent to user {author_id}: {reason}")


async def increment_violation_counter(author_id: str, violation_type: str):
    """Increment user's violation counter"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_violations (author_id, violation_type, count, last_violation)
            VALUES ($1, $2, 1, $3)
            ON CONFLICT (author_id, violation_type)
            DO UPDATE SET
                count = user_violations.count + 1,
                last_violation = $3
        """,
            author_id, violation_type, datetime.utcnow()
        )


async def log_classification_metrics(
    content_id: str,
    confidence: float,
    classification: str
):
    """Log classification metrics for model drift monitoring"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO model_metrics (
                metric_id, content_id, confidence_score,
                classification, timestamp
            ) VALUES ($1, $2, $3, $4, $5)
        """,
            str(uuid.uuid4()), content_id, confidence,
            classification, datetime.utcnow()
        )


async def log_error(content_id: str, error: str, submission_data: Dict[str, Any]):
    """Log errors to audit trail"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_log (
                    log_id, content_id, event_type, event_data, timestamp
                ) VALUES ($1, $2, $3, $4, $5)
            """,
                str(uuid.uuid4()), content_id, "processing_error",
                json.dumps({
                    "error": error,
                    "submission": submission_data
                }),
                datetime.utcnow()
            )
    except Exception as e:
        logger.error(f"Failed to log error: {e}")


async def post_to_social_media(
    content_id: str,
    content: str,
    social_poster: SocialMediaPoster
):
    """Post acceptable content to social media platforms"""
    try:
        results = await social_poster.post_content(content)
        
        # Log social media posting results
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO social_media_posts (
                    post_id, content_id, platforms, results, posted_at
                ) VALUES ($1, $2, $3, $4, $5)
            """,
                str(uuid.uuid4()), content_id,
                json.dumps(list(results.keys())),
                json.dumps(results), datetime.utcnow()
            )
        
        logger.info(f"Content {content_id} posted to social media: {results}")
        
    except Exception as e:
        logger.error(f"Failed to post content {content_id} to social media: {e}")


# Analytics endpoints
@app.get("/api/v1/stats/overview")
async def get_statistics():
    """Get overall moderation statistics"""
    async with db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_content,
                SUM(CASE WHEN classification = 'acceptable' THEN 1 ELSE 0 END) as acceptable,
                SUM(CASE WHEN classification = 'needs_review' THEN 1 ELSE 0 END) as needs_review,
                SUM(CASE WHEN classification = 'toxic' THEN 1 ELSE 0 END) as toxic,
                SUM(CASE WHEN classification = 'spam' THEN 1 ELSE 0 END) as spam,
                AVG(confidence) as avg_confidence
            FROM content
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        
        return dict(stats)


@app.get("/api/v1/stats/model-drift")
async def get_model_drift_metrics():
    """Get model drift metrics based on confidence scores over time"""
    async with db_pool.acquire() as conn:
        metrics = await conn.fetch("""
            SELECT
                DATE_TRUNC('hour', timestamp) as hour,
                classification,
                AVG(confidence_score) as avg_confidence,
                STDDEV(confidence_score) as std_confidence,
                COUNT(*) as count
            FROM model_metrics
            WHERE timestamp > NOW() - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('hour', timestamp), classification
            ORDER BY hour DESC
        """)
        
        return [dict(m) for m in metrics]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )