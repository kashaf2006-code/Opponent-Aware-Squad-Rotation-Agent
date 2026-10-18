# OACSRA — Formula Sheet

## 1. Purpose

OACSRA (Opponent-Aware Cricket Squad Rotation Agent) helps a coach select a Playing XI and manage player rotation across upcoming ODI and T20 fixtures. The formulas below support performance evaluation, workload estimation, rest calculation, and rotation decisions.

**Dataset:** `data/processed/limited_overs_performance.csv`

## 2. Player Performance

### 2.1 Batting Score

Strike rate:

\[
SR=\frac{\text{Runs}}{\text{Balls Faced}}\times100
\]

Normalized runs:

\[
R_s=\min\left(\frac{\text{Runs}}{\text{Run Benchmark}},1\right)\times100
\]

Normalized strike rate:

\[
SR_s=\min\left(\frac{SR}{\text{SR Benchmark}},1\right)\times100
\]

Base batting score:

\[
BP=0.60R_s+0.40SR_s
\]

| Format | Run Benchmark | SR Benchmark |
|---|---:|---:|
| ODI | 64 | 101.71 |
| T20 | 42 | 146.51 |

The benchmarks are project-specific reference values, not universal cricket standards. Scores are capped at 100. The final batting score is the base score shown above; no small-sample reliability adjustment is applied.

### 2.2 Bowling Score

Economy rate:

\[
ER=\frac{\text{Runs Conceded}\times6}{\text{Balls Bowled}}
\]

Normalized wickets:

\[
WK_s=\min\left(\frac{\text{Wickets}}{\text{Wicket Benchmark}},1\right)\times100
\]

Normalized economy:

\[
ER_s=\min\left(\frac{\text{Economy Benchmark}}{ER},1\right)\times100
\]

Bowling score:

\[
BL=0.60WK_s+0.40ER_s
\]

The project-specific wicket benchmark is 2 wickets per bowling appearance. Economy benchmarks are 5.75 runs per over for T20 and 4.55 for ODI. If the economy rate is zero, its normalized score is 100. Scores are capped at 100. Bowling records with missing values or no balls bowled do not produce a score; a player who did not bowl is not treated as having a zero-performance bowling record.

### 2.3 Role-Based Performance

| Role | Performance Score |
|---|---|
| Batter | Batting score |
| Wicketkeeper | Batting score |
| Bowler | Bowling score |
| All-rounder | Average of available batting and bowling scores |

For an all-rounder:

\[
PS=\frac{BP+BL}{2}
\]

Average only the scores supported by actual batting or bowling opportunities. Missing opportunities must not automatically count as zero.

## 3. Recent Workload

Use up to the five most recent appearances in each format, sorted newest to oldest.

| Appearance | Recency Weight |
|---|---:|
| Most recent | 35% |
| Second | 25% |
| Third | 20% |
| Fourth | 12% |
| Fifth | 8% |

Renormalize the weights if fewer than five appearances are available.

### 3.1 Normalize Workload

\[
B_j=\min\left(\frac{\text{Balls Faced}_j}{B_{\text{ref}}},1\right)\times100
\]

\[
L_j=\min\left(\frac{\text{Balls Bowled}_j}{L_{\text{ref}}},1\right)\times100
\]

| Format | Batting Reference | Bowling Reference |
|---|---:|---:|
| ODI | 36 balls | 53 balls |
| T20 | 16 balls | 24 balls |

Calculate recency-weighted components:

\[
B=\sum_{j=1}^{n}\alpha_jB_j
\]

\[
L=\sum_{j=1}^{n}\alpha_jL_j
\]

### 3.2 Role-Based Workload

| Role | Workload Formula |
|---|---|
| Batter | \(W=0.90B+0.10L\) |
| Wicketkeeper | \(W=0.90B+0.10L\) |
| Bowler | \(W=0.10B+0.90L\) |
| All-rounder | \(W=0.50B+0.50L\) |

Workload estimates recent activity; they do not medically predict fatigue or injury. The participation component is omitted because reliable non-selection and rest records are unavailable.

## 4. Rest Between Matches

\[
D=\text{Upcoming Match Date}-\text{Previous Appearance Date}
\]

Optional normalized rest score:

\[
R=\min\left(\frac{D}{D_{\text{ref}}},1\right)\times100
\]

The reference interval \(D_{\text{ref}}\) has not been finalized. Rest days and workload are related but distinct indicators.

## 5. Match Priority and Rotation

The current candidate decision score is:

\[
S=w_pPS+w_w(100-W)
\]

| Match Priority | Performance Weight | Workload Weight |
|---|---:|---:|
| 1 | 50% | 50% |
| 2 | 60% | 40% |
| 3 | 70% | 30% |
| 4 | 80% | 20% |
| 5 | 90% | 10% |

Priority 5 represents the most important match. These weights are provisional and require comparison on representative players.

The optimizer must also enforce team constraints:

- Select exactly 11 players.
- Include at least one wicketkeeper.
- Meet the configured minimum batting and bowling coverage.
- Exclude unavailable players.
- Respect coach-approved changes and earlier approved selections.

The score supports the optimizer; it does not independently determine the Playing XI. Player roles, availability, and team constraints must be enforced separately.

## 6. Validation Status

| Component | Status |
|---|---|
| Batting score implementation | Implemented; automated checks passed |
| Batting benchmarks | Selected for testing |
| Small-sample adjustment | Removed; not part of the final batting formula |
| Bowling formula and benchmarks | Formula defined; implementation/configuration verification pending |
| Workload formula | Defined; full sample verification pending |
| Rest calculation | Basic formula defined; reference interval pending |
| Match-priority weights | Proposed; comparative testing pending |
| Playing XI and multi-match rotation | End-to-end validation pending |

**Important:** Passing code checks confirms that the implementation follows specified rules; it does not prove that a formula is statistically optimal. All reference values and weights should be documented and tested before final integration.