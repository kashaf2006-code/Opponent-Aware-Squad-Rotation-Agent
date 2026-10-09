import sqlite3
import pandas as pd

def run_agent_decision_engine():
    # 1. Connect to the database
    db_path = "database/cricket_agent.db"
    conn = sqlite3.connect(db_path)
    
    try:
        players_df = pd.read_sql("SELECT * FROM players", conn)
    except Exception as e:
        print(f"Error loading players table: {e}")
        conn.close()
        return

    # 2. Apply fallback scores if columns are missing
    if 'performance_score' not in players_df.columns:
        players_df['performance_score'] = 50.0  
    if 'workload_score' not in players_df.columns:
        players_df['workload_score'] = 20.0  

    # 3. Calculate net scores
    players_df['net_score'] = players_df['performance_score'] - (0.5 * players_df['workload_score'])
    ranked_players = players_df.sort_values(by='net_score', ascending=False).drop_duplicates(subset=['person_name']).reset_index(drop=True)

    # 4. Agent Selection Logic (Top 11 play, rest are rotated)
    playing_xi_count = min(11, len(ranked_players))
    
    recommended_xi = ranked_players.head(playing_xi_count).copy()
    recommended_xi['decision'] = 'PLAY'
    recommended_xi['reason'] = 'Optimal performance-to-workload balance.'

    # Players outside the top 11 get rotation/rest recommendations
    rotation_pool = ranked_players.iloc[playing_xi_count:].copy()
    if not rotation_pool.empty:
        rotation_pool['decision'] = 'REST'
        rotation_pool['reason'] = 'High workload relative to current performance score.'
    
    # Combine results
    final_report = pd.concat([recommended_xi, rotation_pool])

    print("\n--- OACSRA Agent Decision Report ---")
    for idx, row in final_report.head(15).iterrows():
        name = row.get('person_name', f"Player_{idx}")
        decision = row['decision']
        reason = row['reason']
        print(f"[{decision}] {name} -> Reason: {reason}")

    # 5. Save recommendations back into SQLite database table
    final_report[['person_name', 'team', 'decision', 'reason', 'net_score']].to_sql(
        'recommendations', conn, if_exists='replace', index=False
    )
    print("\nSuccessfully saved agent recommendations to SQLite database ('recommendations' table).")

    conn.close()
    return final_report

if __name__ == "__main__":
    run_agent_decision_engine()