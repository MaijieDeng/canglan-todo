import json

import pytest

from canglan.store import Store, StoreError


def test_queue_lifecycle_and_completed_items_survive_restart(tmp_path):
    store = Store(tmp_path)
    first = store.add_queue("今日修行")
    second = store.add_queue("长远计划")
    item = store.add_item(first, "读书")
    store.add_item(first, "散步")
    store.toggle_item(first, item)
    store.archive_queue(first)
    reloaded = Store(tmp_path)
    assert [q["id"] for q in reloaded.queues()] == [second]
    assert [q["id"] for q in reloaded.queues(True)] == [first]
    assert len(reloaded.queue(first)["items"]) == 2
    assert reloaded.queue(first)["items"][0]["done"]
    assert reloaded.queue(first)["items"][0]["completed_at"]
    reloaded.restore_queue(first)
    reloaded.toggle_item(first, item)
    assert not reloaded.queue(first)["items"][0]["done"]
    assert reloaded.queue(first)["items"][0]["completed_at"] is None
    assert len(reloaded.queues()) == 2


def test_edit_delete_and_archive_protection(tmp_path):
    store = Store(tmp_path)
    queue = store.add_queue("初稿")
    item = store.add_item(queue, "草稿")
    store.rename_queue(queue, "终稿")
    store.toggle_item(queue, item)
    store.edit_item(queue, item, "校对")
    assert store.queue(queue)["items"][0]["done"]
    store.archive_queue(queue)
    with pytest.raises(StoreError):
        store.add_item(queue, "不应添加")
    with pytest.raises(StoreError):
        store.delete_item(queue, item)
    store.restore_queue(queue)
    store.delete_item(queue, item)
    assert store.queue(queue)["items"] == []
    store.delete_queue(queue)
    assert Store(tmp_path).queues() == []


@pytest.mark.parametrize("text", ["", "   ", "字" * 61])
def test_invalid_queue_titles_do_not_write(tmp_path, text):
    store = Store(tmp_path)
    with pytest.raises(StoreError):
        store.add_queue(text)
    assert store.queues() == []
    assert not store.path.exists()


def test_recovers_backup_and_preserves_corrupt_original(tmp_path):
    store = Store(tmp_path)
    queue = store.add_queue("重要记录")
    store.add_item(queue, "上一版本")
    store.add_item(queue, "最新版本")
    store.path.write_text("{broken", encoding="utf-8")
    recovered = Store(tmp_path)
    assert recovered.recovery_notice
    assert len(recovered.queue(queue)["items"]) == 1
    assert next(tmp_path.glob("quests.corrupt.*.json")).read_text(encoding="utf-8") == "{broken"
    assert json.loads(recovered.path.read_text(encoding="utf-8"))["version"] == 1


def test_corrupt_data_without_valid_backup_is_never_overwritten(tmp_path):
    path = tmp_path / "quests.json"
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(StoreError):
        Store(tmp_path)
    assert path.read_text(encoding="utf-8") == "broken"


def test_failed_save_leaves_memory_and_last_valid_file_unchanged(tmp_path, monkeypatch):
    store = Store(tmp_path)
    store.add_queue("原有记录")
    original_file = store.path.read_bytes()
    original_write = store._atomic_write

    def fail_primary(path, data):
        if path == store.path:
            raise PermissionError("模拟磁盘写入失败")
        original_write(path, data)

    monkeypatch.setattr(store, "_atomic_write", fail_primary)
    with pytest.raises(StoreError):
        store.add_queue("未保存记录")
    assert [q["title"] for q in store.queues()] == ["原有记录"]
    assert store.path.read_bytes() == original_file


def test_readers_cannot_mutate_store_without_a_commit(tmp_path):
    store = Store(tmp_path)
    key = store.add_queue("原有记录")
    store.queues()[0]["title"] = "意外修改"
    store.queue(key)["title"] = "另一次修改"
    assert store.queue(key)["title"] == "原有记录"
