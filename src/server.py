#!/usr/bin/env python3
"""
FastAPI server for chess analysis periodic reviews.
"""
import os
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chess Analysis API", version="1.0.0")

# Database connection string from environment
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise ValueError("DB_URL environment variable is required")

logger.info(f"Database URL loaded: {DB_URL[:20]}..." if len(DB_URL) > 20 else "Database URL loaded")

class EventRequest(BaseModel):
    event_name: str

class EventResponse(BaseModel):
    event_name: str
    latest_date: str

async def get_db_connection():
    """Get PostgreSQL database connection using asyncpg."""
    try:
        return await asyncpg.connect(os.getenv("DB_URL"))
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def run_periodic_review(event_name: str) -> Dict[str, str]:
    """
    Run periodic review analysis for the given event using the PeriodicReviewer.
    """
    try:
        # Import modules (may not be available in all environments)
        try:
            from periodic_reviewer import PeriodicReviewer
            from analysis import ChessAnalyzer
        except ImportError as e:
            logger.error(f"Required modules not available: {e}")
            return {
                "status": "error",
                "message": f"Analysis modules not available: {str(e)}",
                "event_name": event_name
            }
        
        logger.info(f"Running periodic review for event: {event_name}")
        
        # Use PostgreSQL connection URL directly for ChessAnalyzer
        db_path = os.getenv("DB_URL")
        if not db_path:
            return {
                "status": "error",
                "message": "Database connection URL not configured",
                "event_name": event_name
            }
        
        # Initialize analyzer and load data for the specific event
        analyzer = ChessAnalyzer(db_path)
        analyzer.load_data(event_name=event_name)
        
        if analyzer.games_df.empty:
            return {
                "status": "error",
                "message": f"No games found for event: {event_name}",
                "event_name": event_name
            }
        
        # Generate the review
        reviewer = PeriodicReviewer(analyzer.games_df)
        
        # Save report with event-specific filename
        safe_event_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in event_name)
        filename = f"performance_review_{safe_event_name.replace(' ', '_')}.txt"
        success = reviewer.save_report(filename)
        
        if success:
            return {
                "status": "success",
                "message": f"Performance review generated for {len(analyzer.games_df)} games",
                "event_name": event_name,
                "games_analyzed": len(analyzer.games_df),
                "report_filename": filename
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save performance review report",
                "event_name": event_name
            }
            
    except Exception as e:
        logger.error(f"Error running periodic review: {e}")
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)}",
            "event_name": event_name
        }

@app.get("/events", response_model=List[EventResponse])
async def get_recent_events():
    """Get the 5 most recent event names and dates."""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = """
            SELECT DISTINCT event_name, MAX(date) as latest_date
            FROM game_analysis 
            WHERE event_name IS NOT NULL 
            GROUP BY event_name 
            ORDER BY latest_date DESC 
            LIMIT 5
        """
        
        rows = await conn.fetch(query)
        
        events = [
            EventResponse(
                event_name=row['event_name'],
                latest_date=row['latest_date'].isoformat() if row['latest_date'] else ""
            )
            for row in rows
        ]
        
        logger.info(f"Retrieved {len(events)} recent events")
        return events
        
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")
    finally:
        if conn:
            await conn.close()

@app.post("/run-review")
async def run_review(request: EventRequest):
    """Run periodic review for the specified event."""
    try:
        if not request.event_name.strip():
            raise HTTPException(status_code=400, detail="Event name cannot be empty")
        
        # Verify event exists in database
        conn = None
        try:
            conn = await get_db_connection()
            
            exists_query = """
                SELECT COUNT(*) FROM game_analysis 
                WHERE event_name = $1
            """
            
            count = await conn.fetchval(exists_query, request.event_name)
            
            if count == 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Event '{request.event_name}' not found in database"
                )
                
        finally:
            if conn:
                await conn.close()
        
        # Run the periodic review
        result = run_periodic_review(request.event_name)
        
        logger.info(f"Periodic review completed for event: {request.event_name}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running review: {e}")
        raise HTTPException(status_code=500, detail="Failed to run periodic review")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chess-analysis-api"}

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )