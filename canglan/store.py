"""Validated local storage. A failed save never changes the in-memory state."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Callable
from uuid import uuid4


class StoreError(Exception):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "CanglanTodo"


def validate(data: object) -> dict:
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("不支持的数据格式")
    queues = data.get("queues")
    if not isinstance(queues, list):
        raise ValueError("队列数据缺失")
    ids: set[str] = set()
    for queue in queues:
        if not isinstance(queue, dict):
            raise ValueError("队列格式错误")
        for key in ("id", "title", "created_at"):
            if not isinstance(queue.get(key), str) or not queue[key].strip():
                raise ValueError("队列字段错误")
        if queue["id"] in ids:
            raise ValueError("队列编号重复")
        ids.add(queue["id"])
        if queue.get("archived_at") is not None and not isinstance(queue["archived_at"], str):
            raise ValueError("归档日期错误")
        if not isinstance(queue.get("items"), list):
            raise ValueError("条目数据缺失")
        item_ids: set[str] = set()
        for item in queue["items"]:
            if not isinstance(item, dict):
                raise ValueError("条目格式错误")
            for key in ("id", "text", "created_at"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError("条目字段错误")
            if type(item.get("done")) is not bool or item["id"] in item_ids:
                raise ValueError("条目状态错误")
            if item.get("completed_at") is not None and not isinstance(item["completed_at"], str):
                raise ValueError("条目完成日期错误")
            item_ids.add(item["id"])
    return data


class Store:
    def __init__(self, data_dir: Path | None = None):
        self.directory = Path(data_dir) if data_dir else default_data_dir()
        self.path = self.directory / "quests.json"
        self.backup = self.directory / "quests.backup.json"
        self.recovery_notice: str | None = None
        self.directory.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists() and not self.backup.exists():
            return {"version": 1, "queues": []}
        try:
            return validate(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            try:
                recovered = validate(json.loads(self.backup.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError) as error:
                raise StoreError(f"无法读取待办数据。原文件已保留，请检查：\n{self.path}") from error
            if self.path.exists():
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                self.path.rename(self.directory / f"quests.corrupt.{stamp}.json")
            self._atomic_write(self.path, recovered)
            self.recovery_notice = "主数据文件异常，已恢复上一次备份；原文件已保留。"
            return recovered

    @staticmethod
    def _atomic_write(path: Path, data: dict) -> None:
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=".quests-", suffix=".tmp", delete=False) as handle:
                temporary = handle.name
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def _commit(self, mutate: Callable[[dict], None]) -> None:
        candidate = deepcopy(self.data)
        mutate(candidate)
        validate(candidate)
        try:
            # The backup is always a previously valid state, never a partial write.
            self._atomic_write(self.backup, self.data)
            self._atomic_write(self.path, candidate)
        except OSError as error:
            raise StoreError(f"保存失败，当前修改尚未写入。\n{error}") from error
        self.data = candidate

    def queues(self, archived: bool = False) -> list[dict]:
        result = [deepcopy(q) for q in self.data["queues"] if bool(q.get("archived_at")) == archived]
        return sorted(result, key=lambda q: q["archived_at"], reverse=True) if archived else result

    def queue(self, queue_id: str) -> dict:
        return deepcopy(self._find(self.data, queue_id))

    @staticmethod
    def _find(data: dict, queue_id: str, *, editable: bool = False) -> dict:
        queue = next((q for q in data["queues"] if q["id"] == queue_id), None)
        if queue is None:
            raise StoreError("委托已不存在")
        if editable and queue.get("archived_at"):
            raise StoreError("请先重启这纸委托，再修改条目")
        return queue

    @staticmethod
    def _text(value: str, maximum: int) -> str:
        text = value.strip()
        if not text or len(text) > maximum:
            raise StoreError(f"请输入 1–{maximum} 个字符")
        return text

    def add_queue(self, title: str) -> str:
        title = self._text(title, 60)
        key = uuid4().hex
        self._commit(lambda data: data["queues"].append({
            "id": key, "title": title, "created_at": now(), "archived_at": None, "items": []
        }))
        return key

    def rename_queue(self, key: str, title: str) -> None:
        title = self._text(title, 60)
        self._commit(lambda data: self._find(data, key, editable=True).update(title=title))

    def delete_queue(self, key: str) -> None:
        self.queue(key)
        self._commit(lambda data: data.update(queues=[q for q in data["queues"] if q["id"] != key]))

    def archive_queue(self, key: str) -> None:
        self._commit(lambda data: self._find(data, key, editable=True).update(archived_at=now()))

    def restore_queue(self, key: str) -> None:
        self._commit(lambda data: self._find(data, key).update(archived_at=None))

    def add_item(self, queue_id: str, text: str) -> str:
        text = self._text(text, 300)
        key = uuid4().hex
        self._commit(lambda data: self._find(data, queue_id, editable=True)["items"].append({
            "id": key, "text": text, "done": False, "created_at": now(), "completed_at": None
        }))
        return key

    def edit_item(self, queue_id: str, key: str, text: str) -> None:
        text = self._text(text, 300)
        self._mutate_item(queue_id, key, lambda item: item.update(text=text))

    def toggle_item(self, queue_id: str, key: str) -> None:
        def toggle(item: dict) -> None:
            item.update(done=not item["done"], completed_at=None if item["done"] else now())
        self._mutate_item(queue_id, key, toggle)

    def _mutate_item(self, queue_id: str, key: str, mutation: Callable[[dict], None]) -> None:
        def change(data: dict) -> None:
            queue = self._find(data, queue_id, editable=True)
            item = next((i for i in queue["items"] if i["id"] == key), None)
            if item is None:
                raise StoreError("条目已不存在")
            mutation(item)
        self._commit(change)

    def delete_item(self, queue_id: str, key: str) -> None:
        def remove(data: dict) -> None:
            queue = self._find(data, queue_id, editable=True)
            if not any(i["id"] == key for i in queue["items"]):
                raise StoreError("条目已不存在")
            queue["items"] = [i for i in queue["items"] if i["id"] != key]
        self._commit(remove)
