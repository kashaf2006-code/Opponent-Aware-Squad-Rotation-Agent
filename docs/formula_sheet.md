
# Workload Calculation Formula — OACSRA

## 1. Purpose
The workload score estimates a player's recent workload to support squad rotation decisions.

## 2. Variables
- **P:** Participation workload score (0–100).
- **B:** Batting workload score (0–100).
- **L:** Bowling workload score (0–100).

## 3. Role-Based Weights

| Player Role | Participation | Batting | Bowling |
|---|---:|---:|---:|
| Batter | 10% | 80% | 10% |
| Bowler | 10% | 10% | 80% |
| All-rounder | 10% | 45% | 45% |

## 4. Equations

**Batter:**
W = 0.10P + 0.80B + 0.10L

**Bowler:**
W = 0.10P + 0.10B + 0.80L

**All-rounder:**
W = 0.10P + 0.45B + 0.45L

## 5. Interpretation
The final workload score ranges from 0 to 100. Higher scores indicate greater recent workload and can contribute to rotation recommendations.

## 6. Validation Status
Weights finalized for the initial rule-based design. Component normalization and calculated scores must be validated using player performance data before integration.

A. Batting performance score
First, calculate strike rate:
\[
SR=\frac{\text{Runs}}{\text{Balls Faced}}\times100
\]

Then normalize runs and strike rate to scores from 0–100:
\[
R_s=\min\left(\frac{\text{Runs}}{\text{Run Benchmark}},1\right)\times100
\]

\[
SR_s=\min\left(\frac{SR}{\text{Target Strike Rate}},1\right)\times100
\]

Combine them:
\[
\boxed{BP=0.60R_s+0.40SR_s}
\]

This gives more weight to actual runs scored than scoring speed.
B. Bowling performance score
Calculate economy rate:
\[
ER=\frac{\text{Runs Conceded}}{\text{Balls Bowled}/6}
\]

Normalize wickets and economy:
\[
WK_s=\min\left(\frac{\text{Wickets}}{\text{Wicket Benchmark}},1\right)\times100
\]

\[
ER_s=\min\left(\frac{\text{Target Economy}}{ER},1\right)\times100
\]

Then combine them:
\[
\boxed{BL=0.60WK_s+0.40ER_s}
\]

This rewards taking wickets while also considering runs conceded.
2. How should we combine batting and bowling?
The coach-confirmed role determines which score is relevant.
Role	Performance score
Batter	Batting performance
Wicketkeeper	Batting performance
Bowler	Bowling performance
All-rounder	Average of batting and bowling performance
For all-rounders, we must handle cases where the player has no batting or bowling opportunity in a match rather than treating missing activity as poor performance

Rest Between Matches — OACSRA
1. Calculate rest days
\[
D_i=\text{Upcoming Match Date}-\text{Previous Appearance Date}
\]

This gives the number of calendar days between a player's previous appearance and the upcoming match. We should calculate it using actual dates, not simply count the number of intervening fixtures.
2. Convert it into a rest score
We could normalize the rest interval to a score from 0–100:
\[
R_i=\min\left(\frac{D_i}{D_{\text{ref}}},1\right)\times100
\]

Here, \(D_{\text{ref}}\) is a chosen reference interval. A higher score means more time between appearances.
However, the reference interval needs to be selected and tested before we finalize this formula.