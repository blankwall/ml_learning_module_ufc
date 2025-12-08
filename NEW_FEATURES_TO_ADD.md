# New Features To Add

This document lists features that are not yet implemented but would be valuable for the UFC prediction model.

## Tier 2 (High Value) - Missing Features

### 1. Competition Quality (Opponent Ranks in Recent Fights)
**Status**: ❌ Not Implemented  
**Priority**: High  
**Description**: Track the quality of opponents faced in recent fights. This helps distinguish between fighters who beat top competition vs. those who pad records against weak opponents.

**Implementation Notes**:
- Requires ranking data (UFC rankings, betting odds, or ELO-style ratings)
- Could calculate: average opponent ranking in last 3/5 fights
- Alternative: use opponent win rate as proxy for quality
- Features to add:
  - `avg_opponent_win_rate_last_3`
  - `avg_opponent_win_rate_last_5`
  - `top_ranked_opponent_wins` (wins against ranked opponents)
  - `opponent_quality_score` (weighted average)

**Data Requirements**: 
- Opponent rankings (may need to scrape or calculate from betting odds)
- Or use opponent career win rate as proxy

---

### 2. Finish Rate Trends (Recent vs Career)
**Status**: ⚠️ Partial (we have both metrics but not the trend/comparison)  
**Priority**: High  
**Description**: Compare recent finish rate to career finish rate to identify fighters whose finishing ability is improving or declining.

**Implementation Notes**:
- We have: `finish_rate` (career) and `finish_rate_last_3/5/10` (recent)
- Need to add: trend features showing the difference
- Features to add:
  - `finish_rate_trend_3` = `finish_rate_last_3 - finish_rate`
  - `finish_rate_trend_5` = `finish_rate_last_5 - finish_rate`
  - `finish_rate_trend_10` = `finish_rate_last_10 - finish_rate`
  - `improving_finisher` (binary: recent > career by threshold)
  - `declining_finisher` (binary: recent < career by threshold)

**Code Location**: `features/fighter_features.py` - Add to `_extract_fight_history_features()` or create new method

---

### 3. Pace Differential (Volume Fighters vs Defensive)
**Status**: ⚠️ Partial (we have striking output diff but not pace-specific features)  
**Priority**: Medium-High  
**Description**: Compare fighters' pace/volume vs. defensive style. High-volume strikers vs. defensive counter-strikers create different fight dynamics.

**Implementation Notes**:
- We have: `striking_output_diff` (volume difference)
- Need to add: pace classification and matchup features
- Features to add:
  - `f1_pace_style` (high_volume, moderate, defensive) - based on strikes landed vs absorbed ratio
  - `f2_pace_style` (high_volume, moderate, defensive)
  - `pace_matchup` (volume_vs_volume, volume_vs_defensive, defensive_vs_defensive)
  - `pace_differential` (strikes_landed_per_min - strikes_absorbed_per_min, showing net activity)
  - `volume_advantage` (who throws more)

**Code Location**: `features/matchup_features.py` - Add to `_calculate_style_matchup()` or new method

---

### 4. Days Since Last Fight (Activity Level)
**Status**: ❌ Not Implemented  
**Priority**: High  
**Description**: Track how long since a fighter's last fight. Too long = ring rust, too short = insufficient recovery.

**Implementation Notes**:
- We have: `fights_in_last_year` (approximate) but not exact days
- Need to calculate: days between fight date and `as_of_date`
- Features to add:
  - `days_since_last_fight`
  - `days_since_last_fight_category` (fresh: <90, normal: 90-180, rusty: >180, very_rusty: >365)
  - `activity_level` (active: <120 days avg, normal: 120-200, inactive: >200)
  - `recovery_time` (for fighters with multiple recent fights, avg days between)

**Code Location**: `features/fighter_features.py` - Add to `_extract_momentum_features()` or new method

**Data Requirements**: 
- Need to properly parse `event_date` from fight history
- Calculate date differences using `as_of_date` parameter

---

## Tier 3 (Nice to Have) - Missing Features

