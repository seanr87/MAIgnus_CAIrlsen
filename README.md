# MAIgnus_CAIrlsen Chess Analysis Bot

An automated chess analysis tool that fetches your games from Chess.com, analyzes them with Stockfish and GPT, and emails you personalized analysis reports.

## Ultimate Vision

[Chess.com API] → [Game Fetcher] → [Database] ← [Game Analyzer] → [Pattern Recognizer] → [Dashboard/Report Generator]

## Overview

MAIgnus_CAIrlsen is a modular chess analysis pipeline that:

1. Fetches your latest games from Chess.com using their API
2. Analyzes games using the Stockfish engine for objective evaluation
3. Generates human-friendly analysis using GPT-4
4. Composes and sends a styled email report with your game analysis

## File Structure

- `config.py` - Centralized configuration settings and environment variables
- `utils.py` - Common utility functions used across modules
- `chess_api.py` - Functions for interacting with the Chess.com API
- `analyzer.py` - Combined game analysis using Stockfish and GPT
- `email_sender.py` - Email composition and delivery module
- `maignus_bot.py` - Main execution script that orchestrates the workflow

## Setup

### Prerequisites

- Python 3.8+
- Stockfish chess engine installed
- Chess.com account
- OpenAI API key (for GPT-4 access)
- Email account with app password for sending emails

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
CHESS_USERNAME=your_username
OPENAI_API_KEY=your_openai_key
STOCKFISH_PATH=/path/to/stockfish
SENDER_EMAIL=your_email@example.com
EMAIL_APP_PASSWORD=your_app_password
RECEIVER_EMAIL=destination@example.com
```

### Installation

1. Clone the repository
2. Create required directories:
   ```
   mkdir -p data reports logs
   ```
3. Install dependencies:
   ```
   pip install python-chess requests openai yagmail markdown python-dotenv
   ```

## Usage

Run the main bot script to execute the full workflow:

```bash
python maignus_bot.py
```

This will:
1. Check for any new games on Chess.com
2. Generate analysis for the latest game
3. Send an email with the analysis

### Scheduling

For automated analysis, set up a cron job or scheduled task to run the script regularly:

```
# Run daily at 8 AM
0 8 * * * cd /path/to/project && python maignus_bot.py
```

## Customization

- Modify the email template in `email_sender.py` to change the appearance of reports
- Adjust Stockfish analysis parameters in `analyzer.py` for different depth levels
- Customize GPT prompts in `analyzer.py` to change the style of analysis

## Logs

Logs are stored in the `logs` directory:
- `maignus_bot.log` - Main workflow logs
- `analyzer.log` - Game analysis logs
- `email_sender.log` - Email delivery logs
- `send_failures.log` - Records of failed email attempts