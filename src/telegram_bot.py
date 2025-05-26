#!/usr/bin/env python3
"""
Telegram bot for triggering chess analysis reviews.
Uses python-telegram-bot v20+ with async handlers.
"""
import os
import json
import logging
import aiohttp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Telegram token from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

# API endpoints
API_BASE_URL = "https://maignus-cairlsen.onrender.com"
EVENTS_ENDPOINT = f"{API_BASE_URL}/events"
REVIEW_ENDPOINT = f"{API_BASE_URL}/run-review"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    welcome_message = """
🏆 Welcome to MAIgnus Chess Analysis Bot!

Use /review to trigger a performance analysis for recent chess events.

Commands:
• /start - Show this welcome message
• /review - Select an event for analysis
• /help - Show help information
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_message = """
🤖 MAIgnus Chess Analysis Bot Help

This bot helps you trigger performance reviews for your chess games.

**How to use:**
1. Type /review to see recent events
2. Click on an event button to start analysis
3. Wait for confirmation that the review is running

**Commands:**
• /start - Welcome message
• /review - Select event for analysis
• /help - This help message

**Note:** Analysis may take a few minutes to complete. The detailed report will be generated and saved.
    """
    await update.message.reply_text(help_message)

async def fetch_recent_events():
    """Fetch recent events from the API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVENTS_ENDPOINT) as response:
                if response.status == 200:
                    events = await response.json()
                    logger.info(f"Fetched {len(events)} events from API")
                    return events
                else:
                    logger.error(f"API returned status {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return None

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /review command - show recent events as buttons."""
    try:
        # Send "thinking" message
        thinking_message = await update.message.reply_text("🔍 Fetching recent events...")
        
        # Fetch events from API
        events = await fetch_recent_events()
        
        if not events:
            await thinking_message.edit_text(
                "❌ No recent events found or unable to connect to analysis service."
            )
            return
        
        if len(events) == 0:
            await thinking_message.edit_text(
                "📭 No recent chess events available for analysis."
            )
            return
        
        # Create inline keyboard with event buttons
        keyboard = []
        for event in events:
            event_name = event.get('event_name', 'Unknown Event')
            latest_date = event.get('latest_date', 'Unknown Date')
            
            # Truncate long event names for button display
            display_name = event_name[:40] + '...' if len(event_name) > 40 else event_name
            button_text = f"📅 {display_name} ({latest_date})"
            
            # Use full event name as callback data
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"review:{event_name}")])
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await thinking_message.edit_text(
            "🏆 Select an event to analyze:\n\n"
            "Click on an event below to start the performance review analysis.",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in review command: {e}")
        await update.message.reply_text(
            f"❌ Error loading events: {str(e)}"
        )

async def trigger_review_analysis(event_name: str):
    """Trigger the review analysis via API."""
    try:
        payload = {"event_name": event_name}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                REVIEW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    logger.info(f"Successfully triggered review for event: {event_name}")
                    return result
                else:
                    logger.error(f"API error {response.status}: {result}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error triggering review: {e}")
        return None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks from inline keyboard."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    try:
        callback_data = query.data
        
        if callback_data == "cancel":
            await query.edit_message_text("❌ Analysis cancelled.")
            return
        
        if callback_data.startswith("review:"):
            event_name = callback_data[7:]  # Remove "review:" prefix
            
            # Update message to show processing
            await query.edit_message_text(
                f"⚙️ Starting analysis for event: {event_name}\n\nThis may take a few minutes. Please wait..."
            )

            
            # Trigger the review
            result = await trigger_review_analysis(event_name)
            
            if result and result.get('status') == 'success':
                games_count = result.get('games_analyzed', 'unknown')
                report_file = result.get('report_filename', 'performance_review.txt')
                
                success_message = f"""
✅ **Analysis Started Successfully!**

📊 Event: {event_name}
🎯 Games Analyzed: {games_count}
📝 Report File: {report_file}

The detailed performance review is being generated. The report will be saved and may trigger additional notifications when complete.
                """
                
                await query.edit_message_text(success_message)

                
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'Failed to connect to analysis service'
                
                await query.edit_message_text(
                    f"❌ Analysis Failed\n\n"
                    f"Event: {event_name}\n"
                    f"Error: {error_msg}\n\n"
                    "Please try again later or check if the event has available games."
                )

        else:
            await query.edit_message_text("❓ Unknown action. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.edit_message_text(
            f"❌ Error processing request\n\n"
            f"Details: {str(e)}\n\n"
            "Please try again later."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors that occur during bot operation."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    # Try to notify the user if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )
        except Exception:
            pass  # Ignore if we can't send the error message

def main():
    """Start the Telegram bot."""
    logger.info("Starting MAIgnus Chess Analysis Telegram Bot...")
    
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("review", review_command))
        
        # Add callback handler for button clicks
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("Bot handlers registered successfully")
        logger.info("Starting polling...")
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()