### 5. Chin Durability Score
**Status**: ❌ Not Implemented  
**Priority**: Medium  
**Description**: Measure a fighter's ability to take damage without being finished. Combines KO/TKO losses with strikes absorbed.

**Implementation Notes**:
- Calculate from: KO/TKO losses, strikes absorbed per minute, knockdowns taken
- Features to add:
  - `chin_durability_score` (lower KO rate + higher strikes absorbed before KO = better chin)
  - `ko_resistance` (1 - ko_loss_rate, adjusted for career length)
  - `strikes_absorbed_before_ko` (average strikes absorbed in fights that ended in KO/TKO)
  - `knockdown_rate` (knockdowns per fight)

**Code Location**: `features/fighter_features.py` - New method `_extract_durability_features()`

**Data Requirements**:
- Need knockdown data (may be in FightStats or need to parse from fight details)
- KO/TKO loss tracking (we have this)

---

### 6. Age Trajectory (Performance Decline Rate)
**Status**: ❌ Not Implemented  
**Priority**: Medium  
**Description**: Track how a fighter's performance changes with age. Some fighters decline faster than others.

**Implementation Notes**:
- Calculate: win rate by age bracket, performance trend over time
- Features to add:
  - `age_performance_trend` (win rate in last 5 fights vs career, adjusted for age)
  - `age_decline_indicator` (negative if performance dropping with age)
  - `peak_age_performance` (best win rate age range)
  - `current_age_vs_peak` (how far past peak age)
  - `age_risk_factor` (higher for older fighters with declining performance)

**Code Location**: `features/fighter_features.py` - New method `_extract_age_trajectory_features()`

**Data Requirements**:
- Need to track age at time of each fight (calculate from date_of_birth and event_date)
- Performance metrics by age bracket

---

### 7. Camp Changes
**Status**: ❌ Not Implemented  
**Priority**: Low (requires external data)  
**Description**: Track when fighters change training camps. Some camp changes lead to improvements, others to declines.

**Implementation Notes**:
- Requires: external data source or manual tracking
- Features to add:
  - `recent_camp_change` (binary: changed camps in last year)
  - `camp_change_count` (number of camp changes in career)
  - `camp_change_impact` (performance before vs after camp change)

**Code Location**: Would need new data source or manual annotation

**Data Requirements**: 
- External data source (news, interviews, or manual tracking)
- Not easily scrapable from UFC stats

---

## Additional Valuable Features (Not in Original List)

### 8. Weight Class Consistency
**Status**: ❌ Not Implemented  
**Priority**: Medium  
**Description**: Track if fighters consistently fight in the same weight class or move around. Moving up/down can affect performance.

**Features to add**:
- `weight_class_consistency` (% of fights in primary weight class)
- `recent_weight_class_change` (changed weight class in last 3 fights)
- `weight_class_moves_up` (moving up in weight - binary)
- `weight_class_moves_down` (moving down in weight - binary)
- `weight_class_advantage` (size advantage in current matchup)

**Code Location**: `features/fighter_features.py` - Add to fight history analysis

---

### 9. Title Fight Experience & Performance
**Status**: ⚠️ Partial (we have `title_fight_experience` count but not performance metrics)  
**Priority**: Medium  
**Description**: Track performance specifically in title fights. Some fighters perform better under pressure.

**Features to add**:
- `title_fight_win_rate` (win rate in title fights specifically)
- `title_fight_experience` (already have count, but add performance)
- `title_fight_performance_diff` (title fight win rate vs overall win rate)
- `championship_round_experience` (fights that went 4+ rounds)

**Code Location**: `features/fighter_features.py` - Enhance `_extract_fight_history_features()`

---

### 10. Method-Specific Performance
**Status**: ⚠️ Partial (we have method rates but not matchup-specific)  
**Priority**: Medium  
**Description**: Track how fighters perform in different fight outcomes (KO, submission, decision).

**Features to add**:
- `ko_win_rate` (win rate when fight ends in KO/TKO)
- `submission_win_rate` (win rate when fight ends in submission)
- `decision_win_rate` (win rate in decisions)
- `method_preference_matchup` (both prefer same method, different methods)

