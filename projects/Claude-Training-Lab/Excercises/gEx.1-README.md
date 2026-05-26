# gEx.1 - Multi-Tool Agent with Escalation Logic

This generated exercise implements all requested steps for Exercise 1 under the Excercises folder.

## Files

- gEx.1-multi_tool_agent.py
- gEx.1-tests.py
- gEx.1-README.md

## Exercise Coverage

1. Define 3-4 MCP tools with detailed descriptions
- Implemented 4 tools with explicit purpose, expected input schema, and boundary conditions:
  - get_account_balance
  - get_invoice_balance
  - submit_refund
  - create_support_ticket
- Two intentionally similar tools are clearly differentiated:
  - get_account_balance (account ledger level)
  - get_invoice_balance (customer + month billing-cycle level)

2. Implement an agentic loop with stop_reason handling
- The loop explicitly handles:
  - tool_use: execute the next tool calls and continue looping.
  - end_turn: synthesize and return the final response.
- See method: MultiToolAgent.run(...)

3. Add structured tool errors and behavior
- Errors include:
  - errorCategory: transient | validation | permission
  - isRetryable: true | false
  - description: human-readable text
- Behavior:
  - transient + retryable errors are automatically retried (up to max_retries)
  - validation/permission errors are returned to user-facing synthesis without retry

4. Add programmatic hook for business rule enforcement
- Method: intercept_tool_call(...)
- Business rule:
  - refund amount above escalation_threshold is blocked
  - request is redirected into escalation workflow
  - escalation creates support ticket with metadata

5. Test with multi-concern messages and unified synthesis
- Multi-concern decomposition is implemented in _plan_concerns(...)
- Unified synthesis is implemented in _synthesize(...)
- Tests include:
  - multi-concern with retry + escalation
  - permission business error
  - validation error

## How to Run

From the Excercises directory:

```powershell
python gEx.1-multi_tool_agent.py
python gEx.1-tests.py
```

## What to Study and Rebuild

1. Tool design clarity:
- Compare get_account_balance vs get_invoice_balance and note how boundary text reduces selection confusion.

2. Agent loop control:
- Follow stop_reason transitions to see why tool_use and end_turn are enough for this pattern.

3. Reliability pattern:
- Inspect execute_tool(...) retry logic for transient failures.

4. Governance pattern:
- Inspect intercept_tool_call(...) to understand how policy checks stay outside tool internals.

5. Multi-concern orchestration:
- Inspect _plan_concerns(...) and _synthesize(...) to see decomposition + recomposition.
