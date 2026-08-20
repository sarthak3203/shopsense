"""
Module 5 demo runner — run as two SEPARATE process invocations to prove
checkpointing survives a restart.

M7 update: each invocation is wrapped in trace_ticket_session() AND uses
traced_invoke() (instead of calling graph.invoke() directly) so all node
spans for this ticket nest under ONE Langfuse trace per ticket, rather
than each node becoming its own separate root trace. flush_traces() is
called before exit since this is a short-lived CLI process (Langfuse
ingestion is batched/async).

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
from src.tracing import trace_ticket_session, flush_traces, traced_invoke

DB_PATH = "shopsense_checkpoints.db"


def start(ticket_id, channel, customer_id, raw_text):
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": ticket_id}}

        # issue_type isn't known yet (triage hasn't run), so tag as
        # "unknown" -- the individual node spans still carry full detail.
        with trace_ticket_session(customer_id, ticket_id, issue_type="unknown"):
            result = traced_invoke(
                graph,
                {
                    "ticket_id": ticket_id,
                    "channel": channel,
                    "customer_id": customer_id,
                    "raw_text": raw_text,
                },
                config,
            )
        flush_traces()

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

        # We don't have customer_id/issue_type without loading the
        # checkpoint state first; thread_id (== ticket_id) is enough to
        # correlate this resume's spans with the original trace's session
        # in the Langfuse UI via search.
        with trace_ticket_session(customer_id=thread_id, ticket_id=thread_id, issue_type="resume"):
            result = traced_invoke(
                graph,
                Command(resume={"approved": decision == "approve", "note": note}),
                config,
            )
        flush_traces()

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