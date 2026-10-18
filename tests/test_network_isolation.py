from __future__ import annotations

import asyncio
import socket

import httpx
import pytest


UNRESOLVABLE_URL = "http://pytest-network-isolation.invalid/"


def test_real_http_transports_are_blocked_before_dns() -> None:
    with httpx.Client(transport=httpx.HTTPTransport()) as client:
        with pytest.raises(
            AssertionError,
            match=r"Network-backed HTTPX transports.*disabled inside pytest.*--live",
        ):
            client.get(UNRESOLVABLE_URL)

    async def attempt_async_request() -> None:
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport()) as client:
            await client.get(UNRESOLVABLE_URL)

    with pytest.raises(
        AssertionError,
        match=r"Network-backed HTTPX transports.*disabled inside pytest.*--live",
    ):
        asyncio.run(attempt_async_request())


def test_raw_socket_egress_is_blocked_before_the_operating_system() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        with pytest.raises(
            AssertionError,
            match=r"Network-backed HTTPX transports.*disabled inside pytest.*--live",
        ):
            connection.connect(("192.0.2.1", 443))

    with pytest.raises(
        AssertionError,
        match=r"Network-backed HTTPX transports.*disabled inside pytest.*--live",
    ):
        socket.getaddrinfo("pytest-network-isolation.invalid", 443)
