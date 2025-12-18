from __future__ import annotations

import pytest

from app.common import in_memory_graph_payload_cache as graph_payload_cache


def test_build_cache_key_requires_graph_root_id_and_graph_id() -> None:
    graph_payload_cache.clear_all_graph_data()

    with pytest.raises(ValueError):
        graph_payload_cache.build_cache_key("", "graph_a")
    with pytest.raises(ValueError):
        graph_payload_cache.build_cache_key("root_a", "")


def test_store_fetch_resolve_and_invalidate_graph_payload_cache() -> None:
    graph_payload_cache.clear_all_graph_data()

    graph_data_first = {"graph_id": "graph_a", "nodes": [], "edges": []}
    graph_data_second = {"graph_id": "graph_a", "nodes": [{"id": "n1"}], "edges": []}

    cache_key_first = graph_payload_cache.store_graph_data("root_a", "graph_a", graph_data_first)
    cache_key_second = graph_payload_cache.store_graph_data("root_b", "graph_a", graph_data_second)

    assert cache_key_first == "root_a::graph_a"
    assert cache_key_second == "root_b::graph_a"

    assert graph_payload_cache.fetch_graph_data(cache_key_first) == graph_data_first
    assert graph_payload_cache.fetch_graph_data(cache_key_second) == graph_data_second

    # detail_info 优先使用直接 payload，其次使用 graph_data_key。
    assert (
        graph_payload_cache.resolve_graph_data({"graph_data": {"direct": True}, "graph_data_key": cache_key_first})
        == {"direct": True}
    )
    assert graph_payload_cache.resolve_graph_data({"graph_data_key": cache_key_first}) == graph_data_first
    assert graph_payload_cache.resolve_graph_data({"graph_data_key": "missing::key"}) is None
    assert graph_payload_cache.resolve_graph_data({"graph_data": "not-a-dict"}) is None

    # 按图 ID 失效：应清理所有图根下同一 graph_id 的缓存条目。
    graph_payload_cache.drop_graph_data_for_graph("graph_a")
    assert graph_payload_cache.fetch_graph_data(cache_key_first) is None
    assert graph_payload_cache.fetch_graph_data(cache_key_second) is None

    # 再写入两条，验证按图根失效与全量清空。
    cache_key_third = graph_payload_cache.store_graph_data("root_a", "graph_a", graph_data_first)
    cache_key_fourth = graph_payload_cache.store_graph_data("root_a", "graph_b", graph_data_second)
    assert graph_payload_cache.fetch_graph_data(cache_key_third) == graph_data_first
    assert graph_payload_cache.fetch_graph_data(cache_key_fourth) == graph_data_second

    graph_payload_cache.drop_graph_data_for_root("root_a")
    assert graph_payload_cache.fetch_graph_data(cache_key_third) is None
    assert graph_payload_cache.fetch_graph_data(cache_key_fourth) is None

    removed_count = graph_payload_cache.clear_all_graph_data()
    assert removed_count == 0


