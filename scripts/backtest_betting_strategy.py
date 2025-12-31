#!/usr/bin/env python3
"""
Backtest betting strategies from an evaluation CSV (eval_data_*.csv).

Goal: optimize ROI, not accuracy.

Assumptions:
- The evaluation CSV contains 2 rows per fight (each fighter as "f1" once).
- Each row has:
  - fight_key
  - target (1 if f1 won, else 0)
  - model_prob_f1
  - fighter1_odds / fighter2_odds and fighter1_prob / fighter2_prob (odds-file ordering)
  - fighter1_norm_odds / fighter2_norm_odds and f1_name_norm (to map odds -> f1)

We create a fight-level decision:
  - Compute EV for betting each side
  - Bet at most 1 side per fight (the side with highest EV) if EV > threshold
  - Support flat stake or fractional Kelly sizing (with caps)
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd


def american_payout_per_unit(odds: float) -> float:
    """Profit on a 1-unit stake if the bet wins (excluding return of stake)."""
    o = float(odds)
    if o == 0:
        return float("nan")
    if o > 0:
        return o / 100.0
    return 100.0 / (-o)


def expected_profit_per_unit(p_win: float, odds: float) -> float:
    """Expected profit in units for staking 1 unit at given odds with win prob p_win."""
    payout = american_payout_per_unit(odds)
    if not np.isfinite(payout):
        return float("nan")
    p = float(p_win)
    return p * payout - (1.0 - p) * 1.0


def kelly_fraction(p_win: float, odds: float) -> float:
    """
    Kelly fraction for staking a proportion of bankroll:
      f* = (b*p - q) / b  where b is decimal profit per unit stake, q=1-p
    We return max(0, f*) (no shorting).
    """
    b = american_payout_per_unit(odds)
    if not np.isfinite(b) or b <= 0:
        return 0.0
    p = float(p_win)
    q = 1.0 - p
    f = (b * p - q) / b
    return max(0.0, f)


def safe_div(n: float, d: float) -> float:
    return float(n) / float(d) if d else float("nan")


@dataclass(frozen=True)
class BacktestResult:
    n_fights: int
    n_bets: int
    staked: float
    profit: float
    roi: float
    win_rate: float
    avg_edge: float
    avg_ev: float


def _require_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _add_row_mapped_odds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add:
      - odds_for_f1
      - market_prob_f1_raw (already exists as market_prob_f1 in eval_data, but keep consistent)
      - market_prob_f1_novig (normalize within fight_key)
      - payout_for_f1
    """
    _require_cols(
        df,
        [
            "fight_key",
            "f1_name_norm",
            "fighter1_norm_odds",
            "fighter2_norm_odds",
            "fighter1_odds",
            "fighter2_odds",
            "fighter1_prob",
            "fighter2_prob",
            "market_prob_f1",
        ],
    )

    df = df.copy()
    is_f1_fighter1 = df["f1_name_norm"].astype(str) == df["fighter1_norm_odds"].astype(str)
    df["odds_for_f1"] = np.where(is_f1_fighter1, df["fighter1_odds"], df["fighter2_odds"])
    df["market_prob_f1_raw"] = df["market_prob_f1"]

    # No-vig: normalize within each fight_key using odds-file ordering, then map back to the row.
    # (Avoid groupby.apply warnings by computing first() then joining.)
    market_pair = (
        df.groupby("fight_key", as_index=True)[["fighter1_prob", "fighter2_prob"]]
        .first()
        .rename(columns={"fighter1_prob": "p1_raw", "fighter2_prob": "p2_raw"})
    )
    market_pair["psum"] = market_pair["p1_raw"] + market_pair["p2_raw"]
    market_pair["p1_novig"] = market_pair["p1_raw"] / market_pair["psum"]
    market_pair["p2_novig"] = market_pair["p2_raw"] / market_pair["psum"]

    df = df.join(market_pair[["p1_novig", "p2_novig"]], on="fight_key")
    df["market_prob_f1_novig"] = np.where(is_f1_fighter1, df["p1_novig"], df["p2_novig"])
    df = df.drop(columns=["p1_novig", "p2_novig"], errors="ignore")
    df["payout_for_f1"] = df["odds_for_f1"].apply(american_payout_per_unit)
    return df