**Code Location**: `features/matchup_features.py` - Add to style matchup

---

### 11. Control Time & Grappling Dominance
**Status**: ❌ Not Implemented  
**Priority**: Medium  
**Description**: Track control time and ground dominance. Important for grapplers.

**Features to add**:
- `avg_control_time_per_fight` (from fight stats)
- `control_time_advantage` (F1 control time - F2 control time)
- `ground_strike_rate` (strikes from ground position)
- `grappling_dominance_score` (control time + takedowns + ground strikes)

**Code Location**: `features/fighter_features.py` - Would need to parse from FightStats JSON

**Data Requirements**: 
- Parse `control_time` from `fighter_1_totals` / `fighter_2_totals` in FightStats
- Parse ground strikes from `significant_strikes` JSON

---

### 12. Significant Strike Accuracy by Position
**Status**: ❌ Not Implemented  
**Priority**: Low-Medium  
**Description**: Track accuracy in different positions (distance, clinch, ground). Shows versatility.

**Features to add**:
- `distance_striking_accuracy` (from significant_strikes JSON)
- `clinch_striking_accuracy`
- `ground_striking_accuracy`
- `striking_versatility_score` (ability to strike effectively from all positions)

**Code Location**: `features/fighter_features.py` - Parse from FightStats JSON

**Data Requirements**: 
- Parse from `significant_strikes` JSON in FightStats
- Calculate accuracy from "X of Y" format

---

### 13. Opponent Strength Over Time
**Status**: ❌ Not Implemented  
**Priority**: Medium  
**Description**: Track if fighters are facing tougher or easier competition over time.

**Features to add**:
- `opponent_strength_trend` (average opponent win rate in recent fights vs career)
- `strength_of_schedule` (average opponent quality)
- `toughest_opponent_win_rate` (win rate against top 25% of opponents by win rate)

**Code Location**: `features/fighter_features.py` - New method

---

### 14. Comeback Ability
**Status**: ❌ Not Implemented  
**Priority**: Low-Medium  
**Description**: Track ability to win after losing first round or being behind.

**Features to add**:
- `comeback_wins` (wins after losing first round - would need round-by-round data)
- `comeback_rate` (comeback wins / total wins)
- `resilience_score` (ability to recover from adversity)

**Code Location**: Would need round-by-round scoring data

**Data Requirements**: 
- Round-by-round scoring (not easily available from current data)
- Could approximate from fight outcomes and round finished

---

### 15. Fight Location & Travel
**Status**: ❌ Not Implemented  
**Priority**: Low  
**Description**: Track if fighters perform better at home, with travel, etc.

**Features to add**:
- `home_country_win_rate` (if we can determine fighter nationality)
- `travel_distance` (distance from home to fight location)
- `time_zone_change` (if significant)

**Code Location**: Would need location data

**Data Requirements**: 
- Fighter nationality/home location
- Event location data (we have this)
- Calculate distances/time zones

---

## Implementation Priority Summary

### High Priority (Implement Soon):
1. **Days Since Last Fight** - Easy to implement, high value
2. **Finish Rate Trends** - Simple calculation, high value
3. **Competition Quality** - High value, may need data source

### Medium Priority:
4. **Pace Differential** - Good value, moderate complexity
5. **Chin Durability Score** - Good value, need knockdown data
6. **Age Trajectory** - Good value, moderate complexity
7. **Weight Class Consistency** - Easy, good value
8. **Title Fight Performance** - Easy enhancement
9. **Control Time & Grappling** - Need to parse JSON data

### Lower Priority:
10. **Method-Specific Performance** - Nice to have
11. **Striking Accuracy by Position** - Need to parse JSON
12. **Opponent Strength Over Time** - Moderate complexity
13. **Comeback Ability** - Limited data availability
14. **Camp Changes** - Requires external data
15. **Fight Location & Travel** - Requires additional data

---

## Notes

- Features marked with ⚠️ are partially implemented and need enhancement
- Features marked with ❌ are not implemented at all
- Data requirements indicate what additional data sources or parsing is needed
- Code locations suggest where new features should be added

