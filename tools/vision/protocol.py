import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class MCPRequest:
    "JSON-RPC request structure."
    method: str
    params: dict
    id: int

    def to_json(self) -> str:
        return json.dumps({
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
            "id": self.id
        })

@dataclass
class MCPResponse:
    "JSON-RPC response structure."
    id: int
    result: Optional[dict] = None
    error: Optional[dict] = None

    @classmethod
    def from_json(cls, data: str) -> "MCPResponse":
        parsed = json.loads(data)
        return cls(
            id=parsed.get("id"),
            result=parsed.get("result"),
            error=parsed.get("error")
        )

    @property
    def success(self) -> bool:
        return self.error is None

class MCPProtocol:
    "MCP protocol handler."

    def __init__(self):
        self._request_id = 0
        self._protocol_logger = logging.getLogger("mcp.protocol")

    def create_request(self, method: str, params: dict) -> MCPRequest:
        "Create a new request with auto-incrementing ID."
        self._request_id += 1
        request = MCPRequest(method=method, params=params, id=self._request_id)
        self._protocol_logger.debug(f">>> {request.to_json()}")
        return request

    def parse_response(self, data: str) -> MCPResponse:
        "Parse a JSON-RPC response."
        self._protocol_logger.debug(f"<<< {data.strip()}")
        return MCPResponse.from_json(data)

    def create_notification(self, method: str, params: dict = None) -> str:
        "Create a notification (no response expected)."
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        msg = json.dumps(notification)
        self._protocol_logger.debug(f">>> {msg}")
        return msg
