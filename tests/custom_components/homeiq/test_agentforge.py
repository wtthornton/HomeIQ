"""Tests for the AgentForge invocation client (TAP-5307)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from aiohttp import ClientError, ClientSession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.homeiq.agentforge import (
    AgentForgeClient,
    AgentForgeError,
    AgentForgeResponse,
    AgentForgeUnauthorizedError,
)

from .conftest import AGENTFORGE_ENDPOINT, AGENTFORGE_URL, task_response

STEERED = {
    "invocation_id": "b9d8cae7",
    "status": "running",
    "invoke_steered": True,
    "steer_reason": "exceeds_sync_invoke_steering_threshold",
}
RESULT_URL = f"{AGENTFORGE_URL}/projects/homeiq/invocations/b9d8cae7/result"

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
def mocker() -> AiohttpClientMocker:
    """Return an aiohttp request mocker."""
    return AiohttpClientMocker()


@pytest.fixture
async def session(mocker: AiohttpClientMocker) -> AsyncGenerator[ClientSession]:
    """Return a session bound to the mocker."""
    client_session = mocker.create_session(asyncio.get_running_loop())
    yield client_session
    await client_session.close()


@pytest.fixture
def client(session: ClientSession) -> AgentForgeClient:
    """Return a client pointed at the mocked AgentForge."""
    return AgentForgeClient(
        session, AGENTFORGE_URL, "afp_test", "homeiq", 5, poll_interval=0, async_wait=5
    )


async def test_invoke_posts_the_project_route(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """The prompt goes to the project-scoped invoke route with a bearer key."""
    mocker.post(AGENTFORGE_ENDPOINT, json=task_response())

    response = await client.async_invoke("How long was the kitchen light on?")

    _method, url, body, headers = mocker.mock_calls[0]
    assert str(url) == AGENTFORGE_ENDPOINT
    assert body == {"prompt": "How long was the kitchen light on?"}
    assert headers["Authorization"] == "Bearer afp_test"
    assert response.text == "The kitchen light was on for 4 hours."
    assert response.as_user_message() == "The kitchen light was on for 4 hours."


async def test_config_hint_is_forwarded(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """An agent selector is passed through when given."""
    mocker.post(AGENTFORGE_ENDPOINT, json=task_response())

    await client.async_invoke("hello", config_hint="analyst")

    assert mocker.mock_calls[0][2]["config_hint"] == "analyst"


async def test_budget_block_reads_as_a_refusal(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A blocked plan is a refusal message, not an exception."""
    mocker.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(
            result="orchestration blocked by budget: portfolio monthly budget hard cap engaged",
            is_error=True,
        ),
    )

    response = await client.async_invoke("summarise the month")

    assert response.refused_for_budget is True
    message = response.as_user_message()
    assert "stopped this request before spending more" in message
    assert "portfolio monthly budget hard cap engaged" in message
    assert "could not complete" not in message


async def test_per_run_budget_cap_reads_as_a_refusal(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """The per-run spend cap is recognised as a budget refusal too."""
    mocker.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(
            result="Platform API anthropic exceeded max_budget_usd ($3.1000 > $2.00)",
            is_error=True,
        ),
    )

    response = await client.async_invoke("summarise the month")

    assert response.refused_for_budget is True
    assert "stopped this request before spending more" in response.as_user_message()


