import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .protocol import MCPProtocol, MCPResponse

logger = logging.getLogger(__name__)

@dataclass
class VisionResult:
    "Result from a vision analysis call."
    success: bool
    content: str
    raw_response: dict
    error: Optional[str] = None

class MCPConnectionError(Exception):
    "Raised when MCP server connection fails."
    pass

class MCPVisionClient:
    """
    Direct MCP client for Z.AI vision server.
    Spawns the MCP server as a subprocess and communicates via JSON-RPC over stdio.
    """

    def __init__(self, api_key: str = None, mode: str = "ZAI"):
        self.api_key = api_key or os.environ.get("Z_AI_API_KEY") or os.environ.get("ZAI_API_KEY")
        self.mode = mode
        self.process: Optional[subprocess.Popen] = None
        self.protocol = MCPProtocol()
        self._initialized = False
        self._lock = asyncio.Lock()

        if not self.api_key:
            raise ValueError("Z_AI_API_KEY or ZAI_API_KEY required in environment")

    async def start(self, timeout: float = 30.0) -> None:
        "Spawn MCP server and complete initialization handshake."
        self._spawn_server()
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                await self._initialize()
                self._initialized = True
                logger.info("MCP Vision Client initialized")
                return
            except Exception as e:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise MCPConnectionError(f"Failed to initialize MCP server within {timeout}s: {e}")
                
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read().decode(errors='ignore') if self.process.stderr else ""
                    raise MCPConnectionError(f"MCP server process died during startup. Stderr: {stderr}")

                await asyncio.sleep(0.5)

    def _spawn_server(self) -> None:
        "Spawn the MCP server process."
        env = {**os.environ, "Z_AI_API_KEY": self.api_key, "Z_AI_MODE": self.mode}
        
        # In this environment, npx is on the path
        cmd = ["npx", "-y", "@z_ai/mcp-server@latest"]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, # Keep stderr separate for debugging
                env=env
            )
            logger.info(f"Spawned MCP server process (PID: {self.process.pid})")
        except OSError as e:
            raise MCPConnectionError(f"Failed to spawn MCP server: {e}")

    async def _initialize(self) -> None:
        "Complete MCP initialization handshake."
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "naval-gallery-classifier", "version": "0.1.0"}
        })

        if not response.success:
            raise MCPConnectionError(f"MCP initialization failed: {response.error}")

        await self._send_notification("notifications/initialized")

    async def _send_request(self, method: str, params: dict, timeout: float = 60.0) -> MCPResponse:
        "Send JSON-RPC request and wait for response."
        async with self._lock:
            request = self.protocol.create_request(method, params)
            request_line = request.to_json() + "\n"
            
            self.process.stdin.write(request_line.encode())
            self.process.stdin.flush()

            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout

            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise MCPConnectionError(f"Timeout waiting for response to {method}")

                try:
                    # Non-blocking read of stdout
                    response_line = await asyncio.wait_for(
                        loop.run_in_executor(None, self.process.stdout.readline),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    raise MCPConnectionError(f"Timeout waiting for response to {method}")

                if not response_line:
                    if self.process.poll() is not None:
                        stderr = self.process.stderr.read().decode(errors="ignore") if self.process.stderr else ""
                        raise MCPConnectionError(f"MCP server died: {stderr}")
                    raise MCPConnectionError("Empty response from MCP server")

                raw = response_line.decode(errors="ignore").strip()
                try:
                    parsed = json.loads(raw)
                    if parsed.get("id") == request.id:
                        return MCPResponse.from_json(raw)
                except json.JSONDecodeError:
                    continue

    async def _send_notification(self, method: str, params: dict = None) -> None:
        "Send JSON-RPC notification (no response expected)."
        notification = self.protocol.create_notification(method, params)
        self.process.stdin.write((notification + "\n").encode())
        self.process.stdin.flush()

    async def analyze_image(self, image_path: str, prompt: str, timeout: float = 120.0) -> VisionResult:
        "Analyze an image using Z.AI vision."
        if not self._initialized:
            raise RuntimeError("Client not initialized. Call start() first.")

        # Normalize path to absolute
        abs_path = str(Path(image_path).resolve()).replace("\\", "/")

        response = await self._send_request("tools/call", {
            "name": "analyze_image",
            "arguments": {
                "image_source": abs_path,
                "prompt": prompt
            }
        }, timeout=timeout)

        return self._parse_tool_response(response)

    def _parse_tool_response(self, response: MCPResponse) -> VisionResult:
        "Parse MCP tool response into VisionResult."
        if not response.success:
            return VisionResult(
                success=False,
                content="",
                raw_response={"error": response.error},
                error=response.error.get("message", "Unknown error") if response.error else "Unknown error"
            )

        result = response.result or {}
        content_list = result.get("content", [])
        is_error = bool(result.get("isError"))

        text_content = ""
        for item in content_list:
            if item.get("type") == "text":
                text_content += item.get("text", "")

        if is_error:
            return VisionResult(
                success=False,
                content="",
                raw_response={"result": result},
                error=text_content or "Tool call failed"
            )

        return VisionResult(success=True, content=text_content, raw_response={"result": result})

    async def close(self) -> None:
        "Shutdown MCP server."
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self._initialized = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
