"""Run and print the M8 golden eval set."""

import sys
import time
import litellm

litellm._turn_on_debug()

from src.eval_runner import evaluate_ticket, load_golden_tickets, run_ticket


def main():
    tickets = load_golden_tickets()
    print(f"ShopSense Golden Eval -- {len(tickets)} tickets\n" + "=" * 72)
    results = []
    start = time.time()
    for ticket in tickets:
        t0 = time.time()
        try:
            result = run_ticket(ticket)
            failures = evaluate_ticket(ticket, result)
            status = "PASS" if not failures else "FAIL"
        except Exception as e:
            result, failures, status = None, [f"CRASHED: {type(e).__name__}: {e}"], "ERROR"
        elapsed = time.time() - t0
        results.append((ticket, status, failures, elapsed))
        marker = "PASS" if status == "PASS" else status
        outcome = "n/a" if not result else ("escalated" if result["values"].get("requires_human") else "auto-resolved")
        print(f"{marker:5} {ticket['ticket_id']:10} [{ticket['category']:28}] ({outcome}, {elapsed:.1f}s)")
        for failure in failures:
            print(f"     -> {failure}")
    passed = sum(1 for _, status, _, _ in results if status == "PASS")
    failed = sum(1 for _, status, _, _ in results if status == "FAIL")
    errored = sum(1 for _, status, _, _ in results if status == "ERROR")
    print("=" * 72)
    print(f"{passed}/{len(tickets)} passed, {failed} failed, {errored} errored -- total {time.time() - start:.1f}s")
    breaches = [failure for _, _, failures, _ in results for failure in failures if "guardrail" in failure]
    print(f"{len(breaches)} non-negotiable guardrail breaches")
    for breach in breaches:
        print(f"   - {breach}")
    sys.exit(0 if failed == 0 and errored == 0 else 1)


if __name__ == "__main__":
    main()