async def test_awaiting_budget_gate_reads_as_a_pause(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A soft budget gate tells the user where to approve it."""
    mocker.post(
        AGENTFORGE_ENDPOINT,
        json=task_response(result="", orchestration_state="awaiting_gate"),
    )

    assert (
        "paused this request for budget approval"
        in (await client.async_invoke("plan something big")).as_user_message()
    )


async def test_generic_agent_error_is_readable(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A non-budget failure is reported as a failure, with the detail kept."""
    mocker.post(AGENTFORGE_ENDPOINT, json=task_response(result="tool crashed", is_error=True))

    response = await client.async_invoke("do the thing")

    assert response.refused_for_budget is False
    assert response.as_user_message() == ("HomeIQ could not complete that request: tool crashed")


async def test_error_without_detail_still_says_something() -> None:
    """An empty error result does not produce an empty message."""
    response = AgentForgeResponse(text="", is_error=True, agent_used="x", orchestration_state=None)

    assert "no detail" in response.as_user_message()


@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        ("missing-bearer", "AgentForge did not receive an API key."),
        ("key-invalid-or-revoked", "AgentForge rejected the API key as invalid or revoked."),
        ("cross-project-denied", "The AgentForge API key belongs to a different project."),
    ],
)
async def test_auth_failures_are_named(
    client: AgentForgeClient, mocker: AiohttpClientMocker, detail: str, expected: str
) -> None:
    """Each project-auth rejection maps to its own message."""
    status = 403 if detail == "cross-project-denied" else 401
    mocker.post(AGENTFORGE_ENDPOINT, status=status, json={"detail": detail})

    with pytest.raises(AgentForgeUnauthorizedError) as err:
        await client.async_invoke("hi")

    assert err.value.user_message == expected


@pytest.mark.parametrize(
    ("status", "code", "fragment"),
    [
        (404, "not_found", "no such project or agent"),
        (503, "unavailable", "AgentForge is unavailable"),
        (504, "timeout", "took too long"),
        (500, "http_error", "returned HTTP 500"),
    ],
)
async def test_http_failures_are_mapped(
    client: AgentForgeClient,
    mocker: AiohttpClientMocker,
    status: int,
    code: str,
    fragment: str,
) -> None:
    """Every documented failure status becomes a readable error."""
    mocker.post(AGENTFORGE_ENDPOINT, status=status, json={"detail": "boom"})

    with pytest.raises(AgentForgeError) as err:
        await client.async_invoke("hi")

    assert err.value.code == code
    assert fragment in err.value.user_message