def backtest_one_bet_per_fight(
    df_eval: pd.DataFrame,
    *,
    strategy: str = "best_ev",
    min_ev: float = 0.0,
    min_p: float = 0.0,
    min_edge: float = 0.0,
    symmetric: bool = True,  # Default True: handle order-sensitive models by averaging both perspectives
    sizing: str = "flat",
    flat_stake: float = 1.0,
    bankroll: float = 100.0,
    kelly_multiplier: float = 0.25,
    max_bet_fraction: float = 0.02,
    verbose: bool = False,
    show_bets: bool = False,
) -> BacktestResult:
    """
    Build one decision per fight_key:
      - strategy=best_ev: pick side with highest EV; if EV <= min_ev => no bet
      - strategy=winner: pick side with highest model_prob_f1 (the model's predicted winner)
      - strategy=winner_underdog_only: same as winner, but only bet if that side is the underdog
      - Optional min_p: require chosen side model_prob_f1 >= min_p (confidence filter)
      - stake via flat or (fractional) Kelly with cap
    """
    _require_cols(df_eval, ["fight_key", "target", "model_prob_f1", "edge"])
    df = _add_row_mapped_odds(df_eval)

    # Optional symmetric probability:
    # eval_data has 2 rows per fight_key (each fighter is f1 once). Some models are order-sensitive,
    # so p(f1 wins | f1,f2) is not guaranteed to equal 1 - p(f2 wins | f2,f1).
    #
    # We compute a symmetric per-row win prob:
    #   p_sym(row) = 0.5 * ( p_row + (1 - p_other_row) )   when exactly 2 rows exist for fight_key
    #
    # This yields a stable probability for EV regardless of row ordering.
    if symmetric:
        df = df.copy()
        df["model_prob_f1_raw"] = df["model_prob_f1"].astype(float)
        grp_count = df.groupby("fight_key")["model_prob_f1_raw"].transform("count")
        grp_sum = df.groupby("fight_key")["model_prob_f1_raw"].transform("sum")
        other_p = grp_sum - df["model_prob_f1_raw"]

        df["model_prob_f1_sym"] = np.where(
            grp_count == 2,
            0.5 * (df["model_prob_f1_raw"] + (1.0 - other_p)),
            df["model_prob_f1_raw"],
        )
        prob_col = "model_prob_f1_sym"
    else:
        prob_col = "model_prob_f1"

    # Compute per-row EV and "edge" vs no-vig market as an alternative diagnostic
    df["ev_per_unit"] = df.apply(
        lambda r: expected_profit_per_unit(r[prob_col], r["odds_for_f1"]),
        axis=1,
    )
    df["edge_novig"] = df[prob_col] - df["market_prob_f1_novig"]

    strategy = str(strategy).strip().lower()
    if strategy not in {"best_ev", "winner", "winner_underdog_only"}:
        raise ValueError("strategy must be one of: best_ev, winner, winner_underdog_only")

    # Pick one side per fight
    if strategy == "best_ev":
        best_rows = (
            df.sort_values(["fight_key", "ev_per_unit"], ascending=[True, False])
            .groupby("fight_key", as_index=False)
            .head(1)
            .copy()
        )
    else:
        # winner / winner_underdog_only: choose the side with higher model_prob_f1
        best_rows = (
            df.sort_values(["fight_key", prob_col], ascending=[True, False])
            .groupby("fight_key", as_index=False)
            .head(1)
            .copy()
        )

    n_fights = int(best_rows["fight_key"].nunique())

    bets = best_rows.copy()

    # Optional confidence filter (this is your "hold off" lever without ever betting against the model)
    try:
        min_p = float(min_p)
    except (TypeError, ValueError):
        min_p = 0.0
    if min_p > 0:
        bets = bets[bets[prob_col] >= min_p].copy()

    # Optional edge filter (model prob - market prob)
    try:
        min_edge = float(min_edge)
    except (TypeError, ValueError):
        min_edge = 0.0
    if min_edge > 0:
        bets = bets[bets["edge_novig"] >= min_edge].copy()

    # Strategy-specific filters
    if strategy == "best_ev":
        bets = bets[bets["ev_per_unit"] > float(min_ev)].copy()
    elif strategy == "winner_underdog_only":
        # Under\-dog = lower market implied probability
        # We use the no-vig prob for stability; raw also works.
        bets = bets[bets["market_prob_f1_novig"] < 0.5].copy()

    if bets.empty:
        return BacktestResult(
            n_fights=n_fights,
            n_bets=0,
            staked=0.0,
            profit=0.0,
            roi=float("nan"),
            win_rate=float("nan"),
            avg_edge=float("nan"),
            avg_ev=float("nan"),
        )

    sizing = str(sizing).lower().strip()
    if sizing not in {"flat", "kelly"}:
        raise ValueError("sizing must be one of: flat, kelly")

    if sizing == "flat":
        bets["stake"] = float(flat_stake)
    else:
        # Fractional Kelly with a cap per bet (as % bankroll)
        km = float(kelly_multiplier)
        cap = float(max_bet_fraction)
        br = float(bankroll)

        def _stake_row(r) -> float:
            f = kelly_fraction(r[prob_col], r["odds_for_f1"])
            f = max(0.0, min(f * km, cap))
            return br * f

        bets["stake"] = bets.apply(_stake_row, axis=1)

    # Realized profits
    def _profit_row(r) -> float:
        stake = float(r["stake"])
        if stake <= 0:
            return 0.0
        payout = american_payout_per_unit(r["odds_for_f1"])
        win = int(r["target"]) == 1  # row is "f1" perspective
        return stake * (payout if win else -1.0)

    bets["profit"] = bets.apply(_profit_row, axis=1)

    staked = float(bets["stake"].sum())
    profit = float(bets["profit"].sum())
    roi = safe_div(profit, staked)
    win_rate = safe_div((bets["profit"] > 0).sum(), len(bets))

    # Verbose diagnostics
    if verbose:
        print("\n" + "=" * 80)
        print("VERBOSE DIAGNOSTICS")
        print("=" * 80)
        
        # Check for order sensitivity (model is order-sensitive if p(A|A,B) + p(B|B,A) != 1.0)
        if not symmetric:
            order_sensitivity_check = df.groupby("fight_key").apply(
                lambda g: abs(g["model_prob_f1"].sum() - 1.0) if len(g) == 2 else 0.0
            )
            avg_order_sensitivity = order_sensitivity_check.mean()
            max_order_sensitivity = order_sensitivity_check.max()
            
            print(f"\nOrder sensitivity check (without --symmetric):")
            print(f"  Average deviation from symmetry: {avg_order_sensitivity:.4f}")
            print(f"  Max deviation:                  {max_order_sensitivity:.4f}")
            if avg_order_sensitivity > 0.01:
                print(f"  ⚠️  Model appears order-sensitive! Consider using --symmetric flag.")
                print(f"     (When fighters are flipped, probabilities don't sum to 1.0)")
            else:
                print(f"  ✓ Model appears order-invariant (probabilities sum to ~1.0)")
        
        # Check if winner and best_ev would pick the same sides (diagnostic)
        if strategy in {"best_ev", "winner"}:
            # Compare what winner strategy would pick vs best_ev
            winner_picks = (
                df.sort_values(["fight_key", prob_col], ascending=[True, False])
                .groupby("fight_key", as_index=False)
                .head(1)
                .copy()
            )
            best_ev_picks = (
                df.sort_values(["fight_key", "ev_per_unit"], ascending=[True, False])
                .groupby("fight_key", as_index=False)
                .head(1)
                .copy()
            )
            
            # Merge to compare
            winner_picks = winner_picks[["fight_key", "f1_name_norm", prob_col, "ev_per_unit"]].rename(
                columns={"f1_name_norm": "winner_side", prob_col: "winner_prob", "ev_per_unit": "winner_ev"}
            )
            best_ev_picks = best_ev_picks[["fight_key", "f1_name_norm", prob_col, "ev_per_unit"]].rename(
                columns={"f1_name_norm": "best_ev_side", prob_col: "best_ev_prob", "ev_per_unit": "best_ev_ev"}
            )
            
            comparison = winner_picks.merge(best_ev_picks, on="fight_key", how="inner")
            same_side = (comparison["winner_side"] == comparison["best_ev_side"]).sum()
            total_comparable = len(comparison)
            
            print(f"\nStrategy comparison diagnostic:")
            print(f"  Fights where 'winner' and 'best_ev' pick same side: {same_side}/{total_comparable} ({same_side/total_comparable:.1%})")
            if same_side < total_comparable:
                diff_fights = comparison[comparison["winner_side"] != comparison["best_ev_side"]]
                print(f"  Fights where they differ: {len(diff_fights)}")
                if len(diff_fights) > 0:
                    print(f"  Example differences:")
                    for idx, row in diff_fights.head(3).iterrows():
                        print(f"    {row['fight_key']}: winner picks {row['winner_side']} (prob={row['winner_prob']:.2f}, EV={row['winner_ev']:.3f})")
                        print(f"                      best_ev picks {row['best_ev_side']} (prob={row['best_ev_prob']:.2f}, EV={row['best_ev_ev']:.3f})")
        
        # Track filtering stages
        n_after_pick = len(best_rows)
        n_after_min_p = len(best_rows[best_rows[prob_col] >= min_p]) if min_p > 0 else n_after_pick
        n_after_min_edge = len(best_rows[(best_rows[prob_col] >= min_p) & (best_rows["edge_novig"] >= min_edge)]) if (min_p > 0 or min_edge > 0) else (len(best_rows[best_rows["edge_novig"] >= min_edge]) if min_edge > 0 else n_after_min_p)
        n_after_strategy = len(bets)
        
        print(f"\nFiltering stages:")
        print(f"  Total fights in eval:        {n_fights}")
        print(f"  After picking best side:     {n_after_pick}")
        if min_p > 0:
            print(f"  After min_p={min_p:.2f} filter:     {n_after_min_p} ({n_after_pick - n_after_min_p} skipped)")
        if min_edge > 0:
            prev_count = n_after_min_p if min_p > 0 else n_after_pick
            print(f"  After min_edge={min_edge:.3f} filter:  {n_after_min_edge} ({prev_count - n_after_min_edge} skipped)")
        if strategy == "best_ev" and min_ev > 0:
            prev_for_ev = n_after_min_edge if min_edge > 0 else (n_after_min_p if min_p > 0 else n_after_pick)
            n_after_ev = len(best_rows[
                (best_rows[prob_col] >= min_p if min_p > 0 else True) &
                (best_rows["edge_novig"] >= min_edge if min_edge > 0 else True) &
                (best_rows["ev_per_unit"] > min_ev)
            ])
            print(f"  After min_ev={min_ev:.3f} filter:     {n_after_ev} ({prev_for_ev - n_after_ev} skipped)")
        elif strategy == "winner_underdog_only":
            prev_for_underdog = n_after_min_edge if min_edge > 0 else (n_after_min_p if min_p > 0 else n_after_pick)
            n_after_underdog = len(best_rows[
                (best_rows[prob_col] >= min_p if min_p > 0 else True) &
                (best_rows["edge_novig"] >= min_edge if min_edge > 0 else True) &
                (best_rows["market_prob_f1_novig"] < 0.5)
            ])
            print(f"  After underdog filter:        {n_after_underdog} ({prev_for_underdog - n_after_underdog} skipped)")
        print(f"  Final bets placed:            {n_after_strategy}")
        
        # Underdog analysis (all fights, not just bets)
        all_fights = best_rows.copy()
        all_fights["is_underdog"] = all_fights["market_prob_f1_novig"] < 0.5
        all_fights["is_favorite"] = all_fights["market_prob_f1_novig"] >= 0.5
        
        total_underdogs = all_fights["is_underdog"].sum()
        underdog_wins = all_fights[all_fights["is_underdog"]]["target"].sum()
        underdog_win_rate = safe_div(underdog_wins, total_underdogs)
        
        total_favorites = all_fights["is_favorite"].sum()
        favorite_wins = all_fights[all_fights["is_favorite"]]["target"].sum()
        favorite_win_rate = safe_div(favorite_wins, total_favorites)
        
        print(f"\nMarket-based underdog/favorite breakdown (all fights):")
        print(f"  Total underdog fights:        {total_underdogs}")
        print(f"  Underdog wins:                {underdog_wins} ({underdog_win_rate:.1%})")
        print(f"  Total favorite fights:        {total_favorites}")
        print(f"  Favorite wins:                {favorite_wins} ({favorite_win_rate:.1%})")
        
        # Bet-level underdog/favorite breakdown
        if len(bets) > 0:
            bet_underdogs = bets["market_prob_f1_novig"] < 0.5
            bet_favorites = bets["market_prob_f1_novig"] >= 0.5
            
            n_bet_underdogs = bet_underdogs.sum()
            n_bet_favorites = bet_favorites.sum()
            
            if n_bet_underdogs > 0:
                underdog_bet_wins = bets[bet_underdogs]["profit"] > 0
                underdog_bet_win_rate = safe_div(underdog_bet_wins.sum(), n_bet_underdogs)
                underdog_bet_profit = bets[bet_underdogs]["profit"].sum()
                underdog_bet_roi = safe_div(underdog_bet_profit, bets[bet_underdogs]["stake"].sum())
                print(f"\nBet-level breakdown:")
                print(f"  Underdog bets:                {n_bet_underdogs}")
                print(f"    Win rate:                   {underdog_bet_win_rate:.1%}")
                print(f"    Profit:                     {underdog_bet_profit:.3f} units")
                print(f"    ROI:                        {underdog_bet_roi:.1%}")
            
            if n_bet_favorites > 0:
                favorite_bet_wins = bets[bet_favorites]["profit"] > 0
                favorite_bet_win_rate = safe_div(favorite_bet_wins.sum(), n_bet_favorites)
                favorite_bet_profit = bets[bet_favorites]["profit"].sum()
                favorite_bet_roi = safe_div(favorite_bet_profit, bets[bet_favorites]["stake"].sum())
                print(f"  Favorite bets:                {n_bet_favorites}")
                print(f"    Win rate:                   {favorite_bet_win_rate:.1%}")
                print(f"    Profit:                     {favorite_bet_profit:.3f} units")
                print(f"    ROI:                        {favorite_bet_roi:.1%}")
        
        # Model probability distribution
        if len(bets) > 0:
            print(f"\nModel probability distribution (bets only):")
            print(f"  Min:                          {bets[prob_col].min():.3f}")
            print(f"  25th percentile:              {bets[prob_col].quantile(0.25):.3f}")
            print(f"  Median:                       {bets[prob_col].median():.3f}")
            print(f"  75th percentile:              {bets[prob_col].quantile(0.75):.3f}")
            print(f"  Max:                          {bets[prob_col].max():.3f}")
            print(f"  Mean:                         {bets[prob_col].mean():.3f}")
        
        # Win rate by confidence bins
        if len(bets) > 0:
            print(f"\nWin rate by model confidence bins:")
            bins = [0.0, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.0]
            bets["prob_bin"] = pd.cut(bets[prob_col], bins=bins, include_lowest=True)
            for bin_name, group in bets.groupby("prob_bin", observed=True):
                n = len(group)
                wins = (group["profit"] > 0).sum()
                wr = safe_div(wins, n)
                if n > 0:
                    print(f"  {bin_name}: {n:3d} bets, {wins:3d} wins ({wr:.1%})")
        
        # Edge distribution
        if len(bets) > 0:
            print(f"\nEdge distribution (model prob - market prob, no-vig):")
            print(f"  Min:                          {bets['edge_novig'].min():.4f}")
            print(f"  25th percentile:              {bets['edge_novig'].quantile(0.25):.4f}")
            print(f"  Median:                       {bets['edge_novig'].median():.4f}")
            print(f"  75th percentile:              {bets['edge_novig'].quantile(0.75):.4f}")
            print(f"  Max:                          {bets['edge_novig'].max():.4f}")
            print(f"  Mean:                         {bets['edge_novig'].mean():.4f}")
        
        # EV distribution
        if len(bets) > 0:
            print(f"\nEV distribution (expected profit per unit):")
            print(f"  Min:                          {bets['ev_per_unit'].min():.4f}")
            print(f"  25th percentile:              {bets['ev_per_unit'].quantile(0.25):.4f}")
            print(f"  Median:                       {bets['ev_per_unit'].median():.4f}")
            print(f"  75th percentile:              {bets['ev_per_unit'].quantile(0.75):.4f}")
            print(f"  Max:                          {bets['ev_per_unit'].max():.4f}")
            print(f"  Mean:                         {bets['ev_per_unit'].mean():.4f}")
        
        print("=" * 80)

    # Show individual bets for historical validation
    if show_bets and len(bets) > 0:
        print("\n" + "=" * 80)
        print("INDIVIDUAL BETS (for historical validation)")
        print("=" * 80)
        
        # Prepare display columns (use available columns from eval_data)
        display_cols = []
        if "event_day" in bets.columns:
            display_cols.append("event_day")
        elif "event_date" in bets.columns:
            display_cols.append("event_date")
        
        if "f1_name" in bets.columns:
            display_cols.append("f1_name")
        if "f2_name" in bets.columns:
            display_cols.append("f2_name")
        
        # Add bet details
        bets_display = bets.copy()
        bets_display["bet_side_name"] = bets_display.apply(
            lambda r: r.get("f1_name", "Fighter 1") if pd.notna(r.get("f1_name")) else "Fighter 1",
            axis=1
        )
        bets_display["opponent_name"] = bets_display.apply(
            lambda r: r.get("f2_name", "Fighter 2") if pd.notna(r.get("f2_name")) else "Fighter 2",
            axis=1
        )
        bets_display["bet_odds"] = bets_display["odds_for_f1"]
        bets_display["model_prob"] = bets_display[prob_col]
        bets_display["market_prob"] = bets_display["market_prob_f1_novig"]
        bets_display["edge"] = bets_display["edge_novig"]
        bets_display["ev"] = bets_display["ev_per_unit"]
        bets_display["won"] = (bets_display["profit"] > 0).astype(int)
        bets_display["outcome"] = bets_display["won"].map({1: "WIN", 0: "LOSS"})
        bets_display["profit_display"] = bets_display["profit"]
        
        # Sort by date (if available) then by profit
        sort_cols = []
        if "event_day" in bets_display.columns:
            sort_cols.append("event_day")
        elif "event_date" in bets_display.columns:
            sort_cols.append("event_date")
        sort_cols.append("profit")
        
        bets_display = bets_display.sort_values(sort_cols, ascending=[True, False])
        
        # Build display dataframe
        display_df = pd.DataFrame({
            "Date": bets_display.get("event_day", bets_display.get("event_date", "N/A")),
            "Bet On": bets_display["bet_side_name"],
            "vs": bets_display["opponent_name"],
            "Odds": bets_display["bet_odds"].astype(int),
            "Model Prob": bets_display["model_prob"].apply(lambda x: f"{x:.1%}"),
            "Market Prob": bets_display["market_prob"].apply(lambda x: f"{x:.1%}"),
            "Edge": bets_display["edge"].apply(lambda x: f"{x:+.3f}"),
            "EV": bets_display["ev"].apply(lambda x: f"{x:+.4f}"),
            "Outcome": bets_display["outcome"],
            "Profit": bets_display["profit_display"].apply(lambda x: f"{x:+.3f}u"),
        })
        
        print(f"\nTotal bets: {len(display_df)}")
        print(f"Wins: {(bets_display['won'] == 1).sum()}, Losses: {(bets_display['won'] == 0).sum()}")
        print("\n" + display_df.to_string(index=False))
        
        # Summary by outcome
        print("\n" + "-" * 80)
        print("Summary by outcome:")
        wins_df = bets_display[bets_display["won"] == 1]
        losses_df = bets_display[bets_display["won"] == 0]
        
        if len(wins_df) > 0:
            print(f"\nWINS ({len(wins_df)} bets):")
            print(f"  Total profit: {wins_df['profit'].sum():.3f} units")
            print(f"  Avg profit per win: {wins_df['profit'].mean():.3f} units")
            print(f"  Avg odds: {wins_df['bet_odds'].mean():.1f}")
            print(f"  Avg model prob: {wins_df['model_prob'].mean():.3f}")
        
        if len(losses_df) > 0:
            print(f"\nLOSSES ({len(losses_df)} bets):")
            print(f"  Total loss: {losses_df['profit'].sum():.3f} units")
            print(f"  Avg loss per bet: {losses_df['profit'].mean():.3f} units")
            print(f"  Avg odds: {losses_df['bet_odds'].mean():.1f}")
            print(f"  Avg model prob: {losses_df['model_prob'].mean():.3f}")
        
        print("=" * 80)

    return BacktestResult(
        n_fights=n_fights,
        n_bets=int(len(bets)),
        staked=staked,
        profit=profit,
        roi=roi,
        win_rate=win_rate,
        avg_edge=float(bets["edge_novig"].mean()),
        avg_ev=float(bets["ev_per_unit"].mean()),
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Backtest betting strategies from eval_data CSV")
    p.add_argument("--eval-data", type=str, required=True, help="Path to eval_data_*.csv")
    p.add_argument(
        "--strategy",
        type=str,
        default="best_ev",
        choices=["best_ev", "winner", "winner_underdog_only"],
        help=(
            "Betting rule. "
            "best_ev = bet side with highest EV if EV>min_ev. "
            "winner = bet model's predicted winner (max model_prob_f1) regardless of EV. "
            "winner_underdog_only = only bet when the model-predicted winner is also the underdog."
        ),
    )
    p.add_argument("--min-ev", type=float, default=0.0, help="Only bet if EV per 1-unit stake > this threshold")
    p.add_argument(
        "--min-p",
        type=float,
        default=0.0,
        help="Only bet if chosen side model_prob >= this (confidence filter). For winner-strategies, this is your main 'hold off' knob.",
    )
    p.add_argument(
        "--min-edge",
        type=float,
        default=0.0,
        help="Only bet if edge (model_prob - market_prob, no-vig) >= this threshold. Useful for filtering out bets where model and market agree closely.",
    )
    p.add_argument("--sizing", type=str, default="flat", choices=["flat", "kelly"], help="Stake sizing method")
    p.add_argument("--flat-stake", type=float, default=1.0, help="Stake per bet when sizing=flat")
    p.add_argument("--bankroll", type=float, default=100.0, help="Bankroll used for Kelly sizing")
    p.add_argument("--kelly-multiplier", type=float, default=0.25, help="Fractional Kelly multiplier (e.g. 0.25)")
    p.add_argument("--max-bet-fraction", type=float, default=0.02, help="Cap per bet as fraction of bankroll (Kelly)")
    p.add_argument(
        "--sweep",
        action="store_true",
        help="Sweep min-ev thresholds and print a small ROI table (flat sizing).",
    )
    p.add_argument("--sweep-max-ev", type=float, default=0.10, help="Max EV threshold for sweep (inclusive)")
    p.add_argument("--sweep-step", type=float, default=0.01, help="Step size for sweep")
    p.add_argument(
        "--symmetric",
        action="store_true",
        default=True,
        help=(
            "Use symmetric probabilities per fight_key (reduces model order-sensitivity). "
            "Computes model_prob_f1_sym from the two eval_data rows per fight and uses it for EV/selection. "
            "DEFAULT: True. Use --no-symmetric to disable."
        ),
    )
    p.add_argument(
        "--no-symmetric",
        dest="symmetric",
        action="store_false",
        help="Disable symmetric probability computation (use raw model_prob_f1).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print extensive diagnostic statistics (underdog win rates, filtering stages, probability/edge distributions, etc.)",
    )
    p.add_argument(
        "--show-bets",
        action="store_true",
        help="Print a detailed table of all individual bets with fighter names, odds, outcomes, and profit for historical validation",
    )

    args = p.parse_args()
    df = pd.read_csv(args.eval_data)

    if args.sweep:
        # Sweep min_ev thresholds for flat stakes only (simple, avoids overfitting on sizing).
        step = float(args.sweep_step)
        if step <= 0:
            raise ValueError("--sweep-step must be > 0")
        thresholds = np.arange(0.0, float(args.sweep_max_ev) + 1e-9, step)
        rows = []
        for t in thresholds:
            r = backtest_one_bet_per_fight(
                df,
                strategy=str(args.strategy),
                min_ev=float(t),
                min_p=float(args.min_p),
                min_edge=float(args.min_edge),
                symmetric=bool(args.symmetric),
                sizing="flat",
                flat_stake=float(args.flat_stake),
                verbose=False,  # Disable verbose during sweeps
                show_bets=False,  # Disable show_bets during sweeps
            )
            rows.append(
                {
                    "min_ev": round(float(t), 4),
                    "bets": r.n_bets,
                    "profit": round(r.profit, 3),
                    "staked": round(r.staked, 3),
                    "roi": round(r.roi, 4) if np.isfinite(r.roi) else float("nan"),
                    "win_rate": round(r.win_rate, 4) if np.isfinite(r.win_rate) else float("nan"),
                    "avg_ev": round(r.avg_ev, 4) if np.isfinite(r.avg_ev) else float("nan"),
                    "avg_edge_novig": round(r.avg_edge, 4) if np.isfinite(r.avg_edge) else float("nan"),
                }
            )
        out = pd.DataFrame(rows)
        out = out.sort_values(["roi", "bets"], ascending=[False, False])
        # print best 15
        print(out.head(15).to_string(index=False))
        return

    res = backtest_one_bet_per_fight(
        df,
        strategy=str(args.strategy),
        min_ev=float(args.min_ev),
        min_p=float(args.min_p),
        min_edge=float(args.min_edge),
        symmetric=bool(args.symmetric),
        sizing=str(args.sizing),
        flat_stake=float(args.flat_stake),
        bankroll=float(args.bankroll),
        kelly_multiplier=float(args.kelly_multiplier),
        max_bet_fraction=float(args.max_bet_fraction),
        verbose=bool(args.verbose),
        show_bets=bool(args.show_bets),
    )

    print("\n" + "=" * 80)
    print("BETTING BACKTEST (one bet per fight)")
    print("=" * 80)
    print(f"eval fights:         {res.n_fights}")
    print(f"bets placed:         {res.n_bets}")
    print(f"total staked:        {res.staked:.3f} units")
    print(f"total profit:        {res.profit:.3f} units")
    print(f"ROI:                {res.roi:.3%}" if np.isfinite(res.roi) else "ROI:                N/A")
    print(f"bet win rate:        {res.win_rate:.3%}" if np.isfinite(res.win_rate) else "bet win rate:        N/A")
    print(f"avg EV per unit:     {res.avg_ev:.4f}")
    print(f"avg edge (no-vig):   {res.avg_edge:.4f}")


if __name__ == "__main__":
    main()


