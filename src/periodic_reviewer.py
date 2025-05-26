#!/usr/bin/env python3
"""
Periodic Performance Review Generator for MAIgnus Chess Coaching System
======================================================================

This script analyzes chess games over a selected period and generates
comprehensive performance reviews using GPT-4.

Author: MAIgnus_CAIrlsen
Created: 2025-05-25
"""

import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from openai import OpenAI

from src.config import OPENAI_API_KEY, GPT_MODEL, REPORTS_DIR, CHESS_USERNAME
from utils import log

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

class PeriodicReviewer:
    """
    Generates comprehensive periodic performance reviews using GPT-4 analysis.
    """
    
    def __init__(self, games_df: pd.DataFrame, username: str = CHESS_USERNAME):
        """
        Initialize the periodic reviewer.
        
        Args:
            games_df (pd.DataFrame): DataFrame containing chess games
            username (str): Player's username
        """
        self.games_df = games_df.copy() if not games_df.empty else pd.DataFrame()
        self.username = username
        self.stats = {}
        
        if not self.games_df.empty:
            # Ensure date column is datetime
            if 'date' in self.games_df.columns:
                self.games_df['date'] = pd.to_datetime(self.games_df['date'])
            
            # Generate basic statistics
            self._calculate_basic_stats()
        
        logger.info(f"PeriodicReviewer initialized with {len(self.games_df)} games")
    
    def _calculate_basic_stats(self) -> None:
        """Calculate basic statistics from the games DataFrame."""
        if self.games_df.empty:
            self.stats = {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'win_rate': 0.0,
                'avg_rating': 0,
                'rating_change': 0
            }
            return
        
        # Basic performance stats
        result_counts = self.games_df['result'].value_counts()
        total_games = len(self.games_df)
        
        self.stats = {
            'total_games': total_games,
            'wins': result_counts.get('win', 0),
            'losses': result_counts.get('loss', 0),
            'draws': result_counts.get('draw', 0),
            'win_rate': (result_counts.get('win', 0) / total_games * 100) if total_games > 0 else 0,
            'avg_rating': self.games_df['player_rating'].mean() if 'player_rating' in self.games_df.columns else 0,
            'rating_change': self._calculate_rating_change()
        }
    
    def _calculate_rating_change(self) -> int:
        """Calculate rating change from first to last game."""
        if len(self.games_df) < 2 or 'player_rating' not in self.games_df.columns:
            return 0
        
        # Sort by date to get chronological order
        sorted_games = self.games_df.sort_values('date')
        first_rating = sorted_games.iloc[0]['player_rating']
        last_rating = sorted_games.iloc[-1]['player_rating']
        
        return int(last_rating - first_rating)
    
    def _categorize_time_control(self, time_control: str) -> str:
        """Categorize time control into standard chess categories."""
        if not time_control or time_control == 'Unknown':
            return 'Unknown'
        
        try:
            if '+' in time_control:
                base_time = int(time_control.split('+')[0])
            else:
                base_time = int(time_control)
            
            if base_time < 3:
                return 'Bullet'
            elif base_time < 10:
                return 'Blitz'
            elif base_time < 30:
                return 'Rapid'
            else:
                return 'Classical'
        except (ValueError, TypeError):
            return 'Unknown'
    
    def _format_stats_for_gpt(self) -> str:
        """Format statistics in a clean way for GPT consumption."""
        if self.games_df.empty:
            return "No games available for analysis."
        
        # Time control analysis
        time_controls = {}
        if 'time_control' in self.games_df.columns:
            self.games_df['time_category'] = self.games_df['time_control'].apply(self._categorize_time_control)
            time_controls = self.games_df.groupby('time_category')['result'].agg(['count', lambda x: (x == 'win').sum() / len(x) * 100]).round(1)
            time_controls.columns = ['games', 'win_rate']
        
        # Opening analysis
        opening_stats = ""
        if 'opening_name' in self.games_df.columns:
            top_openings = self.games_df.groupby('opening_name').agg({
                'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100 if len(x) > 0 else 0]
            }).round(1)
            top_openings.columns = ['games', 'win_rate']
            top_openings = top_openings.sort_values('games', ascending=False).head(5)
            
            opening_stats = "\nTop 5 openings:\n"
            for opening, stats in top_openings.iterrows():
                opening_stats += f"- {opening}: {int(stats['games'])} games, {stats['win_rate']:.1f}% win rate\n"
        
        # Stockfish stats (if available)
        stockfish_stats = ""
        stockfish_cols = ['player_avg_cpl', 'player_blunders', 'player_mistakes', 'player_inaccuracies']
        if any(col in self.games_df.columns for col in stockfish_cols):
            stockfish_stats = "\nStockfish Analysis Summary:\n"
            for col in stockfish_cols:
                if col in self.games_df.columns:
                    avg_val = self.games_df[col].mean()
                    if pd.notna(avg_val):
                        clean_name = col.replace('player_', '').replace('_', ' ').title()
                        stockfish_stats += f"- Average {clean_name}: {avg_val:.1f}\n"
        
        # Format time control stats
        time_control_stats = ""
        if not time_controls.empty:
            time_control_stats = "\nTime Control Performance:\n"
            for category, stats in time_controls.iterrows():
                if stats['games'] > 0:
                    time_control_stats += f"- {category}: {int(stats['games'])} games, {stats['win_rate']:.1f}% win rate\n"
        
        return f"""
Period Analysis Summary:
- Total Games: {self.stats['total_games']}
- Win Rate: {self.stats['win_rate']:.1f}% ({self.stats['wins']}W-{self.stats['losses']}L-{self.stats['draws']}D)
- Average Rating: {self.stats['avg_rating']:.0f}
- Rating Change: {self.stats['rating_change']:+d}
{opening_stats}
{time_control_stats}
{stockfish_stats}
""".strip()
    
    def generate_overall_trends(self) -> str:
        """Generate overall performance trends section using GPT."""
        logger.info("Generating overall trends analysis...")
        
        stats_summary = self._format_stats_for_gpt()
        
        prompt = f"""
You are a tournament-level chess coach reviewing a player's recent games.
Your job is to assess how they play — not just the results.

Player: {self.username}
Games: {len(self.games_df)}

{stats_summary}

Write 1-2 **insightful, blunt paragraphs** describing the player's strengths, weaknesses, and tendencies.
Do NOT repeat stats. Focus on:
- How the player wins (attacks, endgames, traps?)
- Strategic tendencies (open positions? risky play?)
- Decision quality (blunders in good positions? tempo loss?)
- What worked, and what might stop working against stronger players

Be specific. Pretend you're preparing this player for a serious online tournament.
"""
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional chess coach providing performance analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating overall trends: {e}")
            return f"Error generating analysis: {str(e)}"
    
    def generate_opening_review(self) -> str:
        """Generate opening repertoire review using GPT."""
        logger.info("Generating opening repertoire review...")

        if self.games_df.empty or 'opening_name' not in self.games_df.columns:
            return "No opening data available."

        openings_used = self.games_df['opening_name'].value_counts()
        single_opening = len(openings_used) == 1
        top_opening = openings_used.idxmax()

        if single_opening:
            # Break down by variation
            if 'pgn_text' not in self.games_df.columns:
                return "PGN data required for opening variation analysis."

            from query_names import parse_pgn_details
            self.games_df['variation'] = self.games_df['pgn_text'].apply(lambda pgn: parse_pgn_details(pgn).get('opening_name', 'Unknown'))

            variation_stats = self.games_df.groupby('variation').agg({
                'result': ['count', lambda x: (x == 'win').sum(), lambda x: (x == 'loss').sum(), lambda x: (x == 'draw').sum()]
            })
            variation_stats.columns = ['games', 'wins', 'losses', 'draws']
            variation_stats['win_rate'] = (variation_stats['wins'] / variation_stats['games'] * 100).round(1)
            variation_summary = "\n".join([
                f"- {variation}: {row['games']} games, {row['win_rate']:.1f}% win rate ({row['wins']}W-{row['losses']}L-{row['draws']}D)"
                for variation, row in variation_stats.iterrows()
            ])

            prompt = f"""
You are a chess coach preparing a player for tournament competition. Your task is to assess how well the player uses openings — not just the results.

Player: {self.username}

{opening_summary}

Analyze the player's use of these openings. For each of the most played:
- Are they using it correctly? Or making basic structural or tempo mistakes?
- Do their win rates reflect understanding or poor opposition?
- Are they entering risky, sharp lines or playing conservatively?

If the player relies heavily on a single opening or variation, assess whether their depth in it is sufficient and suggest how they could be punished by a stronger player. Recommend what to keep, refine, or replace. Avoid generic tips.
"""
        else:
            # Multi-opening mode
            opening_stats = self.games_df.groupby('opening_name').agg({
                'result': ['count', lambda x: (x == 'win').sum(), lambda x: (x == 'loss').sum(), lambda x: (x == 'draw').sum()]
            })
            opening_stats.columns = ['games', 'wins', 'losses', 'draws']
            opening_stats['win_rate'] = (opening_stats['wins'] / opening_stats['games'] * 100).round(1)
            opening_summary = "\n".join([
                f"- {opening}: {row['games']} games, {row['win_rate']:.1f}% win rate ({row['wins']}W-{row['losses']}L-{row['draws']}D)"
                for opening, row in opening_stats.sort_values('games', ascending=False).iterrows()
            ])

            prompt = f"""
You are a chess coach preparing a player for tournament competition. Your task is to assess how well the player uses openings — not just the results.

Player: {self.username}

{opening_summary}

Analyze the player's use of these openings. For each of the most played:
- Are they using it correctly? Or making basic structural or tempo mistakes?
- Do their win rates reflect understanding or poor opposition?
- Are they entering risky, sharp lines or playing conservatively?

If the player relies heavily on a single opening or variation, assess whether their depth in it is sufficient and suggest how they could be punished by a stronger player. Recommend what to keep, refine, or replace. Avoid generic tips.
"""


        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach who specializes in opening preparation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating opening review: {e}")
            return f"Error generating opening analysis: {str(e)}"

    
    def generate_time_control_breakdown(self) -> str:
        """Generate time control performance breakdown using GPT."""
        logger.info("Generating time control breakdown...")

        if self.games_df.empty or 'time_control' not in self.games_df.columns:
            return "No time control data available for analysis."

        # Categorize and count
        self.games_df['time_category'] = self.games_df['time_control'].apply(self._categorize_time_control)
        categories = self.games_df['time_category'].unique()
        single_category = len(categories) == 1

        # Summary
        time_stats = self.games_df.groupby('time_category').agg({
            'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100]
        }).round(1)
        time_stats.columns = ['games', 'win_rate']

        time_summary = ""
        for category, stats in time_stats.iterrows():
            time_summary += f"- {category}: {int(stats['games'])} games, {stats['win_rate']:.1f}% win rate\n"

        focus = ""
        if single_category:
            focus = f"\nAll games were played as **{categories[0]}**. Please tailor your coaching advice specifically to that format."

        prompt = f"""
You are a chess coach preparing a player for rated online tournament play. Your task is to assess how well they perform under different time controls.

Player: {self.username}

{time_summary}
{focus}

Don't restate stats. Instead:
- Evaluate if the player struggles under time pressure (e.g. Blitz) or thrives with time to think (e.g. Rapid)
- Are they fast and sloppy? Or slow and accurate?
- Do their openings help save time or cause time trouble?
- What time controls fit their style? Which need training?

Offer 1 paragraph of concrete, blunt advice. Prioritize how they can train to compete better in faster or slower formats.
"""


        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach specializing in time control formats."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating time control breakdown: {e}")
            return f"Error generating time control analysis: {str(e)}"

    
    def generate_strengths_weaknesses(self) -> str:
        """Generate strengths and weaknesses analysis using GPT."""
        logger.info("Generating strengths and weaknesses analysis...")
        
        stats_summary = self._format_stats_for_gpt()
        
        # Additional analysis for patterns
        pattern_analysis = ""
        if not self.games_df.empty:
            # Color preference
            if 'player_color' in self.games_df.columns:
                color_stats = self.games_df.groupby('player_color')['result'].agg(['count', lambda x: (x == 'win').sum() / len(x) * 100]).round(1)
                color_stats.columns = ['games', 'win_rate']
                pattern_analysis += "\nColor Performance:\n"
                for color, stats in color_stats.iterrows():
                    pattern_analysis += f"- As {color}: {int(stats['games'])} games, {stats['win_rate']:.1f}% win rate\n"
        
        prompt = f"""
You are a chess coach evaluating a player's tendencies across all games.

Player: {self.username}

{stats_summary}
{pattern_analysis}

Avoid repeating statistics. Instead, analyze:
- Strategic identity (attacker? defender? tactical opportunist?)
- Patterns in their wins and losses
- Do they overextend? Blunder in won positions? Survive bad positions?
- Are they stronger as White or Black — and why?

Summarize strengths, flaws, and trends that would show up to any serious coach or opponent scouting this player. Write 2–3 direct paragraphs with no fluff.
"""


        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are an experienced chess coach skilled at identifying player strengths and weaknesses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating strengths and weaknesses: {e}")
            return f"Error generating strengths/weaknesses analysis: {str(e)}"
    
    def generate_coaching_recommendations(self) -> str:
        """Generate coaching recommendations using GPT."""
        logger.info("Generating coaching recommendations...")
        
        stats_summary = self._format_stats_for_gpt()
        
        prompt = f"""
You are a tournament chess coach. Based on this player's trends, provide 1–2 direct training recommendations.

Player: {self.username}

{stats_summary}

Don't repeat results. Tell them what to work on this month:
- A weakness they can directly fix (e.g. time pressure blunders, poor endgame conversion, overuse of one opening)
- A study method to address it (e.g. puzzle drills, annotated game review, opening prep via database)

Be concrete, not generic. Prioritize changes that will actually help the player improve their results.
"""

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach providing specific, actionable training recommendations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating coaching recommendations: {e}")
            return f"Error generating coaching recommendations: {str(e)}"
    
    def generate_stats_summary(self) -> str:
        """Generate a formatted statistics summary table."""
        logger.info("Generating statistics summary...")
        
        if self.games_df.empty:
            return "No games available for statistics summary."
        
        # Basic stats
        summary = f"""
**Performance Overview:**
- Total Games: {self.stats['total_games']}
- Wins: {self.stats['wins']} ({self.stats['win_rate']:.1f}%)
- Losses: {self.stats['losses']} ({(self.stats['losses']/self.stats['total_games']*100):.1f}%)
- Draws: {self.stats['draws']} ({(self.stats['draws']/self.stats['total_games']*100):.1f}%)
- Average Rating: {self.stats['avg_rating']:.0f}
- Rating Change: {self.stats['rating_change']:+d}
"""
        
        # Time control breakdown
        if 'time_control' in self.games_df.columns:
            time_stats = self.games_df.groupby('time_category')['result'].agg(['count', lambda x: (x == 'win').sum() / len(x) * 100]).round(1)
            time_stats.columns = ['games', 'win_rate']
            
            summary += "\n**Time Control Breakdown:**\n"
            for category, stats in time_stats.iterrows():
                if stats['games'] > 0:
                    summary += f"- {category}: {int(stats['games'])} games ({stats['win_rate']:.1f}% win rate)\n"
        
        # Stockfish summary
        stockfish_cols = ['player_avg_cpl', 'player_blunders', 'player_mistakes', 'player_inaccuracies']
        if any(col in self.games_df.columns for col in stockfish_cols):
            summary += "\n**Engine Analysis Average:**\n"
            for col in stockfish_cols:
                if col in self.games_df.columns:
                    avg_val = self.games_df[col].mean()
                    if pd.notna(avg_val):
                        clean_name = col.replace('player_', '').replace('_', ' ').title()
                        summary += f"- {clean_name}: {avg_val:.1f}\n"
        
        return summary.strip()
    
    def generate_full_report(self) -> str:
        """Generate the complete performance review report."""
        logger.info("Generating full performance review report...")
        
        if self.games_df.empty:
            return "No games available for analysis. Please ensure the games DataFrame contains data."
        
        # Get date range for report header
        if 'date' in self.games_df.columns:
            start_date = self.games_df['date'].min().strftime('%Y-%m-%d')
            end_date = self.games_df['date'].max().strftime('%Y-%m-%d')
            date_range = f"Period: {start_date} to {end_date}"
        else:
            date_range = "Period: Unknown"
        
        # Generate each section
        overall_trends = self.generate_overall_trends()
        opening_review = self.generate_opening_review()
        time_control_breakdown = self.generate_time_control_breakdown()
        strengths_weaknesses = self.generate_strengths_weaknesses()
        coaching_recommendations = self.generate_coaching_recommendations()
        stats_summary = self.generate_stats_summary()
        
        # Compile full report
        report = f"""# Chess Performance Review - {self.username}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{date_range}
Games Analyzed: {len(self.games_df)}

## Overall Trends

{overall_trends}

## Opening Repertoire Review

{opening_review}

## Time Control Breakdown

{time_control_breakdown}

## Strengths and Weaknesses

{strengths_weaknesses}

## Coaching Recommendations

{coaching_recommendations}

## Stats Summary

{stats_summary}

---
*Report generated by MAIgnus_CAIrlsen Chess Coaching System*
"""
        
        return report
    
    def save_report(self, filename: str = "performance_review.txt") -> bool:
        """
        Save the performance review report to a file.
        
        Args:
            filename (str): Name of the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure reports directory exists
            os.makedirs(REPORTS_DIR, exist_ok=True)
            
            # Generate and save report
            report = self.generate_full_report()
            file_path = os.path.join(REPORTS_DIR, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Performance review saved to {file_path}")
            print(f"✅ Performance review saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            print(f"❌ Error saving report: {e}")
            return False


def get_recent_events(db_path, limit=5):
    """Get recent non-null event names from the database."""
    import duckdb
    try:
        with duckdb.connect(db_path) as conn:
            result = conn.execute("""
                SELECT DISTINCT event_name, MAX(date) as latest_date
                FROM game_analysis 
                WHERE event_name IS NOT NULL 
                GROUP BY event_name 
                ORDER BY latest_date DESC 
                LIMIT ?
            """, [limit]).fetchall()
            return [(event, date) for event, date in result]
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        return []

def prompt_event_selection(db_path):
    """Prompt user to select a recent event for review."""
    events = get_recent_events(db_path)
    if not events:
        print("❌ No events found in database")
        return None

    print("\n📅 Recent Events:")
    print("-" * 50)
    for i, (event_name, latest_date) in enumerate(events, 1):
        print(f"{i}. {event_name} (latest: {latest_date})")

    while True:
        try:
            choice = input(f"\nSelect event (1-{len(events)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(events):
                selected_event = events[choice_num - 1][0]
                print(f"✅ Selected: {selected_event}")
                return selected_event
            else:
                print(f"❌ Invalid choice. Please enter 1-{len(events)})")
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q'")
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            return None

def main():
    import argparse
    from analysis import ChessAnalyzer

    parser = argparse.ArgumentParser(description="Generate a periodic chess performance review")
    parser.add_argument('--db', default='../database/MAIgnus.db', help='Path to DuckDB database')
    parser.add_argument('--filter', choices=['6months', '1year'], help='Date filter for review')
    parser.add_argument('--event-prompt', action='store_true', help='Prompt to select an event')
    parser.add_argument('--last-n', type=int, help='Analyze only the N most recent games')
    parser.add_argument('--output', default='performance_review.txt', help='Output file name')

    args = parser.parse_args()

    if args.event_prompt and args.last_n:
        print("❌ Cannot use --event-prompt and --last-n together.")
        return

    db_path = args.db
    event_name = None

    if args.event_prompt:
        event_name = prompt_event_selection(db_path)
        if not event_name:
            return

    analyzer = ChessAnalyzer(db_path)
    analyzer.load_data(date_filter=args.filter, limit=None, event_name=event_name, last_n=args.last_n)

    if analyzer.games_df.empty:
        print("❌ No games found. Exiting.")
        return

    reviewer = PeriodicReviewer(analyzer.games_df)
    reviewer.save_report(args.output)

    # Send the email
    from periodic_reviewer_email import send_performance_review_email
    send_performance_review_email(analyzer.games_df)

if __name__ == "__main__":
    main()
