import sqlite3
import json

conn = sqlite3.connect("arsa.db")
c = conn.cursor()

tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])

# Check debate stage and debate_logs
for pid in [1, 2, 3]:
    print(f"\n=== Project {pid} Debate ===")
    logs = c.execute("SELECT id, hypothesis_id, proposal_a, proposal_b, winner_proposal, rationale FROM debate_logs WHERE project_id=?", (pid,)).fetchall()
    print(f"Debate logs count: {len(logs)}")
    for log in logs:
        print(f"  ID {log[0]}: Hypo {log[1]} | Winner: {log[4]}")
        print(f"    Prop A: {log[2][:100]}...")
        print(f"    Prop B: {log[3][:100]}...")
        print(f"    Rationale: {log[5][:120]}...")
    
    stage = c.execute("SELECT status, output_data FROM research_stages WHERE project_id=? AND stage_name='debate'", (pid,)).fetchone()
    if stage:
        print(f"  Stage status: {stage[0]}")
        if stage[1]:
            try:
                data = json.loads(stage[1])
                print(f"  Stage output keys: {list(data.keys())}")
                print(f"  Stage Winner: {data.get('winner_proposal')}")
                print(f"  Prop C: {data.get('proposal_c', '')[:100]}...")
                print(f"  Debate rounds: {len(data.get('debate_rounds', []))}")
            except Exception as e:
                print("  Stage output json error:", e)

