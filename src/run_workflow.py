"""
Module 5 demo runner — run as two SEPARATE process invocations to prove
checkpointing survives a restart.

Usage:
    python -m src.run_workflow start <ticket_id> <channel> <customer_id> "<raw_text>"
    python -m src.run_workflow resume <thread_id> approve ["note"]
    python -m src.run_workflow resume <thread_id> reject ["note"]
"""

import sys
import json
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from src.langgraph_workflow import build_graph

DB_PATH = "shopsense_checkpoints.db"


def start(ticket_id, channel, customer_id, raw_text):
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": ticket_id}}
        result = graph.invoke(
            {
                "ticket_id": ticket_id,
                "channel": channel,
                "customer_id": customer_id,
                "raw_text": raw_text,
            },
            config=config,
        )

        if "__interrupt__" in result:
            print(f"\n⏸  PAUSED for human approval. thread_id={ticket_id}")
            print(json.dumps(result["__interrupt__"][0].value, indent=2, default=str))
            print(f"\nResume with:\n  python -m src.run_workflow resume {ticket_id} approve")
            print(f"  python -m src.run_workflow resume {ticket_id} reject\n")
        else:
            print(f"\n✅ DONE. final_status={result.get('final_status')}")
            print(f"notes: {result.get('resolution_notes')}\n")


def resume(thread_id, decision, note=""):
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(
            Command(resume={"approved": decision == "approve", "note": note}),
            config=config,
        )
        print(f"\n✅ DONE. final_status={result.get('final_status')}")
        print(f"notes: {result.get('resolution_notes')}\n")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "start":
        start(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "resume":
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        resume(sys.argv[2], sys.argv[3], note)
    else:
        print("Unknown command. Use 'start' or 'resume'.")