from __future__ import annotations

from typing import Any, Protocol


class PmBackend(Protocol):
    name: str

    def find_task(self, query: str) -> list[dict[str, Any]]: ...
    def update_status(self, task_id: str, status: str) -> dict[str, Any]: ...
    def add_comment(self, task_id: str, body: str) -> dict[str, Any]: ...


class MockPm:
    name = "mock"

    def __init__(self) -> None:
        self.tasks = [
            {"id": "t1", "title": "Phase 1 audit", "status": "doing", "assignee": "discovery-analyst"},
        ]
        self.comments: list[dict[str, Any]] = []

    def find_task(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [t for t in self.tasks if q in t["title"].lower() or q == t["id"]]

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = status
                return t
        raise KeyError(task_id)

    def add_comment(self, task_id: str, body: str) -> dict[str, Any]:
        item = {"task_id": task_id, "body": body}
        self.comments.append(item)
        return item


class EnvPm:
    def __init__(self, name: str) -> None:
        self.name = name

    def _missing(self) -> None:
        raise RuntimeError(f"{self.name} is not configured in this tenant.")

    def find_task(self, query: str) -> list[dict[str, Any]]:
        self._missing()
        return []

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        self._missing()
        return {}

    def add_comment(self, task_id: str, body: str) -> dict[str, Any]:
        self._missing()
        return {}


def load_backend(name: str | None) -> PmBackend:
    name = (name or "mock").lower()
    if name in {"mock", "example"}:
        return MockPm()
    if name in {"jira", "asana", "monday", "clickup", "smartsheet", "ms-project", "trello"}:
        return EnvPm(name)
    raise ValueError(f"unknown PM backend: {name}")
