#!/usr/bin/env python3
"""
Test script for event filtering functionality in analysis.py
"""
import sys
import os
import duckdb

# Add the current directory to Python path to import analysis module
sys.path.insert(0, '.')

try:
    from src.analysis import ChessAnalyzer, get_recent_events, prompt_event_selection
except ImportError as e:
    print(f"❌ Error importing analysis module: {e}")
    print("Make sure analysis.py is in the current directory")
    sys.exit(1)

def test_database_connection():
    """Test that we can connect to the database."""
    print("🔗 Testing database connection...")
    try:
        analyzer = ChessAnalyzer()
        print(f"✅ Connected to database: {analyzer.db_path}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_get_recent_events():
    """Test the get_recent_events function."""
    print("\n📅 Testing get_recent_events()...")
    try:
        analyzer = ChessAnalyzer()
        events = get_recent_events(analyzer.db_path, limit=5)
        
        if not events:
            print("⚠️  No events found in database")
            return False
        
        print(f"✅ Found {len(events)} recent events:")
        for i, (event_name, latest_date) in enumerate(events, 1):
            print(f"   {i}. {event_name} (latest: {latest_date})")
        
        return True
    except Exception as e:
        print(f"❌ get_recent_events() failed: {e}")
        return False

def test_load_data_with_event():
    """Test loading data with event filtering."""
    print("\n🔍 Testing load_data() with event filtering...")
    try:
        analyzer = ChessAnalyzer()
        
        # First, get an event to test with
        events = get_recent_events(analyzer.db_path, limit=1)
        if not events:
            print("⚠️  No events available for testing")
            return False
        
        test_event = events[0][0]
        print(f"📊 Testing with event: '{test_event}'")
        
        # Load data with event filter
        analyzer.load_data(event_name=test_event)
        
        if analyzer.games_df.empty:
            print(f"⚠️  No games found for event '{test_event}'")
            return False
        
        print(f"✅ Loaded {len(analyzer.games_df)} games for event '{test_event}'")
        
        # Verify all games have the correct event name
        if 'event_name' in analyzer.games_df.columns:
            unique_events = analyzer.games_df['event_name'].unique()
            if len(unique_events) == 1 and unique_events[0] == test_event:
                print(f"✅ All games correctly filtered to event '{test_event}'")
            else:
                print(f"❌ Filtering failed. Found events: {unique_events}")
                return False
        else:
            print("⚠️  event_name column not found in results")
        
        # Show sample data
        print(f"📋 Sample games:")
        sample_cols = ['date', 'opponent_name', 'event_name', 'result']
        available_cols = [col for col in sample_cols if col in analyzer.games_df.columns]
        if available_cols:
            print(analyzer.games_df[available_cols].head(3).to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ load_data() with event filtering failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_load_data_without_event():
    """Test loading data without event filtering (normal operation)."""
    print("\n🔍 Testing load_data() without event filtering...")
    try:
        analyzer = ChessAnalyzer()
        
        # Load data without event filter (limit to 10 for quick test)
        analyzer.load_data(limit=10)
        
        if analyzer.games_df.empty:
            print("⚠️  No games found in database")
            return False
        
        print(f"✅ Loaded {len(analyzer.games_df)} games without event filter")
        
        # Show unique events in the data
        if 'event_name' in analyzer.games_df.columns:
            unique_events = analyzer.games_df['event_name'].dropna().unique()
            print(f"📊 Found {len(unique_events)} unique events in sample")
            if len(unique_events) > 0:
                print(f"   Events: {list(unique_events)[:3]}...")  # Show first 3
        
        return True
        
    except Exception as e:
        print(f"❌ load_data() without event filtering failed: {e}")
        return False

def test_interactive_selection():
    """Test the interactive event selection (simulation)."""
    print("\n🎯 Testing interactive event selection...")
    try:
        analyzer = ChessAnalyzer()
        events = get_recent_events(analyzer.db_path)
        
        if not events:
            print("⚠️  No events available for interactive testing")
            return False
        
        print("📅 Available events for selection:")
        for i, (event_name, latest_date) in enumerate(events, 1):
            print(f"   {i}. {event_name} (latest: {latest_date})")
        
        print("✅ Interactive selection setup working")
        print("💡 To test interactively, run: python analysis.py --event-prompt")
        
        return True
        
    except Exception as e:
        print(f"❌ Interactive selection test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Event Filtering Functionality")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Get Recent Events", test_get_recent_events),
        ("Load Data Without Event", test_load_data_without_event),
        ("Load Data With Event", test_load_data_with_event),
        ("Interactive Selection Setup", test_interactive_selection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"⚠️  {test_name}: FAILED or INCOMPLETE")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"🏆 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Event filtering is working correctly.")
        print("\n💡 Try these commands to test manually:")
        print("   python analysis.py --event-prompt")
        print("   python analysis.py --last-n 5")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)