"""Minimal MCP-like tool server used for support-agent training."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolError(Exception):
    error_category: str
    is_retryable: bool
    description: str

    def to_payload(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "errorCategory": self.error_category,
            "isRetryable": self.is_retryable,
            "description": self.description,
        }


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, str]
    handler: Callable[..., Dict[str, Any]]


class MCPMockServer:
    """Tiny JSON-RPC shaped tool server for local labs."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._tools: Dict[str, ToolSpec] = {}
        self._failures: Dict[str, Dict[str, Any]] = {}
        self._event_sink: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_event_sink(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._event_sink = callback

    def register_tool(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def list_tools(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for spec in self._tools.values():
            out.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "inputSchema": spec.input_schema,
                }
            )
        return out

    def inject_failure(
        self,
        tool_name: str,
        error_category: str,
        is_retryable: bool,
        description: str,
        mode: str = "once",
    ) -> None:
        if mode not in {"once", "always"}:
            raise ValueError("mode must be once or always")
        self._failures[tool_name] = {
            "mode": mode,
            "error": ToolError(error_category, is_retryable, description),
        }

    def clear_failure(self, tool_name: str) -> None:
        self._failures.pop(tool_name, None)

    def clear_all_failures(self) -> None:
        self._failures.clear()

    def _emit(self, event: Dict[str, Any]) -> None:
        if self._event_sink is not None:
            self._event_sink(event)

    def _call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        spec = self._tools.get(tool_name)
        start = perf_counter()
        forced_failure = False

        if spec is None:
            elapsed = int((perf_counter() - start) * 1000)
            out = {
                "ok": False,
                "errorCategory": "validation",
                "isRetryable": False,
                "description": f"Unknown tool '{tool_name}'.",
            }
            self._emit(
                {
                    "tool": tool_name,
                    "args": args,
                    "ok": False,
                    "forced_failure": False,
                    "error_category": out["errorCategory"],
                    "error_description": out["description"],
                    "latency_ms": elapsed,
                }
            )
            return out

        failure = self._failures.get(tool_name)
        if failure is not None:
            forced_failure = True
            err: ToolError = failure["error"]
            if failure["mode"] == "once":
                self._failures.pop(tool_name, None)

            elapsed = int((perf_counter() - start) * 1000)
            payload = err.to_payload()
            self._emit(
                {
                    "tool": tool_name,
                    "args": args,
                    "ok": False,
                    "forced_failure": True,
                    "error_category": payload["errorCategory"],
                    "error_description": payload["description"],
                    "latency_ms": elapsed,
                }
            )
            return payload

        try:
            data = spec.handler(**args)
            elapsed = int((perf_counter() - start) * 1000)
            out = {
                "ok": True,
                "tool": tool_name,
                "protocol": "mcp-mock-v1",
                "data": data,
            }
            self._emit(
                {
                    "tool": tool_name,
                    "args": args,
                    "ok": True,
                    "forced_failure": forced_failure,
                    "error_category": None,
                    "error_description": None,
                    "latency_ms": elapsed,
                }
            )
            return out
        except ToolError as err:
            elapsed = int((perf_counter() - start) * 1000)
            out = err.to_payload()
            self._emit(
                {
                    "tool": tool_name,
                    "args": args,
                    "ok": False,
                    "forced_failure": forced_failure,
                    "error_category": out["errorCategory"],
                    "error_description": out["description"],
                    "latency_ms": elapsed,
                }
            )
            return out
        except Exception as err:
            elapsed = int((perf_counter() - start) * 1000)
            out = {
                "ok": False,
                "errorCategory": "transient",
                "isRetryable": False,
                "description": f"Unhandled exception in tool '{tool_name}': {err}",
            }
            self._emit(
                {
                    "tool": tool_name,
                    "args": args,
                    "ok": False,
                    "forced_failure": forced_failure,
                    "error_category": out["errorCategory"],
                    "error_description": out["description"],
                    "latency_ms": elapsed,
                }
            )
            return out

    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")
        req_id = request.get("id")

        if method == "tools/list":
            result = self.list_tools()
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        if method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            result = self._call_tool(tool_name, args)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }
