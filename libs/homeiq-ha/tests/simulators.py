"""Fixture-backed Home Assistant simulator shared across the test modules.

Extracted from test_agent_recipes.py (TAP-5921): six test files were importing
the harness from a sibling test module, which is fragile and inflated that
file past the maintainability gate. ``SimHA`` wires a scripted WebSocket
(``SimWs``) and REST (``SimRest``) pair over one mutable ``state`` dict seeded
from ``FRESH_INSTANCE`` — a factory-fresh instance shape captured live.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from homeiq_ha.client.errors import HACommandError

FRESH_INSTANCE: dict[str, Any] = {
    "backup_config": {
        "agents": {},
        "automatic_backups_configured": False,
        "create_backup": {"agent_ids": [], "password": None, "include_database": True},
        "retention": {"copies": None, "days": None},
        "schedule": {"days": [], "recurrence": "never", "time": None},
    },
    "backups": [],
    # One destination, as the live instance reports via backup/agents/info.
    "backup_agents": [{"agent_id": "hassio.local", "name": "local"}],
    #: Set by backup/generate; lands after `polls_until_done` reads of
    #: backup/info, mirroring Home Assistant's asynchronous job.
    "pending_backup": None,
    "polls_until_done": 0,
    "core_config": {"currency": "USD", "country": "US", "time_zone": "America/Los_Angeles"},
    "areas": [
        {"area_id": "living_room", "name": "Living Room"},
        {"area_id": "kitchen", "name": "Kitchen"},
        {"area_id": "bedroom", "name": "Bedroom"},
    ],
    "floors": [],
    "labels": [],
    "devices": [{"id": f"dev{i}", "name": f"WLED {i}", "area_id": None} for i in range(19)],
    "entities": [{"entity_id": f"light.wled_{i}"} for i in range(164)],
    "addons": [],
    "config_entries": [],
}


class SimWs:
    """WebSocket half of the simulator."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.writes: list[str] = []
        #: Every command with the fields it carried, so a test can assert on
        #: what was actually sent rather than only on the resulting state.
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _advance_backup(self) -> str:
        """Model an asynchronous backup job, one poll at a time."""
        pending = self.state.get("pending_backup")
        if not pending:
            return "idle"
        self.state["polls_until_done"] -= 1
        if self.state["polls_until_done"] > 0:
            return "create_backup"
        self.state["backups"].append(pending)
        self.state["pending_backup"] = None
        return "idle"

    async def send_command(
        self,
        command_type: str,
        *,
        _timeout: float | None = None,
        fields: dict[str, Any] | None = None,
        **payload: Any,
    ) -> Any:
        fields = fields or {}
        args = {**payload, **fields}
        self.calls.append((command_type, copy.deepcopy(args)))

        handled, result = self._read(command_type)
        if handled:
            return result
        if command_type == "supervisor/api":
            return await self._supervisor(args)

        # Everything below writes — recorded so tests can assert "no writes".
        self.writes.append(command_type)
        return self._write(command_type, args)

    def _read(self, command_type: str) -> tuple[bool, Any]:
        """Answer a read command; ``(False, None)`` when it isn't one."""
        if command_type == "backup/config/info":
            return True, {"config": self.state["backup_config"]}
        if command_type == "backup/agents/info":
            return True, {"agents": self.state["backup_agents"]}
        if command_type == "backup/info":
            # Advance first: the job lands partway through a poll loop, which is
            # the whole behaviour verify has to cope with.
            state = self._advance_backup()
            return True, {"backups": list(self.state["backups"]), "state": state}
        if command_type == "get_config":
            return True, self.state["core_config"]
        if command_type.endswith("_registry/list"):
            return True, self.state[_registry_key(command_type)]
        if command_type == "zha/devices":
            return True, self.state.get("zha_devices", [])
        if command_type == "config_entries/flow/progress":
            return True, self.state.get("flow_progress", [])
        if command_type == "hacs/repositories/list":
            return True, self.state.get("hacs_repositories", [])
        return False, None

    def _write(self, command_type: str, args: dict[str, Any]) -> Any:
        if command_type == "config_entries/ignore_flow":
            # Mirror HA core config_entries.py ignore_config_flow: unknown
            # flow -> not_found; a flow without unique_id is refused; else
            # the flow is dismissed and an ignore-source entry persists it.
            flows = self.state.get("flow_progress", [])
            flow = next((f for f in flows if f.get("flow_id") == args.get("flow_id")), None)
            if flow is None:
                raise HACommandError(command_type, "not_found", "Flow not found")
            if "unique_id" not in (flow.get("context") or {}):
                raise HACommandError(
                    command_type, "no_unique_id", "Specified flow has no unique ID."
                )
            self.state["flow_progress"] = [f for f in flows if f is not flow]
            self.state["config_entries"].append(
                {
                    "entry_id": f"ignore-{args['flow_id']}",
                    "domain": flow.get("handler"),
                    "source": "ignore",
                    "title": args.get("title"),
                }
            )
            return None
        if command_type == "hacs/repository/download":
            # Mirror HACS: download flips installed; loading needs a restart.
            for repo in self.state.get("hacs_repositories", []):
                if str(repo.get("id")) == str(args.get("repository")):
                    repo["installed"] = True
            return None
        if command_type == "backup/config/update":
            return self._backup_config_update(args)
        if command_type == "backup/generate":
            return self._backup_generate(args)
        if command_type == "config/core/update":
            self.state["core_config"].update(args)
            return None
        if command_type == "backup/delete":
            self.state["backups"] = [
                b for b in self.state["backups"] if b["backup_id"] != args["backup_id"]
            ]
            return None
        if command_type.endswith("_registry/create"):
            return self._registry_create(command_type, args)
        if command_type.endswith("_registry/delete"):
            key = _registry_key(command_type)
            id_field = _registry_id_field(command_type)
            target = args[id_field]
            self.state[key] = [e for e in self.state[key] if e.get(id_field) != target]
            return None
        if command_type.endswith("_registry/update"):
            return self._registry_update(command_type, args)
        return None

    def _backup_config_update(self, args: dict[str, Any]) -> None:
        config = self.state["backup_config"]
        config["schedule"].update(args.get("schedule") or {})
        config["retention"].update(args.get("retention") or {})
        config["create_backup"].update(args.get("create_backup") or {})
        # A schedule only becomes live once it has somewhere to write to;
        # observed on the live instance, which starts reporting
        # next_automatic_backup the moment agent_ids is non-empty.
        scheduled = bool(
            config["schedule"].get("recurrence") not in (None, "never")
            and config["create_backup"].get("agent_ids")
        )
        config["next_automatic_backup"] = "2026-08-02T04:56:21-07:00" if scheduled else None
        # Deliberately NOT touched: HA core marks automatic_backups_configured
        # "only used by frontend" (components/backup/config.py) — it records
        # frontend-onboarding completion and is never derived from config
        # updates, so it stays false on an API-configured instance (TAP-6027).

    def _backup_generate(self, args: dict[str, Any]) -> dict[str, Any]:
        if not args.get("agent_ids"):
            raise HACommandError(
                "backup/generate", "invalid_format", "required key not provided: agent_ids"
            )
        self.state["pending_backup"] = {"backup_id": "b1", "name": args.get("name")}
        self.state["polls_until_done"] = 2
        # Only a job handle — the backup itself does not exist yet.
        return {"backup_job_id": "job1"}

    def _registry_create(self, command_type: str, args: dict[str, Any]) -> dict[str, Any]:
        key = _registry_key(command_type)
        # HA assigns slug ids (lowercase, non-alnum -> _), not raw names.
        slug = re.sub(r"[^a-z0-9]+", "_", args["name"].lower()).strip("_")
        self.state[key].append({f"{key[:-1]}_id": slug, "name": args["name"]})
        return self.state[key][-1]

    def _registry_update(self, command_type: str, args: dict[str, Any]) -> Any:
        key = _registry_key(command_type)
        id_field = _registry_id_field(command_type)
        # The live device-registry API takes device_id even though the
        # registry entries themselves are keyed "id".
        target = args.pop(id_field, None) or args.pop("device_id", None)
        # Mirror HA: an entity rename arrives as new_entity_id.
        if key == "entities" and "new_entity_id" in args:
            args["entity_id"] = args.pop("new_entity_id")
        for entry in self.state[key]:
            if entry.get(id_field) == target:
                entry.update(args)
                return entry
        return None

    async def _supervisor(self, args: dict[str, Any]) -> Any:
        endpoint = args["endpoint"]
        method = args.get("method", "get")
        if method == "get":
            return self._supervisor_read(endpoint)
        self.writes.append(f"supervisor {method} {endpoint}")
        return self._supervisor_write(endpoint, args.get("data"))

    def _supervisor_read(self, endpoint: str) -> Any:
        if endpoint == "/addons":
            return {"addons": self.state["addons"]}
        if endpoint.startswith("/addons/") and endpoint.endswith("/info"):
            slug = endpoint.split("/")[2]
            return self.state.get("addon_info", {}).get(slug, {})
        return None

    def _supervisor_write(self, endpoint: str, data: dict[str, Any] | None = None) -> None:
        if endpoint.startswith("/addons/") and endpoint.endswith("/options"):
            slug = endpoint.split("/")[2]
            info = self.state.setdefault("addon_info", {}).setdefault(slug, {})
            info.setdefault("options", {}).update((data or {}).get("options") or {})
        elif endpoint.startswith("/store/addons/") and endpoint.endswith("/install"):
            slug = endpoint.split("/")[3]
            self.state["addons"].append({"slug": slug, "state": "stopped"})
        elif endpoint.startswith("/addons/") and endpoint.endswith("/start"):
            slug = endpoint.split("/")[2]
            for addon in self.state["addons"]:
                if addon["slug"] == slug:
                    addon["state"] = "started"
        elif endpoint.startswith("/addons/") and endpoint.endswith("/uninstall"):
            slug = endpoint.split("/")[2]
            self.state["addons"] = [a for a in self.state["addons"] if a["slug"] != slug]

    async def list_entities(self) -> list[dict[str, Any]]:
        return self.state["entities"]

    async def close(self) -> None:
        self.state.setdefault("ws_reconnects", []).append("close")

    async def connect(self) -> None:
        self.state.setdefault("ws_reconnects", []).append("connect")

    async def supervisor_api(
        self,
        endpoint: str,
        *,
        method: str = "get",
        payload: dict[str, Any] | None = None,
        timeout: float = 900,
    ) -> Any:
        fields: dict[str, Any] = {"endpoint": endpoint, "method": method, "timeout": int(timeout)}
        if payload is not None:
            fields["data"] = payload
        return await self.send_command("supervisor/api", fields=fields)


#: registry name -> (state key, id field)
_REGISTRIES = {
    "area": ("areas", "area_id"),
    "floor": ("floors", "floor_id"),
    "label": ("labels", "label_id"),
    "device": ("devices", "id"),
    "entity": ("entities", "entity_id"),
}


def _registry_key(command_type: str) -> str:
    # config/area_registry/list -> areas
    registry = command_type.split("/")[1].removesuffix("_registry")
    return _REGISTRIES[registry][0]


def _registry_id_field(command_type: str) -> str:
    registry = command_type.split("/")[1].removesuffix("_registry")
    return _REGISTRIES[registry][1]


class SimRest:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.writes: list[str] = []

    async def start_config_flow(self, domain: str, **_context: Any) -> dict[str, Any]:
        """First step of a config flow, scripted via state['flow_first_step']."""
        self.writes.append(f"flow_start {domain}")
        return dict(
            self.state.get("flow_first_step")
            or {"type": "form", "flow_id": "sim-flow", "data_schema": []}
        )

    async def advance_config_flow(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        self.writes.append(f"flow_advance {flow_id}")
        self.state.setdefault("flow_inputs", []).append(dict(user_input))
        queue = self.state.get("flow_steps")
        if queue:
            # Scripted multi-step flow: each advance pops the next step.
            step = dict(queue.pop(0))
        else:
            step = dict(self.state.get("flow_next_step") or {"type": "create_entry"})
            if step.get("type") == "create_entry" and user_input.get("name"):
                # Mirror HA: the created entity_id derives from the name.
                slug = re.sub(r"[^a-z0-9]+", "_", str(user_input["name"]).lower()).strip("_")
                self.state["entities"].append({"entity_id": f"sensor.{slug}"})
        for entity in step.pop("add_entities", []):
            # Scripted side effect: entities the completing step materialises.
            self.state["entities"].append(dict(entity))
        for flow in step.pop("add_flows", []):
            # Scripted side effect: discovery flows a completing setup opens.
            self.state.setdefault("flow_progress", []).append(dict(flow))
        result = step.get("result")
        if step.get("type") == "create_entry" and isinstance(result, dict):
            # Mirror HA: a completed flow's entry becomes readable back.
            self.state["config_entries"].append(dict(result))
        return step

    async def abort_config_flow(self, flow_id: str) -> None:
        self.writes.append(f"flow_abort {flow_id}")
        self.state["flow_progress"] = [
            f for f in self.state.get("flow_progress", []) if f.get("flow_id") != flow_id
        ]

    async def get_config_flow(self, flow_id: str) -> dict[str, Any]:
        """Current-step re-render (a read).

        Scripted via state['flow_current_steps'] (per flow_id) falling back
        to state['flow_current_step'] (one shared step).
        """
        per_flow = self.state.get("flow_current_steps") or {}
        return dict(
            per_flow.get(flow_id)
            or self.state.get("flow_current_step")
            or {"type": "form", "flow_id": flow_id, "data_schema": []}
        )

    @staticmethod
    def classify_flow_step(step: dict[str, Any]) -> str:
        # The production classifier, so tests exercise real semantics.
        from homeiq_ha.client.rest import HARestClient

        return HARestClient.classify_flow_step(step)

    async def request(self, method: str, path: str, **_kwargs: Any) -> Any:
        if method.upper() != "GET":
            self.writes.append(f"{method.upper()} {path}")
        if path == "/api/config":
            return {"state": "RUNNING"}
        if path == "/api/config/config_entries/entry":
            return self.state["config_entries"]
        if method.upper() == "DELETE" and path.startswith("/api/config/config_entries/entry/"):
            entry_id = path.rsplit("/", 1)[-1]
            self.state["config_entries"] = [
                e for e in self.state["config_entries"] if e.get("entry_id") != entry_id
            ]
            return {}
        return {}

    async def get_config_entries(self) -> list[dict[str, Any]]:
        return await self.request("GET", "/api/config/config_entries/entry")

    async def get_states(self) -> list[dict[str, Any]]:
        return self.state.get("states", [])

    async def check_config(self) -> dict[str, Any]:
        return dict(self.state.get("check_config") or {"result": "valid"})

    async def call_service(self, domain: str, service: str, **data: Any) -> Any:
        self.writes.append(f"service {domain}.{service}")
        self.state.setdefault("service_calls", []).append((domain, service, data))
        return {}

    async def run_config_flow(self, domain: str, _steps: list[dict[str, Any]], **_c: Any) -> Any:
        self.writes.append(f"config_flow {domain}")
        self.state["config_entries"].append(
            {"entry_id": f"entry_{domain}", "domain": domain, "state": "loaded"}
        )
        return {"type": "create_entry"}


class SimHA:
    """Fixture-backed Home Assistant simulator."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = copy.deepcopy(state or FRESH_INSTANCE)
        self.base_url = "http://sim.test"
        self.ws = SimWs(self.state)
        self.rest = SimRest(self.state)

    @property
    def writes(self) -> list[str]:
        return self.ws.writes + self.rest.writes
