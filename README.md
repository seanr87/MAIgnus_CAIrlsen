# MAIgnus_CAIrlsen ♟️

An automated chess coaching bot that analyzes your Chess.com games and sends personalized feedback by email. Runs 4x daily with Task Scheduler.

---

## Features
- Automatically checks for new completed games on Chess.com
- Downloads PGNs and analyzes them using GPT
- Emails game reviews with personalized coaching tips
- Fully automated with logs and error handling

---

## How It Works
1. `game_checker.py`  
   ➡️ Downloads newly completed games from Chess.com  
2. `game_analyzer.py`  
   ➡️ Analyzes PGNs using GPT and generates feedback  
3. `email_sender.py`  
   ➡️ Emails the analysis report  
4. `maignus_bot.py`  
   ➡️ Automates the full workflow: Check → Analyze → Email → Log  
5. Task Scheduler  
   ➡️ Runs the bot 4 times per day

---
