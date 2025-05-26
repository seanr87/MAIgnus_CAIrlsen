#!/usr/bin/env python3
"""
Periodic Performance Review Email Module for MAIgnus Chess Coaching System
=========================================================================

This module sends sophisticated performance review emails with detailed insights,
game highlights, trends, and coaching recommendations. Designed to provide
tournament-level feedback similar to what a professional chess coach would deliver.

Author: MAIgnus_CAIrlsen
Created: 2025-05-25
"""

import os
import re
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from openai import OpenAI

from config import (
    OPENAI_API_KEY, 
    GPT_MODEL,
    SENDER_EMAIL, 
    EMAIL_APP_PASSWORD, 
    RECEIVER_EMAIL,
    REPORTS_DIR, 
    EMAIL_LOG,
    CHESS_USERNAME
)
from utils import log

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

class PerformanceEmailGenerator:
    """
    Generates and sends sophisticated periodic performance review emails.
    """
    
    def __init__(self, games_df=None, username=CHESS_USERNAME):
        """
        Initialize the performance email generator.
        
        Args:
            games_df (pd.DataFrame, optional): DataFrame containing game data
            username (str): Player's username
        """
        self.games_df = games_df.copy() if games_df is not None and not games_df.empty else pd.DataFrame()
        self.username = username
        self.performance_insights = {}
        
        log("PerformanceEmailGenerator initialized", EMAIL_LOG)
        
        if not self.games_df.empty:
            self._prepare_data()
            self._generate_insights()
    
    def _prepare_data(self):
        """Prepare and clean the games DataFrame for analysis."""
        try:
            # Ensure date column is datetime
            if 'date' in self.games_df.columns:
                self.games_df['date'] = pd.to_datetime(self.games_df['date'])
                self.games_df = self.games_df.sort_values('date')
            
            # Fill missing values for analysis
            numeric_columns = ['player_avg_cpl', 'player_blunders', 'player_mistakes', 'player_inaccuracies']
            for col in numeric_columns:
                if col in self.games_df.columns:
                    self.games_df[col] = pd.to_numeric(self.games_df[col], errors='coerce').fillna(0)
            
            log(f"Data prepared: {len(self.games_df)} games ready for analysis", EMAIL_LOG)
            
        except Exception as e:
            log(f"Error preparing data: {e}", EMAIL_LOG)
    
    def _generate_insights(self):
        """Generate all performance insights from the games data."""
        if self.games_df.empty:
            log("No games data available for insights generation", EMAIL_LOG)
            return
        
        try:
            self.performance_insights = {
                'best_game': self._find_best_game(),
                'worst_game': self._find_worst_game(),
                'accuracy_trend': self._analyze_accuracy_trend(),
                'skill_summary': self._generate_skill_summary(),
                'date_range': self._get_date_range()
            }
            log("Performance insights generated successfully", EMAIL_LOG)
            
        except Exception as e:
            log(f"Error generating insights: {e}", EMAIL_LOG)
            self.performance_insights = {}
    
    def _find_best_game(self):
        """Find the player's best performing game based on accuracy metrics."""
        if self.games_df.empty:
            return None
        
        try:
            # Score games based on multiple criteria
            scored_games = self.games_df.copy()
            
            # Primary scoring: low CPL is better
            if 'player_avg_cpl' in scored_games.columns:
                scored_games['cpl_score'] = 100 - scored_games['player_avg_cpl'].clip(0, 100)
            else:
                scored_games['cpl_score'] = 50  # Neutral score if no CPL data
            
            # Bonus for zero blunders
            if 'player_blunders' in scored_games.columns:
                scored_games['blunder_bonus'] = (scored_games['player_blunders'] == 0).astype(int) * 20
            else:
                scored_games['blunder_bonus'] = 0
            
            # Bonus for wins
            if 'result' in scored_games.columns:
                scored_games['result_bonus'] = (scored_games['result'] == 'win').astype(int) * 10
            else:
                scored_games['result_bonus'] = 0
            
            # Calculate total score
            scored_games['total_score'] = (
                scored_games['cpl_score'] + 
                scored_games['blunder_bonus'] + 
                scored_games['result_bonus']
            )
            
            # Find best game
            best_game_idx = scored_games['total_score'].idxmax()
            best_game = scored_games.loc[best_game_idx]
            
            return {
                'opponent': best_game.get('opponent_name', 'Unknown'),
                'result': best_game.get('result', 'Unknown'),
                'opening': best_game.get('opening_name', 'Unknown'),
                'date': best_game.get('date', 'Unknown'),
                'cpl': best_game.get('player_avg_cpl', 'N/A'),
                'blunders': best_game.get('player_blunders', 'N/A'),
                'score': best_game['total_score'],
                'pgn_text': best_game.get('pgn_text', '')
            }
            
        except Exception as e:
            log(f"Error finding best game: {e}", EMAIL_LOG)
            return None
    
    def _find_worst_game(self):
        """Find the player's worst performing game."""
        if self.games_df.empty:
            return None
        
        try:
            # Score games based on negative criteria
            scored_games = self.games_df.copy()
            
            # Primary scoring: high CPL is worse
            if 'player_avg_cpl' in scored_games.columns:
                scored_games['cpl_penalty'] = scored_games['player_avg_cpl'].clip(0, 200)
            else:
                scored_games['cpl_penalty'] = 0
            
            # Penalty for blunders
            if 'player_blunders' in scored_games.columns:
                scored_games['blunder_penalty'] = scored_games['player_blunders'] * 30
            else:
                scored_games['blunder_penalty'] = 0
            
            # Penalty for losses
            if 'result' in scored_games.columns:
                scored_games['result_penalty'] = (scored_games['result'] == 'loss').astype(int) * 20
            else:
                scored_games['result_penalty'] = 0
            
            # Calculate total penalty score
            scored_games['total_penalty'] = (
                scored_games['cpl_penalty'] + 
                scored_games['blunder_penalty'] + 
                scored_games['result_penalty']
            )
            
            # Find worst game
            worst_game_idx = scored_games['total_penalty'].idxmax()
            worst_game = scored_games.loc[worst_game_idx]
            
            return {
                'opponent': worst_game.get('opponent_name', 'Unknown'),
                'result': worst_game.get('result', 'Unknown'),
                'opening': worst_game.get('opening_name', 'Unknown'),
                'date': worst_game.get('date', 'Unknown'),
                'cpl': worst_game.get('player_avg_cpl', 'N/A'),
                'blunders': worst_game.get('player_blunders', 'N/A'),
                'pgn_text': worst_game.get('pgn_text', ''),
                'penalty_score': worst_game['total_penalty']
            }
            
        except Exception as e:
            log(f"Error finding worst game: {e}", EMAIL_LOG)
            return None
    
    def _analyze_accuracy_trend(self):
        """Analyze accuracy trend by splitting games into thirds."""
        if self.games_df.empty or len(self.games_df) < 3:
            return None
        
        try:
            # Split games into thirds
            n_games = len(self.games_df)
            third = n_games // 3
            
            early_games = self.games_df.iloc[:third]
            mid_games = self.games_df.iloc[third:2*third]
            late_games = self.games_df.iloc[2*third:]
            
            # Calculate average CPL for each period
            trend_data = {}
            for period_name, period_games in [('early', early_games), ('mid', mid_games), ('late', late_games)]:
                if 'player_avg_cpl' in period_games.columns:
                    avg_cpl = period_games['player_avg_cpl'].mean()
                    trend_data[period_name] = avg_cpl
                else:
                    trend_data[period_name] = None
            
            # Determine trend direction
            if all(v is not None for v in trend_data.values()):
                early_cpl = trend_data['early']
                late_cpl = trend_data['late']
                
                if late_cpl < early_cpl - 5:
                    trend_direction = "improving"
                elif late_cpl > early_cpl + 5:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "unknown"
            
            return {
                'early_cpl': trend_data.get('early'),
                'mid_cpl': trend_data.get('mid'),
                'late_cpl': trend_data.get('late'),
                'trend_direction': trend_direction,
                'improvement': trend_data.get('early', 0) - trend_data.get('late', 0) if all(v is not None for v in [trend_data.get('early'), trend_data.get('late')]) else 0
            }
            
        except Exception as e:
            log(f"Error analyzing accuracy trend: {e}", EMAIL_LOG)
            return None
    
    def _generate_skill_summary(self):
        """Generate skill summary using statistical analysis and GPT."""
        if self.games_df.empty:
            return None
        
        try:
            # Calculate basic stats
            stats = {}
            if 'player_avg_cpl' in self.games_df.columns:
                stats['avg_cpl'] = self.games_df['player_avg_cpl'].mean()
            if 'player_blunders' in self.games_df.columns:
                stats['avg_blunders'] = self.games_df['player_blunders'].mean()
                stats['blunder_rate'] = (self.games_df['player_blunders'] > 0).mean() * 100
            if 'result' in self.games_df.columns:
                stats['win_rate'] = (self.games_df['result'] == 'win').mean() * 100
            
            # Use GPT to generate insights
            stats_text = "\n".join([f"- {k}: {v:.1f}" for k, v in stats.items()])
            
            prompt = f"""
Based on these chess performance statistics:
{stats_text}

Games analyzed: {len(self.games_df)}

Provide a brief skill assessment (2-3 lines max):
1. Strongest skill or tendency
2. Most common weakness or mistake pattern
3. One specific tactical area that needs work

Be direct and actionable, like a tournament coach would be.
"""
            
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach providing concise skill assessments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            skill_text = response.choices[0].message.content.strip()
            
            return {
                'stats': stats,
                'assessment': skill_text
            }
            
        except Exception as e:
            log(f"Error generating skill summary: {e}", EMAIL_LOG)
            return None
    
    def _get_date_range(self):
        """Get the date range of the analyzed games."""
        if self.games_df.empty or 'date' not in self.games_df.columns:
            return "Unknown period"
        
        try:
            start_date = self.games_df['date'].min().strftime('%Y-%m-%d')
            end_date = self.games_df['date'].max().strftime('%Y-%m-%d')
            return f"{start_date} to {end_date}"
        except:
            return "Unknown period"
    
    def _generate_best_game_summary(self, best_game):
        """Generate a brief summary of the best game using GPT."""
        if not best_game:
            return "No best game identified."
        
        try:
            pgn = best_game.get('pgn_text', '')

            prompt = f"""
            Briefly describe why this was a strong chess performance (1 sentence):

            Result: {best_game['result']} vs {best_game['opponent']}
            Opening: {best_game['opening']}
            Accuracy: {best_game['cpl']} average CPL
            Blunders: {best_game['blunders']}

            PGN of the game:
            {pgn}

            Focus on what made it a good game (accuracy, clean play, etc.).
            """

            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach commenting on good performances."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log(f"Error generating best game summary: {e}", EMAIL_LOG)
            return "Strong, accurate play."
    
    def _generate_worst_game_summary(self, worst_game):
        """Generate a brief summary of the worst game using GPT."""
        if not worst_game:
            return "No worst game identified."
        
        try:
            pgn = worst_game.get('pgn_text', '')

            prompt = f"""
            Briefly explain what went wrong in this chess game (1 sentence):

            Result: {worst_game['result']} vs {worst_game['opponent']}
            Opening: {worst_game['opening']}
            Accuracy: {worst_game['cpl']} average CPL
            Blunders: {worst_game['blunders']}

            PGN of the game:
            {pgn}

            Focus on the main issue (time pressure, tactical errors, etc.).
            """

            
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a chess coach analyzing problematic games."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            log(f"Error generating worst game summary: {e}", EMAIL_LOG)
            return "Accuracy issues and tactical errors."
    
    def _extract_coaching_focus_from_report(self):
        """Extract coaching recommendations from the performance review report."""
        try:
            report_path = os.path.join(REPORTS_DIR, "performance_review.txt")
            if not os.path.exists(report_path):
                return self._generate_fallback_coaching_focus()
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # Extract coaching recommendations section
            coaching_match = re.search(r"## Coaching Recommendations\s+(.*?)(?=\s+##|\Z)", report_content, re.DOTALL)
            
            if coaching_match:
                coaching_text = coaching_match.group(1).strip()
                
                # Use GPT to condense into email-friendly format
                prompt = f"""
Condense this coaching advice into 2 bullet points for an email:

{coaching_text}

Make each point actionable and specific (e.g., "Practice tactical puzzles daily" or "Study endgame patterns").
"""
                
                response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a chess coach creating concise action items."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                
                return response.choices[0].message.content.strip()
            else:
                return self._generate_fallback_coaching_focus()
                
        except Exception as e:
            log(f"Error extracting coaching focus: {e}", EMAIL_LOG)
            return self._generate_fallback_coaching_focus()
    
    def _generate_fallback_coaching_focus(self):
        """Generate basic coaching recommendations when report is unavailable."""
        if self.games_df.empty:
            return "• Continue regular practice\n• Focus on tactical awareness"
        
        try:
            # Basic analysis for fallback recommendations
            recommendations = []
            
            if 'player_blunders' in self.games_df.columns:
                avg_blunders = self.games_df['player_blunders'].mean()
                if avg_blunders > 1:
                    recommendations.append("• Reduce blunders through slower, more careful calculation")
            
            if 'player_avg_cpl' in self.games_df.columns:
                avg_cpl = self.games_df['player_avg_cpl'].mean()
                if avg_cpl > 50:
                    recommendations.append("• Improve position evaluation and candidate move selection")
            
            if len(recommendations) < 2:
                recommendations.append("• Study endgame techniques and tactical patterns")
            
            return "\n".join(recommendations[:2])
            
        except Exception as e:
            log(f"Error generating fallback coaching focus: {e}", EMAIL_LOG)
            return "• Continue regular practice\n• Focus on tactical awareness"
    
    def _format_trend_comment(self, trend_data):
        """Format the accuracy trend into a readable comment."""
        if not trend_data:
            return "Accuracy data unavailable."
        
        direction = trend_data['trend_direction']
        improvement = trend_data.get('improvement', 0)
        
        if direction == "improving":
            return f"Accuracy improving — {improvement:.1f} point CPL reduction over time period"
        elif direction == "declining":
            return f"Accuracy declining — {abs(improvement):.1f} point CPL increase needs attention"
        elif direction == "stable":
            return f"Consistent accuracy — {trend_data.get('late_cpl', 0):.1f} average CPL maintained"
        else:
            return "Mixed accuracy pattern — continue monitoring performance trends"
    
    def _create_email_content(self):
        """Create the main email content with performance insights."""
        try:
            # Get insights
            best_game = self.performance_insights.get('best_game')
            worst_game = self.performance_insights.get('worst_game')
            trend_data = self.performance_insights.get('accuracy_trend')
            skill_summary = self.performance_insights.get('skill_summary')
            date_range = self.performance_insights.get('date_range', 'Unknown period')
            
            # Generate game summaries
            best_summary = self._generate_best_game_summary(best_game) if best_game else "No standout game this period."
            worst_summary = self._generate_worst_game_summary(worst_game) if worst_game else "No problematic games identified."
            
            # Format trend comment
            trend_comment = self._format_trend_comment(trend_data)
            
            # Get coaching recommendations
            coaching_focus = self._extract_coaching_focus_from_report()
            
            # Create email body
            email_body = f"""Hi {self.username},

Here's your chess performance summary for {date_range}.

🏆 Best Game: {best_game['result'] if best_game else 'N/A'} vs {best_game['opponent'] if best_game else 'N/A'} ({best_game['opening'] if best_game else 'N/A'}) — {best_summary}

❌ Toughest Game: {worst_game['result'] if worst_game else 'N/A'} vs {worst_game['opponent'] if worst_game else 'N/A'} — {worst_summary}

📊 Accuracy Trend: {trend_comment}

Key takeaways:
{skill_summary['assessment'] if skill_summary else '• Continue working on tactical accuracy\n• Focus on endgame improvement\n• Practice time management'}

💡 Coaching Focus:
{coaching_focus}

Your full performance report is attached and saved to performance_review.txt.

Keep improving!
MAIgnus Chess Coach"""

            return email_body
            
        except Exception as e:
            log(f"Error creating email content: {e}", EMAIL_LOG)
            return self._create_fallback_email()
    
    def _create_fallback_email(self):
        """Create a basic email when detailed analysis fails."""
        return f"""Hi {self.username},

Your chess performance review is ready for the period analyzed.

The detailed analysis has been saved to your performance_review.txt file.

Continue practicing and stay focused on improvement!

MAIgnus Chess Coach"""
    
    def send_performance_email(self):
        """
        Send the performance review email with insights and attachments.
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            log("Starting performance email generation and sending", EMAIL_LOG)
            
            # Create email content
            email_content = self._create_email_content()
            
            # Generate subject line
            games_count = len(self.games_df) if not self.games_df.empty else 0
            date_range = self.performance_insights.get('date_range', 'Recent Period')
            subject = f"MAIgnus Performance Review: {games_count} Games Analyzed ({date_range})"
            
            # Create email message
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = SENDER_EMAIL
            msg["To"] = RECEIVER_EMAIL
            
            # Add email body
            msg.attach(MIMEText(email_content, "plain"))
            
            # Attach performance review file if it exists
            report_path = os.path.join(REPORTS_DIR, "performance_review.txt")
            if os.path.exists(report_path):
                try:
                    with open(report_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        'attachment; filename= "performance_review.txt"'
                    )
                    msg.attach(part)
                    log("Performance review attached to email", EMAIL_LOG)
                except Exception as e:
                    log(f"Could not attach performance review: {e}", EMAIL_LOG)
            
            # Send email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            
            log(f"✅ Performance email sent successfully with subject: {subject}", EMAIL_LOG)
            return True
            
        except Exception as e:
            log(f"❌ Failed to send performance email: {e}", EMAIL_LOG)
            return False


def send_performance_review_email(games_df=None, username=CHESS_USERNAME):
    """
    Main function to send a performance review email.
    
    Args:
        games_df (pd.DataFrame, optional): DataFrame with game data
        username (str): Player's username
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log("Initiating performance review email process", EMAIL_LOG)
        
        # Create email generator
        email_generator = PerformanceEmailGenerator(games_df, username)
        
        # Send the email
        success = email_generator.send_performance_email()
        
        if success:
            log("Performance review email process completed successfully", EMAIL_LOG)
        else:
            log("Performance review email process failed", EMAIL_LOG)
        
        return success
        
    except Exception as e:
        log(f"Error in performance review email process: {e}", EMAIL_LOG)
        return False