async def test_unreachable_agentforge_is_named(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A connection failure is reported as unreachable."""
    mocker.post(AGENTFORGE_ENDPOINT, exc=ClientError("no route"))

    with pytest.raises(AgentForgeError) as err:
        await client.async_invoke("hi")

    assert err.value.code == "unreachable"
    assert "could not reach AgentForge" in err.value.user_message


async def test_non_json_body_is_a_contract_violation(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A body that is not JSON is refused rather than silently accepted."""
    mocker.post(AGENTFORGE_ENDPOINT, text="<html>gateway</html>")

    with pytest.raises(AgentForgeError) as err:
        await client.async_invoke("hi")

    assert err.value.code == "contract_violation"


async def test_verify_uses_match_only(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """The connectivity probe resolves the key without spawning an agent."""
    mocker.post(AGENTFORGE_ENDPOINT, json={"agent": "homeiq-analyst", "confidence": 0.9})

    await client.async_verify()

    assert mocker.mock_calls[0][2]["match_only"] is True


async def test_verify_tolerates_no_matching_agent(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """AGENT_NOT_FOUND still proves the project and key are good."""
    mocker.post(
        AGENTFORGE_ENDPOINT,
        status=404,
        json={"detail": {"error_code": "AGENT_NOT_FOUND", "detail": "no agent matched"}},
    )

    await client.async_verify()


async def test_verify_rejects_an_unknown_project(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A missing project is a real configuration failure."""
    mocker.post(AGENTFORGE_ENDPOINT, status=404, json={"detail": "project 'homeiq' not found"})

    with pytest.raises(AgentForgeError):
        await client.async_verify()


async def test_verify_rejects_a_bad_key(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """An invalid key fails the probe."""
    mocker.post(AGENTFORGE_ENDPOINT, status=401, json={"detail": "key-invalid-or-revoked"})

    with pytest.raises(AgentForgeUnauthorizedError):
        await client.async_verify()


async def test_steered_invoke_is_followed_to_its_result(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A 202 with only an invocation id is collected from the result route.

    AgentForge steers a long prompt onto its async queue instead of answering
    inline. Before this was handled the entity got an empty string, which Home
    Assistant surfaced as a bare "Unable to get response".
    """
    mocker.post(AGENTFORGE_ENDPOINT, json=STEERED, status=202)
    mocker.get(RESULT_URL, json=task_response(status="complete"))

    response = await client.async_invoke("Which areas exist in this home?")

    assert response.text == "The kitchen light was on for 4 hours."
    assert response.is_error is False
    assert response.agent_used == "homeiq-analyst"
    assert str(mocker.mock_calls[-1][1]) == RESULT_URL


async def test_steered_invoke_waits_while_the_result_is_not_terminal(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A 404 means "not finished yet", so polling continues rather than failing."""
    mocker.post(AGENTFORGE_ENDPOINT, json=STEERED, status=202)
    # The mocker returns its first matching registration every time, so the
    # run has to settle through a side effect rather than two registrations.
    polls = 0

    async def settle_on_the_third_poll(method, url, _data):
        nonlocal polls
        polls += 1
        if polls < 3:
            return AiohttpClientMockResponse(
                method, url, status=404, json={"detail": "not found or not terminal"}
            )
        return AiohttpClientMockResponse(method, url, json=task_response())

    mocker.get(RESULT_URL, side_effect=settle_on_the_third_poll)

    response = await client.async_invoke("Which areas exist in this home?")

    assert polls == 3
    assert response.text == "The kitchen light was on for 4 hours."


async def test_steered_invoke_gives_up_with_a_readable_message(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """A run that never settles is a readable timeout, not a hang or a stack trace."""
    mocker.post(AGENTFORGE_ENDPOINT, json=STEERED, status=202)
    for _ in range(50):
        mocker.get(RESULT_URL, json={"detail": "not found or not terminal"}, status=404)

    with pytest.raises(AgentForgeError) as caught:
        await client.async_invoke("Which areas exist in this home?")

    assert caught.value.code == "timeout"
    assert "queued" in caught.value.user_message


async def test_invoke_without_result_or_invocation_is_a_contract_violation(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """Neither an answer nor something to follow is AgentForge breaking its contract."""
    mocker.post(AGENTFORGE_ENDPOINT, json={"status": "running"}, status=202)

    with pytest.raises(AgentForgeError) as caught:
        await client.async_invoke("Which areas exist in this home?")

    assert caught.value.code == "contract_violation"


def test_answer_field_is_unwrapped_for_the_user() -> None:
    """A gene answering with the house JSON envelope shows its prose, not the object."""
    response = AgentForgeResponse(
        text='{"answer": "You have a kitchen, an office and a garage.", "confidence": 0.9}',
        is_error=False,
        agent_used="homeiq-hiq-assistant",
        orchestration_state=None,
    )

    assert response.as_user_message() == "You have a kitchen, an office and a garage."


def test_plain_prose_and_unparseable_bodies_pass_through() -> None:
    """Only a JSON object carrying a string answer is unwrapped; nothing else is touched."""
    for text in (
        "The kitchen light was on for 4 hours.",
        '{"result": "no answer key here"}',
        "{not json at all",
        '{"answer": {"nested": "not a string"}}',
    ):
        response = AgentForgeResponse(
            text=text, is_error=False, agent_used="a", orchestration_state=None
        )
        assert response.as_user_message() == text


async def test_invoke_sends_the_config_hint(
    client: AgentForgeClient, mocker: AiohttpClientMocker
) -> None:
    """The hint is what binds the call to a project agent instead of the global orchestrator."""
    mocker.post(AGENTFORGE_ENDPOINT, json=task_response())

    await client.async_invoke("Which areas exist?", config_hint="hiq-assistant")

    _method, _url, body, _headers = mocker.mock_calls[0]
    assert body == {"prompt": "Which areas exist?", "config_hint": "hiq-assistant"}
