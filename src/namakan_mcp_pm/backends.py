from __future__ import annotations

import json
import os
from importlib.resources import files
from pathlib import Path
from typing import Any, Protocol


class PmBackend(Protocol):
    name: str

    def find_task(self, query: str) -> list[dict[str, Any]]: ...
    def list_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]: ...
    def list_projects(self) -> list[dict[str, Any]]: ...
    def update_status(self, task_id: str, status: str) -> dict[str, Any]: ...
    def add_comment(self, task_id: str, body: str) -> dict[str, Any]: ...


def _seed() -> dict[str, Any]:
    return json.loads(files("namakan_mcp_pm.data").joinpath("mock.json").read_text(encoding="utf-8"))


class MockPm:
    name = "mock"

    def __init__(self, store: Path | None = None) -> None:
        self.store = store
        if store and store.exists():
            self._data = json.loads(store.read_text(encoding="utf-8"))
        else:
            self._data = _seed()

    def _save(self) -> None:
        if self.store:
            self.store.parent.mkdir(parents=True, exist_ok=True)
            self.store.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def find_task(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            t
            for t in self._data["tasks"]
            if q in t["title"].lower() or q == t["id"] or q in t.get("assignee", "").lower()
        ]

    def list_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]:
        tasks = self._data["tasks"]
        if project_id:
            return [t for t in tasks if t.get("project_id") == project_id]
        return list(tasks)

    def list_projects(self) -> list[dict[str, Any]]:
        return list(self._data["projects"])

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        for task in self._data["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                self._save()
                return task
        raise RuntimeError(f"unknown task {task_id}")

    def add_comment(self, task_id: str, body: str) -> dict[str, Any]:
        if not any(t["id"] == task_id for t in self._data["tasks"]):
            raise RuntimeError(f"unknown task {task_id}")
        item = {"task_id": task_id, "body": body}
        self._data["comments"].append(item)
        self._save()
        return item


class EnvPm:
    def __init__(self, name: str) -> None:
        self.name = name

    def _missing(self) -> None:
        raise RuntimeError(f"{self.name} is not configured. Use NAMAKAN_PM_BACKEND=mock for a laptop demo.")

    def find_task(self, query: str) -> list[dict[str, Any]]:
        self._missing()
        return []

    def list_tasks(self, project_id: str | None = None) -> list[dict[str, Any]]:
        self._missing()
        return []

    def list_projects(self) -> list[dict[str, Any]]:
        self._missing()
        return []

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        self._missing()
        return {}

    def add_comment(self, task_id: str, body: str) -> dict[str, Any]:
        self._missing()
        return {}


def load_backend(name: str | None) -> PmBackend:
    name = (name or os.environ.get("NAMAKAN_PM_BACKEND") or "mock").lower()
    if name in {"mock", "example"}:
        store = os.environ.get("NAMAKAN_PM_STORE")
        return MockPm(Path(store) if store else None)
    if name in {"jira", "asana", "monday", "clickup", "smartsheet", "ms-project", "trello"}:
        return EnvPm(name)
    raise ValueError(f"unknown PM backend: {name}")