def main():
    """
    Main execution function for testing/standalone usage.
    """
    import argparse
    import sys
    import os
    
    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    parser = argparse.ArgumentParser(description="Send performance review email")
    parser.add_argument('--test', action='store_true', help='Test email generation without sending')
    parser.add_argument('--db', default='../database/MAIgnus.db', help='Path to database')
    
    args = parser.parse_args()
    
    try:
        # Load game data if database is available
        games_df = None
        if os.path.exists(args.db):
            try:
                import duckdb
                with duckdb.connect(args.db) as conn:
                    games_df = conn.execute("""
                        SELECT * FROM game_analysis 
                        ORDER BY date DESC 
                        LIMIT 50
                    """).df()
                log(f"Loaded {len(games_df)} games from database", EMAIL_LOG)
            except Exception as e:
                log(f"Could not load games from database: {e}", EMAIL_LOG)
        
        if args.test:
            # Test mode: create generator and show content
            generator = PerformanceEmailGenerator(games_df)
            content = generator._create_email_content()
            print("Email Content Preview:")
            print("="*60)
            print(content)
            print("="*60)
            return True
        else:
            # Send actual email
            return send_performance_review_email(games_df)
            
    except Exception as e:
        log(f"Error in main execution: {e}", EMAIL_LOG)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)