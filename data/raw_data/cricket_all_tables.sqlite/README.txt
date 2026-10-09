Cricket ball-by-ball (Cricsheet)
https://api.tigzig.com/cricket/v1

LICENCE
Open Data Commons Attribution License 1.0 (ODC-BY)
https://opendatacommons.org/licenses/by/1-0/

SOURCE
Cricsheet (cricsheet.org). The tables here are built from the Cricsheet data and refreshed twice daily.

COVERAGE
Cricsheet withholds some matches, including those involving the Afghanistan men's team and the Afghanistan Premier League (cricsheet.org/withheld-matches). That exclusion is inherited here, so this is not a complete record of the competitions it covers. Check Cricsheet's page for the current list.

NO WARRANTY
Provided as is. No guarantee of accuracy, completeness or availability, and no support commitment.

TigZig is not affiliated with or endorsed by Cricsheet. Cricsheet is credited as the source of the underlying match data under the terms of the ODC-BY 1.0 licence.

Contact: amar@harolikar.com


WHAT IS IN THIS ARCHIVE
  ball_by_ball                  5,047,757 rows
  match_info                       11,078 rows
  match_players                   293,456 rows
  people                           18,554 rows
  ball_by_ball_t20_men            802,320 rows
  ball_by_ball_t20_women          493,730 rows
  ball_by_ball_odi_men          1,366,311 rows
  ball_by_ball_odi_women          320,238 rows
  ball_by_ball_test_men         1,722,675 rows
  ball_by_ball_test_women          46,751 rows
  ball_by_ball_ipl                295,732 rows


The ball_by_ball_* files are exact splits of ball_by_ball by format and
gender - every delivery is in the full file and in exactly one split.
Download the full file or the split you need; they hold the same rows.

The DuckDB archive holds the physical tables and, as views, the same
split names db-mcp serves. The SQLite archive holds the physical tables
only - create any views you need from ball_by_ball.

Generated 2026-10-06T06:48:36Z. Refreshed twice daily.

OTHER FORMATS
  The format you ask for IS the file extension you receive - there are no
  aliases and nothing is inferred. Per table:
    .../cricket/v1/download/{table}?format=parquet
    .../cricket/v1/download/{table}?format=csv.gz
    .../cricket/v1/download/{table}?format=csv.zip
  Everything in one file:
    .../cricket/v1/download/all?format=duckdb.zip   (or duckdb.gz)
    .../cricket/v1/download/all?format=sqlite.zip   (or sqlite.gz)
  Sizes and row counts for all of them:
    https://api.tigzig.com/cricket/v1/downloads/manifest
