# Customer Support Resolution Agent (Test Lab)

This exercise builds a deterministic customer support agent you can run without a real database.

The agent handles high-ambiguity support requests in three domains:

- Returns
- Billing disputes
- Account issues

It uses MCP-style tool contracts:

- `get_customer`
- `lookup_order`
- `process_refund`
- `escalate_to_human`

## Files

- `support_agent.py`: Agent orchestration and in-memory mock backend
- `support_repository.py`: SQLite mock DB with seed data and tool-call history logs
- `mcp_mock_layer.py`: MCP-like JSON-RPC tool server (`tools/list`, `tools/call`)
- `support_agent_mcp.py`: Agent orchestration that calls tools through MCP protocol messages
- `chat_cli.py`: Interactive chat shell with verbose trace and failure injection controls
- `mock_data.py`: Synthetic scenario fixtures
- `evaluate_agent.py`: FCR and expected-outcome evaluator
- `test_support_agent.py`: Lightweight deterministic tests
- `test_support_mcp.py`: MCP/data-layer integration tests

## Why this lab uses mock data

You can test orchestration with tool stubs only, but realistic validation of first-contact resolution
requires representative customer/order fixtures. This lab provides both:

- In-memory backend with deterministic records (no DB dependency)
- Synthetic scenarios to measure reliability and escalation behavior

## Run

From this folder:

```powershell
python support_agent.py
python evaluate_agent.py
python evaluate_agent.py --mode target
python test_support_agent.py
python test_support_mcp.py
python chat_cli.py --reset-db --verbose
```

## MCP + DB + Chat Buildout

This lab now includes the three runtime layers needed for realistic end-to-end practice:

- MCP tool layer:
	- Tool calls run through JSON-RPC-shaped requests (`tools/list`, `tools/call`)
	- You can inject failures per tool to simulate broken integrations
- Data layer:
	- SQLite mock DB for state, idempotent refund behavior, and historical tool logs
	- Reseed with `--reset-db` for deterministic test runs
- Chat interface:
	- Interactive CLI loop that sends user messages to the MCP-backed orchestrator
	- Shows outcomes and each tool call result

## Learning Mode: Break and Fix Tool Calls

Launch:

```powershell
python chat_cli.py --reset-db --verbose
```

Useful commands:

- `/help`
- `/tools`
- `/actor agent|manager`
- `/verbose on|off`
- `/fail <tool> <category> <once|always> <retryable:true|false> [description]`
- `/fix <tool|all>`
- `/logs [n]`
- `/exit`

Examples:

```text
/fail lookup_order transient always false Injected outage for testing
Return customer C1001 order O5001
/fix lookup_order
Return customer C1001 order O5001
/logs 20
```

This allows you to intentionally break a tool, observe escalation/recovery behavior, then clear the fault and validate normal execution.

## Evaluation Notes

`evaluate_agent.py` reports:

- Total scenarios
- FCR (first-contact resolution)
- Expected-outcome accuracy
- Whether FCR meets the 80% target

Scenario packs:

- `baseline`: realistic mixed workload with frequent escalation-worthy cases
- `target`: tuned fixture mix that reaches the 80% FCR goal for benchmark verification

## Design Highlights

- Policy-aware returns:
	- 30-day return window
	- Delivery-state checks
	- Ownership/fraud mismatch escalation
- Billing disputes:
	- Auto-refund for small disputes
	- Escalation for larger or blocked disputes
- Account reliability:
	- Locked/unverified accounts escalate for secure handling
	- Active accounts resolve in first contact when safe

## Next Extension Ideas

- Add richer intent parsing and multi-intent decomposition
- Add retry/backoff simulation for transient tool failures
- Add scenario packs that intentionally hit 80%+ to compare against the baseline

