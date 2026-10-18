from __future__ import annotations

import ipaddress
import os
import socket

import httpx
import pytest

# This must be set before importing application modules: api.main imports the
# global Settings singleton, which otherwise loads the repository dotenv file.
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from api import main  # noqa: E402
from api.persistence import SQLitePersistence  # noqa: E402
from api.state_service import (  # noqa: E402
    configure_persistence_for_tests,
    get_persistence,
)


@pytest.fixture(autouse=True)
def local_main_test_authority(monkeypatch):
    """Use the actual trusted local authority instead of TestClient's dummy host."""
    from starlette.testclient import TestClient
    original = TestClient.__init__
    original_websocket = TestClient.websocket_connect

    def local_init(self, app, *args, **kwargs):
        if app is main.app and not args:
            kwargs.setdefault('base_url', 'http://127.0.0.1:8000')
        original(self, app, *args, **kwargs)

    monkeypatch.setattr(TestClient, '__init__', local_init)

    def local_websocket(self, url, *args, **kwargs):
        # This Starlette version hardcodes ws://testserver for relative URLs.
        # Model a real browser authority, without weakening production checks.
        if self.app is main.app and isinstance(url, str) and url.startswith('/'):
            scheme = 'wss' if self.base_url.scheme == 'https' else 'ws'
            url = f'{scheme}://{self.base_url.netloc.decode()}{url}'
        return original_websocket(self, url, *args, **kwargs)

    monkeypatch.setattr(TestClient, 'websocket_connect', local_websocket)


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch):
    """Block Python HTTPX transports and non-loopback raw sockets during tests."""

    message = (
        "Network-backed HTTPX transports and non-loopback raw sockets are "
        "disabled inside pytest. "
        "Run intentional network evaluations with the explicit --live "
        "evaluator outside pytest."
    )

    def block_sync_request(_transport, _request):
        raise AssertionError(message)

    async def block_async_request(_transport, _request):
        raise AssertionError(message)

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_sendto = socket.socket.sendto
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def is_loopback_host(host) -> bool:
        if host is None or host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def is_local_address(address) -> bool:
        # AF_UNIX paths are local IPC.  Windows' asyncio ProactorEventLoop uses
        # an AF_INET socketpair on loopback for its internal self-pipe.
        if isinstance(address, str):
            return True
        return bool(address) and is_loopback_host(address[0])

    def guarded_connect(connection, address):
        if is_local_address(address):
            return original_connect(connection, address)
        raise AssertionError(message)

    def guarded_connect_ex(connection, address):
        if is_local_address(address):
            return original_connect_ex(connection, address)
        raise AssertionError(message)

    def guarded_sendto(connection, data, *args):
        address = args[-1] if args else None
        if is_local_address(address):
            return original_sendto(connection, data, *args)
        raise AssertionError(message)

    def guarded_create_connection(address, *args, **kwargs):
        if is_local_address(address):
            return original_create_connection(address, *args, **kwargs)
        raise AssertionError(message)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if is_loopback_host(host):
            return original_getaddrinfo(host, *args, **kwargs)
        raise AssertionError(message)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", block_sync_request)
    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        block_async_request,
    )
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", guarded_sendto)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)


@pytest.fixture(autouse=True)
def isolate_process_state(tmp_path):
    """Keep every test away from the configured campaign store and session cache."""

    previous_store = get_persistence()
    previous_sessions = dict(main.active_sessions)
    main.reset_llm_readiness_state_for_tests()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "process.sqlite3"))
    main.active_sessions.clear()
    try:
        yield
    finally:
        main.active_sessions.clear()
        main.active_sessions.update(previous_sessions)
        main.reset_llm_readiness_state_for_tests()
        configure_persistence_for_tests(previous_store)
