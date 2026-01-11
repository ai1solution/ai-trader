"""
Quick smoke test for v3.2 profit amplification features.

Tests:
1. Config v3.2 parameters are present
2. Regime-aware partial threshold selection
3. Loser suppression tracking
4. Engine basic functionality with v3.2

Usage:
    python test_v3_2_smoke.py
"""

import sys
from datetime import datetime
import pandas as pd
from rich.console import Console

from engine import EngineConfig
from engine.engine import TradingEngine, Position
from engine.logger import EngineLogger
from engine.enums import SignalType, Regime, TradingState
from engine.market_data import Tick

console = Console()


def test_config_v3_2():
    """Test that v3.2 config parameters exist."""
    console.print("\n[bold cyan]Test 1: Config v3.2 Parameters[/bold cyan]")
    
    config = EngineConfig()
    
    # Check new parameters exist
    assert hasattr(config, 'partial_take_pct_trending'), "Missing partial_take_pct_trending"
    assert hasattr(config, 'partial_take_pct_ranging'), "Missing partial_take_pct_ranging"
    assert hasattr(config, 'post_partial_trail_reduction'), "Missing post_partial_trail_reduction"
    assert hasattr(config, 'loser_suppression_enabled'), "Missing loser_suppression_enabled"
    assert hasattr(config, 'loser_streak_threshold'), "Missing loser_streak_threshold"
    assert hasattr(config, 'extended_cooldown_multiplier'), "Missing extended_cooldown_multiplier"
    
    # Check default values
    assert config.partial_take_pct_trending == 0.0045, f"Wrong trending threshold: {config.partial_take_pct_trending}"
    assert config.partial_take_pct_ranging == 0.0075, f"Wrong ranging threshold: {config.partial_take_pct_ranging}"
    assert config.post_partial_trail_reduction == 0.6, f"Wrong trail reduction: {config.post_partial_trail_reduction}"
    assert config.loser_streak_threshold == 3, f"Wrong loser threshold: {config.loser_streak_threshold}"
    
    console.print("[green]✓ All v3.2 config parameters present with correct defaults[/green]")
    return True


def test_position_post_partial_flag():
    """Test that Position has post-partial trail flag."""
    console.print("\n[bold cyan]Test 2: Position Post-Partial Trail Flag[/bold cyan]")
    
    pos = Position(
        entry_price=50000.0,
        entry_time=datetime.now(),
        size_usd=1000.0,
        direction=SignalType.LONG
    )
    
    assert hasattr(pos, '_post_partial_trail_active'), "Missing _post_partial_trail_active flag"
    assert pos._post_partial_trail_active == False, "Flag should be False initially"
    
    # Simulate partial take
    pos.execute_partial(50500.0, 0.5, datetime.now())
    assert pos.partial_taken == True, "Partial should be taken"
    
    console.print("[green]✓ Position has post-partial trail tracking[/green]")
    return True


def test_engine_loser_tracking():
    """Test that engine has loser suppression tracking."""
    console.print("\n[bold cyan]Test 3: Engine Loser Suppression Tracking[/bold cyan]")
    
    config = EngineConfig()
    logger = EngineLogger(log_file="logs/smoke_test.log", log_level="INFO")
    engine = TradingEngine(symbol="BTCUSDT", config=config, logger=logger)
    
    assert hasattr(engine, 'consecutive_stop_losses'), "Missing consecutive_stop_losses"
    assert hasattr(engine, 'current_cooldown_duration'), "Missing current_cooldown_duration"
    
    assert engine.consecutive_stop_losses == 0, "Counter should start at 0"
    assert engine.current_cooldown_duration == config.cooldown_duration_seconds, "Initial cooldown should be normal"
    
    console.print("[green]✓ Engine has loser suppression tracking[/green]")
    return True


def test_basic_tick_processing():
    """Test that engine can process ticks with v3.2 code."""
    console.print("\n[bold cyan]Test 4: Basic Tick Processing (v3.2)[/bold cyan]")
    
    config = EngineConfig(
        arm_velocity_threshold=0.001,  # Lower for testing
        arm_persistence_ticks=2,
        trailing_stop_pct=0.02,
    )
    
    logger = EngineLogger(log_file="logs/smoke_test.log", log_level="INFO")
    engine = TradingEngine(symbol="BTCUSDT", config=config, logger=logger)
    
    # Process some ticks
    base_price = 50000.0
    base_time = datetime.now()
    
    try:
        for i in range(20):
            # Simulate some price movement
            price = base_price + (i * 10)  # Gradual rise
            tick = Tick(
                timestamp=base_time,
                price=price,
                volume=1.0
            )
            engine.on_tick(tick)
        
        console.print(f"  Ticks processed: {engine.tick_count}")
        console.print(f"  Current state: {engine.state_machine.get_state().name}")
        console.print("[green]✓ Engine processes ticks successfully[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Error processing ticks: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_state_machine_cooldown():
    """Test that state machine supports dynamic cooldown."""
    console.print("\n[bold cyan]Test 5: State Machine Dynamic Cooldown[/bold cyan]")
    
    from engine.state import StateMachine
    
    config = EngineConfig()
    sm = StateMachine(config)
    
    assert hasattr(sm.context, 'cooldown_duration'), "Missing cooldown_duration in context"
    assert hasattr(sm, 'set_cooldown_duration'), "Missing set_cooldown_duration method"
    
    # Test setting custom cooldown
    sm.set_cooldown_duration(180.0)
    assert sm.context.cooldown_duration == 180.0, "Cooldown duration not set correctly"
    
    console.print("[green]✓ State machine supports dynamic cooldown[/green]")
    return True


def main():
    """Run all smoke tests."""
    console.print("\n" + "="*80, style="bold blue")
    console.print("v3.2 PROFIT AMPLIFICATION - SMOKE TESTS", style="bold blue", justify="center")
    console.print("="*80, style="bold blue")
    
    tests = [
        test_config_v3_2,
        test_position_post_partial_flag,
        test_engine_loser_tracking,
        test_basic_tick_processing,
        test_state_machine_cooldown,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            console.print(f"[red]✗ {test.__name__} failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    console.print("\n" + "="*80, style="bold")
    console.print(f"[cyan]Tests Passed:[/cyan] {passed}/{len(tests)}")
    console.print(f"[cyan]Tests Failed:[/cyan] {failed}/{len(tests)}")
    
    if failed == 0:
        console.print("\n[bold green]✓ All smoke tests passed! v3.2 is ready for historical testing.[/bold green]")
        return 0
    else:
        console.print("\n[bold red]✗ Some tests failed. Fix issues before historical testing.[/bold red]")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
