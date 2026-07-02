"""Interactive CLI chat for the MCP-backed support agent lab.

Commands:
  /help
  /tools
  /actor agent|manager
  /verbose on|off
  /fail <tool> <category> <once|always> <retryable:true|false> [description]
  /fix <tool|all>
  /logs [n]
  /exit
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from support_agent_mcp import build_runtime


def print_response(out: Dict[str, Any]) -> None:
    print("=" * 90)
    print(f"Outcome: {out['outcome']}")
    print(f"Message: {out['message']}")
    print("Tool Results:")
    if not out["tool_results"]:
        print("  (none)")
        return

    for idx, item in enumerate(out["tool_results"], start=1):
        if item.get("ok"):
            print(f"  {idx}. OK {item.get('tool')}: {item.get('data')}")
        else:
            print(
                f"  {idx}. FAIL category={item.get('errorCategory')} "
                f"retryable={item.get('isRetryable')} msg={item.get('description')}"
            )


def parse_bool(text: str) -> bool:
    t = text.strip().lower()
    if t in {"true", "1", "yes", "y", "on"}:
        return True
    if t in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError("Expected boolean value (true|false).")


def repl(db_path: str, reset_db: bool, verbose: bool) -> None:
    def _trace(message: str) -> None:
        print(f"[trace] {message}")

    agent, server, repo = build_runtime(
        db_path=db_path,
        reset_db=reset_db,
        verbose=verbose,
        trace_sink=_trace,
    )

    actor_role = "agent"

    print("Support Agent MCP Chat Lab")
    print("Type /help for commands. Type /exit to quit.")

    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split()
            cmd = parts[0].lower()

            if cmd == "/exit":
                print("Exiting.")
                break

            if cmd == "/help":
                print(__doc__)
                continue

            if cmd == "/tools":
                response = server.handle_mcp_request({"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"})
                for t in response.get("result", []):
                    print(f"- {t['name']}: {t['description']}")
                continue

            if cmd == "/actor":
                if len(parts) != 2 or parts[1] not in {"agent", "manager"}:
                    print("Usage: /actor agent|manager")
                    continue
                actor_role = parts[1]
                print(f"actor role set to {actor_role}")
                continue

            if cmd == "/verbose":
                if len(parts) != 2 or parts[1] not in {"on", "off"}:
                    print("Usage: /verbose on|off")
                    continue
                new_value = parts[1] == "on"
                agent.set_verbose(new_value)
                print(f"verbose set to {new_value}")
                continue

            if cmd == "/fail":
                if len(parts) < 6:
                    print("Usage: /fail <tool> <category> <once|always> <retryable:true|false> [description]")
                    continue
                tool_name = parts[1]
                category = parts[2]
                mode = parts[3]
                retryable = parse_bool(parts[4])
                description = " ".join(parts[5:]) or "Injected failure"
                server.inject_failure(
                    tool_name=tool_name,
                    error_category=category,
                    is_retryable=retryable,
                    description=description,
                    mode=mode,
                )
                print(f"failure injected for {tool_name}")
                continue

            if cmd == "/fix":
                if len(parts) != 2:
                    print("Usage: /fix <tool|all>")
                    continue
                target = parts[1]
                if target == "all":
                    server.clear_all_failures()
                    print("all injected failures cleared")
                else:
                    server.clear_failure(target)
                    print(f"failure cleared for {target}")
                continue

            if cmd == "/logs":
                limit = 15
                if len(parts) == 2:
                    limit = int(parts[1])
                rows = repo.recent_tool_logs(limit=limit)
                for row in rows:
                    print(
                        f"#{row['id']} {row['created_at']} tool={row['tool_name']} "
                        f"ok={row['ok']} forced={row['forced_failure']} "
                        f"err={row['error_category']} latency={row['latency_ms']}ms args={row['args']}"
                    )
                if not rows:
                    print("No tool logs found.")
                continue

            print("Unknown command. Type /help.")
            continue

        out = agent.handle_request(user_input, actor_role=actor_role)
        print_response(out)

    repo.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MCP-backed support chat CLI.")
    parser.add_argument("--db-path", default="support_mock.db", help="Path to SQLite mock DB.")
    parser.add_argument("--reset-db", action="store_true", help="Recreate and reseed the database.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose MCP tool tracing.")
    args = parser.parse_args()

    repl(db_path=args.db_path, reset_db=args.reset_db, verbose=args.verbose)


if __name__ == "__main__":
    main()
