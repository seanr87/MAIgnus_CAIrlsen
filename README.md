# MAIgnus CAIrlsen Chess Analysis Bot

MAIgnus CAIrlsen is an automated chess analysis system that combines Stockfish engine evaluation with GPT-generated analysis to provide insightful, coach-like feedback on your chess games.

## Features

- **Game Fetching**: Automatically retrieves your latest games from Chess.com
- **Stockfish Analysis**: Evaluates positions and identifies critical moments using Stockfish
- **Modular GPT Analysis**: Creates targeted analysis for different aspects of your game
- **Critical Moment Visualization**: Captures and analyzes key turning points with board positions
- **Beautiful Email Reports**: Sends polished HTML email reports with visualizations

## Architecture

The system is composed of the following modules:

- `maignus_bot.py` - Main execution script that orchestrates the workflow
- `chess_api.py` - Fetches games from Chess.com
- `modular_analyzer.py` - Performs analysis with modular GPT calls
- `board_visualizer.py` - Generates chess board visualizations from FEN strings
- `email_sender.py` - Formats and sends analysis emails
- `utils.py` - Utility functions used across modules
- `config.py` - Centralized configuration

## Getting Started

### Prerequisites

- Python 3.8+
- Stockfish chess engine installed
- OpenAI API key
- Chess.com account

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/seanr87/MAIgnus_CAIrlsen.git
   cd MAIgnus_CAIrlsen
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   EMAIL_APP_PASSWORD=your_email_app_password
   SENDER_EMAIL=your_email@gmail.com
   RECEIVER_EMAIL=your_email@gmail.com
   CHESS_USERNAME=your_chess_username
   STOCKFISH_PATH=/path/to/stockfish
   ```

### Usage

Run the analysis script to process your latest game:

```
python maignus_bot.py
```

To force analysis on the latest game even if it's not new:

```
python maignus_bot.py --force
```

Alternatively, you can use the provided batch file:

```
run_maignus.bat
```

## How It Works

1. The system fetches your latest games from Chess.com
2. For the newest game, it runs Stockfish analysis to:
   - Calculate centipawn loss, blunders, mistakes, and inaccuracies
   - Identify the top 3 critical moments (largest centipawn losses)
   - Capture the FEN position before each critical moment

3. It then makes modular GPT calls to generate:
   - A narrative game summary
   - Analysis of each critical moment with the FEN position
   - Highlights and lowlights for both players
   - A focused coaching point

4. The analysis is compiled into a clean report
5. Board visualizations are generated for the critical moments
6. A formatted HTML email with all analysis is sent to your inbox

## Directory Structure

```
MAIgnus_CAIrlsen/
├── .env                  # Environment variables (private)
├── config.py             # Configuration settings
├── maignus_bot.py        # Main execution script
├── modular_analyzer.py   # Modular GPT analysis engine
├── chess_api.py          # Chess.com API interaction
├── board_visualizer.py   # Board visualization from FEN
├── email_sender.py       # Email generation and sending
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── run_maignus.bat       # Windows batch execution file
├── data/                 # PGN game files
├── reports/              # Generated analysis reports
│   └── boards/           # Board visualizations
└── logs/                 # Application logs
```

## Customization

- Edit `config.py` to change general settings
- Modify prompts in `modular_analyzer.py` to adjust analysis style
- Customize email template in `email_sender.py`

## Scheduling

For automatic game analysis, set up a scheduled task to run `run_maignus.bat` at your preferred frequency.

### Windows:
Use Task Scheduler to run the batch file periodically.

### Linux/Mac:
Use cron to schedule the script:
```
0 * * * * cd /path/to/MAIgnus_CAIrlsen && python maignus_bot.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [python-chess](https://python-chess.readthedocs.io/) for chess parsing and analysis
- [OpenAI](https://openai.com/) for GPT-powered analysis
- [Chess.com](https://www.chess.com/) for the game data API