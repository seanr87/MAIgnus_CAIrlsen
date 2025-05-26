#!/usr/bin/env python3
"""
Chess Game Performance Analysis Script
=====================================

This script analyzes chess game data stored in a DuckDB database to provide
comprehensive performance insights including win/loss statistics, opening
analysis, time control performance, rating tracking, and trend analysis.

Author: MAIgnus_CAIrlsen
Created: 2025-05-11
"""

import duckdb
import gc
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from contextlib import contextmanager
from functools import wraps
import time
import argparse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chess_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_execution_time(func):
    """Decorator to log execution time of functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Completed {func.__name__} in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed {func.__name__} after {execution_time:.2f} seconds: {e}")
            raise
    return wrapper

class ChessAnalyzer:
    """
    A comprehensive chess game analyzer that examines various aspects of player performance.
    """
    
    def __init__(self, db_path: str = 'database/MAIgnus.db', chunk_size: int = 1000):
        """
        Initialize the chess analyzer with database connection.

        Args:
            db_path (str): Path to the DuckDB database file
            chunk_size (int): Size of chunks for data loading
        """
        self.db_path = self._find_database(db_path)
        self.chunk_size = chunk_size
        self.games_df = None
        
        # Initialize performance metrics
        self._performance_metrics = {
            'data_load_time': 0,
            'total_analysis_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info(f"ChessAnalyzer initialized with database: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections with proper error handling.
        """
        conn = None
        try:
            logger.debug("Opening database connection")
            conn = duckdb.connect(self.db_path)
            yield conn
        except duckdb.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error with database connection: {e}")
            raise
        finally:
            if conn:
                logger.debug("Closing database connection")
                conn.close()
    
    def _find_database(self, db_name: str) -> str:
        """Find the database file in common locations."""
        possible_paths = [
            db_name,
            f'database/{db_name}',
            f'../{db_name}',
            f'../database/{db_name}'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found database at: {path}")
                return path
        
        raise FileNotFoundError(f"Database {db_name} not found in any expected location")
    
    @log_execution_time
    def load_data(self, date_filter: Optional[str] = None, limit: Optional[int] = None, event_name: Optional[str] = None, last_n: Optional[int] = None) -> None:
        """
        Load game data from the database with optimized chunked reading and filtering.
        
        Args:
            date_filter (str, optional): Date filter ('6months', '1year', or 'YYYY-MM-DD') - ignored if event_name is provided
            limit (int, optional): Maximum number of games to load
            event_name (str, optional): Filter by specific event name (takes priority over date_filter)
            last_n (int, optional): Load only the N most recent games
        """
        try:
            start_time = time.time()
            
            # Build query with optional filters
            base_query = """
            SELECT 
                game_id,
                date,
                player_color,
                opponent_name,
                time_control,
                opening_name,
                event_name,
                result,
                player_rating,
                opponent_rating
            FROM game_analysis
            """
            
            # Build WHERE clause with filters
            where_conditions = []
            query_params = []
            
            # Priority: event_name filtering (ignores date_filter if present)
            if event_name:
                where_conditions.append("event_name = ?")
                query_params.append(event_name)
                logger.info(f"Filtering by event_name: {event_name}")
            # Add date filtering only if no event_name is specified
            elif date_filter:
                if date_filter == '6months':
                    where_conditions.append("date >= ?")
                    query_params.append((datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'))
                elif date_filter == '1year':
                    where_conditions.append("date >= ?")
                    query_params.append((datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
                elif len(date_filter) == 10:  # Assume YYYY-MM-DD format
                    where_conditions.append("date >= ?")
                    query_params.append(date_filter)
            
            # Build WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Add ORDER BY and LIMIT
            order_limit = "ORDER BY date DESC"
            
            # Handle last_n parameter
            if last_n:
                order_limit += f" LIMIT {last_n}"
            elif limit:
                order_limit += f" LIMIT {limit}"
            
            full_query = f"{base_query} {where_clause} {order_limit}"
            logger.info(f"Executing query: {full_query}")
            logger.info(f"Query parameters: {query_params}")
            
            # Load data in chunks if dataset is expected to be large
            with self._get_connection() as conn:
                # First, get the total count
                count_query = f"SELECT COUNT(*) as total FROM game_analysis {where_clause}"
                total_rows = conn.execute(count_query, query_params).fetchone()[0]
                logger.info(f"Total rows to load: {total_rows}")
                
                if total_rows == 0:
                    logger.warning("No data found with the specified filters")
                    self.games_df = pd.DataFrame()
                    return
                
                # Load data efficiently
                actual_limit = last_n or limit
                if total_rows > self.chunk_size and not actual_limit:
                    # Calculate how many records we actually want to load
                    records_to_load = min(total_rows, limit) if limit else total_rows
                    logger.info(f"Loading {records_to_load} records in chunks of {self.chunk_size}")
                    chunks = []
                    
                    records_loaded = 0
                    offset = 0
                    
                    while records_loaded < records_to_load:
                        # Calculate how many records to fetch in this chunk
                        records_needed = min(self.chunk_size, records_to_load - records_loaded)
                        chunk_query = f"{base_query} {where_clause} ORDER BY date DESC OFFSET {offset} LIMIT {records_needed}"
                        
                        chunk_df = conn.execute(chunk_query, query_params).df()
                        chunks.append(chunk_df)
                        
                        records_loaded += len(chunk_df)
                        offset += records_needed
                        
                        logger.debug(f"Loaded chunk {len(chunks)}: {len(chunk_df)} records, total: {records_loaded}/{records_to_load}")
                    
                    self.games_df = pd.concat(chunks, ignore_index=True)
                    
                    # Free memory from chunks list
                    del chunks
                    gc.collect()
                    logger.debug("Memory garbage collection completed after chunk concatenation")
                else:
                    self.games_df = conn.execute(full_query, query_params).df()
                
                # Convert date column to datetime
                self.games_df['date'] = pd.to_datetime(self.games_df['date'])
                
                # Precompute commonly used columns
                self.games_df['time_category'] = self.games_df['time_control'].apply(self.categorize_time_control)
                self.games_df['opponent_rating_range'] = pd.cut(
                    self.games_df['opponent_rating'],
                    bins=[0, 1000, 1200, 1400, 1600, 1800, 2000, 3000],
                    labels=['<1000', '1000-1200', '1200-1400', '1400-1600', '1600-1800', '1800-2000', '2000+']
                )
                
                self._performance_metrics['data_load_time'] = time.time() - start_time
                logger.info(f"Successfully loaded {len(self.games_df)} games")
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def analyze_win_loss_draw(self) -> Dict:
        """
        Analyze win/loss/draw statistics.
        
        Returns:
            Dict containing win/loss/draw counts and percentages
        """
        logger.info("Analyzing win/loss/draw statistics...")
        
        if self.games_df.empty:
            return {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'win_rate': 0,
                'loss_rate': 0,
                'draw_rate': 0
            }
        
        result_counts = self.games_df['result'].value_counts()
        total_games = len(self.games_df)
        
        analysis = {
            'total_games': total_games,
            'wins': result_counts.get('win', 0),
            'losses': result_counts.get('loss', 0),
            'draws': result_counts.get('draw', 0),
            'win_rate': (result_counts.get('win', 0) / total_games * 100) if total_games > 0 else 0,
            'loss_rate': (result_counts.get('loss', 0) / total_games * 100) if total_games > 0 else 0,
            'draw_rate': (result_counts.get('draw', 0) / total_games * 100) if total_games > 0 else 0
        }
        
        return analysis
    
    def analyze_openings(self) -> Dict:
        """
        Analyze opening performance and frequencies.
        
        Returns:
            Dict containing opening statistics and performance
        """
        logger.info("Analyzing opening performance...")
        
        if self.games_df.empty:
            return {
                'most_played_openings': pd.DataFrame(),
                'best_win_rate_openings': pd.DataFrame(),
                'unique_openings': 0
            }
        
        # Group by opening and calculate statistics
        opening_stats = self.games_df.groupby('opening_name').agg({
            'result': ['count', lambda x: (x == 'win').sum(), 
                      lambda x: (x == 'loss').sum(), 
                      lambda x: (x == 'draw').sum()]
        }).round(2)
        
        opening_stats.columns = ['total_games', 'wins', 'losses', 'draws']
        opening_stats['win_rate'] = (opening_stats['wins'] / opening_stats['total_games'] * 100).round(2)
        opening_stats['loss_rate'] = (opening_stats['losses'] / opening_stats['total_games'] * 100).round(2)
        opening_stats['draw_rate'] = (opening_stats['draws'] / opening_stats['total_games'] * 100).round(2)
        
        # Sort by frequency and win rate
        most_played = opening_stats.sort_values('total_games', ascending=False).head(10)
        best_openings = opening_stats[opening_stats['total_games'] >= 3].sort_values('win_rate', ascending=False).head(10)
        
        return {
            'most_played_openings': most_played,
            'best_win_rate_openings': best_openings,
            'unique_openings': len(opening_stats)
        }
    
    def categorize_time_control(self, time_control: str) -> str:
        """
        Categorize time control into standard chess categories.
        
        Args:
            time_control (str): Time control string (e.g., "10+0", "5+3")
        
        Returns:
            str: Category (Bullet, Blitz, Rapid, Classical)
        """
        if not time_control or time_control == 'Unknown':
            return 'Unknown'
        
        try:
            # Parse time control (e.g., "10+0" means 10 minutes base + 0 increment)
            if '+' in time_control:
                base_time = int(time_control.split('+')[0])
            else:
                base_time = int(time_control)
            
            # Categorize based on base time
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
    
    def analyze_time_controls(self) -> Dict:
        """
        Analyze performance across different time controls.
        
        Returns:
            Dict containing time control performance statistics
        """
        logger.info("Analyzing time control performance...")
        
        if self.games_df.empty:
            return {'time_control_stats': pd.DataFrame()}
        
        # Use the pre-computed time_category column instead of recreating it
        time_stats = self.games_df.groupby('time_category').agg({
            'result': ['count', lambda x: (x == 'win').sum(), 
                      lambda x: (x == 'loss').sum(), 
                      lambda x: (x == 'draw').sum()]
        }).round(2)
        
        time_stats.columns = ['total_games', 'wins', 'losses', 'draws']
        time_stats['win_rate'] = (time_stats['wins'] / time_stats['total_games'] * 100).round(2)
        time_stats['loss_rate'] = (time_stats['losses'] / time_stats['total_games'] * 100).round(2)
        time_stats['draw_rate'] = (time_stats['draws'] / time_stats['total_games'] * 100).round(2)
        
        return {'time_control_stats': time_stats}
    
    def analyze_ratings(self) -> Dict:
        """
        Analyze player rating statistics and trends.
        
        Returns:
            Dict containing rating statistics and trends
        """
        logger.info("Analyzing rating statistics...")
        
        if self.games_df.empty:
            return {
                'current_rating': 0,
                'highest_rating': 0,
                'lowest_rating': 0,
                'average_rating': 0,
                'rating_std': 0,
                'recent_30_games_avg': 0,
                'rating_trend': 'N/A'
            }
        
        # Basic rating statistics
        rating_stats = {
            'current_rating': self.games_df.iloc[0]['player_rating'],  # Most recent game
            'highest_rating': self.games_df['player_rating'].max(),
            'lowest_rating': self.games_df['player_rating'].min(),
            'average_rating': self.games_df['player_rating'].mean().round(0),
            'rating_std': self.games_df['player_rating'].std().round(0)
        }
        
        # Rating trend (last 30 games)
        last_30_games = self.games_df.head(30)
        recent_avg = last_30_games['player_rating'].mean()
        
        # Rating changes over time periods
        rating_changes = {
            'recent_30_games_avg': recent_avg.round(0),
            'rating_trend': 'improving' if recent_avg > rating_stats['average_rating'] else 'declining'
        }
        
        rating_stats.update(rating_changes)
        return rating_stats
    
    def analyze_performance_over_time(self) -> Dict:
        """
        Analyze performance trends over time periods.
        
        Returns:
            Dict containing time-based performance analysis
        """
        logger.info("Analyzing performance over time...")
        
        if self.games_df.empty:
            return {
                'monthly_performance': pd.DataFrame(),
                'weekly_performance': pd.DataFrame(),
                'daily_performance': pd.DataFrame()
            }
        
        # Set date as index for time-based analysis
        time_df = self.games_df.set_index('date').sort_index()
        
        # Monthly performance
        monthly_stats = time_df.groupby(pd.Grouper(freq='ME')).agg({
            'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100]
        }).round(2)
        monthly_stats.columns = ['games_played', 'win_rate']
        
        # Weekly performance (last 8 weeks)
        weekly_stats = time_df.groupby(pd.Grouper(freq='W')).agg({
            'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100 if len(x) > 0 else 0]
        }).round(2)
        weekly_stats.columns = ['games_played', 'win_rate']
        weekly_stats = weekly_stats.tail(8)
        
        # Performance by day of week
        time_df['day_of_week'] = time_df.index.day_name()
        daily_stats = time_df.groupby('day_of_week').agg({
            'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100]
        }).round(2)
        daily_stats.columns = ['games_played', 'win_rate']
        
        return {
            'monthly_performance': monthly_stats.tail(6),  # Last 6 months
            'weekly_performance': weekly_stats,
            'daily_performance': daily_stats
        }
    
    def generate_opponent_analysis(self) -> Dict:
        """
        Analyze performance against different opponents.
        
        Returns:
            Dict containing opponent-based analysis
        """
        logger.info("Analyzing opponent performance...")
        
        if self.games_df.empty:
            return {
                'frequent_opponents': pd.DataFrame(),
                'performance_by_opponent_rating': pd.DataFrame()
            }
        
        # Performance against specific opponents (opponents faced multiple times)
        opponent_stats = self.games_df.groupby('opponent_name').agg({
            'result': ['count', lambda x: (x == 'win').sum(), 
                      lambda x: (x == 'loss').sum(), 
                      lambda x: (x == 'draw').sum()]
        }).round(2)
        
        opponent_stats.columns = ['total_games', 'wins', 'losses', 'draws']
        opponent_stats['win_rate'] = (opponent_stats['wins'] / opponent_stats['total_games'] * 100).round(2)
        
        # Filter for opponents faced 3+ times
        frequent_opponents = opponent_stats[opponent_stats['total_games'] >= 3].sort_values('total_games', ascending=False)
        
        # Use pre-computed opponent_rating_range column
        rating_range_stats = self.games_df.groupby('opponent_rating_range', observed=True).agg({
            'result': ['count', lambda x: (x == 'win').sum() / len(x) * 100 if len(x) > 0 else 0]
        }).round(2)
        rating_range_stats.columns = ['games_played', 'win_rate']
        
        return {
            'frequent_opponents': frequent_opponents.head(10),
            'performance_by_opponent_rating': rating_range_stats
        }
    
    def print_analysis_summary(self):
        """Print a comprehensive analysis summary to the console."""
        print("\n" + "="*80)
        print("🏆 CHESS PERFORMANCE ANALYSIS SUMMARY")
        print("="*80)
        
        # Overall Performance
        overall = self.analyze_win_loss_draw()
        print(f"\n📊 OVERALL PERFORMANCE")
        print(f"-" * 40)
        print(f"Total Games: {overall['total_games']}")
        print(f"Wins: {overall['wins']} ({overall['win_rate']:.1f}%)")
        print(f"Losses: {overall['losses']} ({overall['loss_rate']:.1f}%)")
        print(f"Draws: {overall['draws']} ({overall['draw_rate']:.1f}%)")
        
        # Rating Analysis
        ratings = self.analyze_ratings()
        print(f"\n📈 RATING ANALYSIS")
        print(f"-" * 40)
        print(f"Current Rating: {ratings['current_rating']}")
        print(f"Highest Rating: {ratings['highest_rating']}")
        print(f"Lowest Rating: {ratings['lowest_rating']}")
        print(f"Average Rating: {ratings['average_rating']}")
        print(f"Recent Trend: {ratings['rating_trend'].upper()}")
        
        # Opening Analysis
        openings = self.analyze_openings()
        print(f"\n♟️  OPENING ANALYSIS")
        print(f"-" * 40)
        print(f"Total Unique Openings: {openings['unique_openings']}")
        
        if not openings['most_played_openings'].empty:
            print("\nMost Played Openings:")
            for opening, stats in openings['most_played_openings'].head(5).iterrows():
                print(f"  {opening}: {int(stats['total_games'])} games ({stats['win_rate']:.1f}% win rate)")
        
        if not openings['best_win_rate_openings'].empty:
            print("\nBest Win Rate Openings (3+ games):")
            for opening, stats in openings['best_win_rate_openings'].head(5).iterrows():
                print(f"  {opening}: {stats['win_rate']:.1f}% ({int(stats['total_games'])} games)")
        
        # Time Control Analysis
        time_controls = self.analyze_time_controls()
        print(f"\n⏱️  TIME CONTROL ANALYSIS")
        print(f"-" * 40)
        time_stats = time_controls['time_control_stats']
        if not time_stats.empty:
            for category, stats in time_stats.iterrows():
                if stats['total_games'] > 0:
                    print(f"{category}: {int(stats['total_games'])} games ({stats['win_rate']:.1f}% win rate)")
        
        # Recent Performance
        time_analysis = self.analyze_performance_over_time()
        print(f"\n📅 RECENT PERFORMANCE")
        print(f"-" * 40)
        weekly_performance = time_analysis['weekly_performance']
        if not weekly_performance.empty:
            print("Last 4 weeks win rate:")
            for date, stats in weekly_performance.tail(4).iterrows():
                if stats['games_played'] > 0:
                    print(f"  Week of {date.strftime('%Y-%m-%d')}: {stats['win_rate']:.1f}% ({int(stats['games_played'])} games)")
        
        # Opponent Analysis
        opponents = self.generate_opponent_analysis()
        print(f"\n🎯 OPPONENT ANALYSIS")
        print(f"-" * 40)
        frequent_opponents = opponents['frequent_opponents']
        if not frequent_opponents.empty:
            print("Most Faced Opponents:")
            for opponent, stats in frequent_opponents.head(5).iterrows():
                print(f"  {opponent}: {int(stats['total_games'])} games ({stats['win_rate']:.1f}% win rate)")
        
        print(f"\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)
    
    def save_detailed_report(self, filename: str = 'chess_analysis_report.txt'):
        """
        Save a detailed analysis report to a file.
        
        Args:
            filename (str): Name of the file to save the report
        """
        logger.info(f"Saving detailed report to {filename}")
        
        # Use UTF-8 encoding to handle emojis properly
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("CHESS PERFORMANCE ANALYSIS - DETAILED REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total games analyzed: {len(self.games_df)}\n\n")
            
            # Redirect stdout to file and generate analysis
            import contextlib
            with contextlib.redirect_stdout(f):
                self.print_analysis_summary()
        
        print(f"\n📄 Detailed report saved to {filename}")

def get_recent_events(db_path, limit=5):
    """Get the most recent non-null event names from the database."""
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
    """Prompt user to select an event name from recent events."""
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
                print(f"❌ Invalid choice. Please enter 1-{len(events)}")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q'")
        except KeyboardInterrupt:
            print("\n\n❌ Selection cancelled")
            return None

def get_recent_events(db_path, limit=5):
    """Get the most recent non-null event names from the database."""
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
    """Prompt user to select an event name from recent events."""
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
                print(f"❌ Invalid choice. Please enter 1-{len(events)}")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number or 'q'")
        except KeyboardInterrupt:
            print("\n\n❌ Selection cancelled")
            return None


def main():
    """Main function to run the chess analysis."""
    parser = argparse.ArgumentParser(description='Analyze chess game performance')
    parser.add_argument('--db', default='MAIgnus.db', help='Database file path')
    parser.add_argument('--filter', choices=['6months', '1year'], help='Date filter for analysis')
    parser.add_argument('--limit', type=int, help='Limit number of games to analyze')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Chunk size for data loading')
    parser.add_argument('--output', default='chess_analysis_report.txt', help='Output report filename')
    parser.add_argument('--event-prompt', action='store_true', help='Interactively select an event name to filter analysis')
    parser.add_argument('--last-n', type=int, help='Analyze the N most recent games')
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.event_prompt and args.last_n:
        print("❌ Error: --event-prompt and --last-n cannot be used together")
        sys.exit(1)
    
    try:
        # Handle event selection if requested
        selected_event = None
        if args.event_prompt:
            logger.info("Event selection mode enabled")
            selected_event = prompt_event_selection(args.db)
            if selected_event is None:
                logger.info("No event selected, exiting")
                return
        # Initialize analyzer
        logger.info("Initializing chess analyzer...")
        analyzer = ChessAnalyzer(db_path=args.db, chunk_size=args.chunk_size)

        # Load data
        logger.info("Loading data...")
        analyzer.load_data(date_filter=args.filter, limit=args.limit, event_name=selected_event)

        # Run comprehensive analysis
        logger.info("Running analysis...")
        analyzer.print_analysis_summary()

        # Save detailed report
        logger.info("Saving report...")
        analyzer.save_detailed_report(args.output)

        logger.info("Analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()