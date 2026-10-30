"""规则引擎测试：上升沿触发、持续不重复、恢复后可再次触发。"""
from __future__ import annotations

from liniot.bus import EventBus
from liniot.rules import RuleEngine
from liniot.store import Store


def make_engine(tmp_path, webhook=""):
    store = Store(tmp_path / "r.db")
    bus = EventBus()
    engine = RuleEngine(store, bus, webhook)
    store.upsert_device("sensor-1", "传感器", "sensor", {})
    return store, engine


def test_threshold_fires_once_while_condition_holds(tmp_path):
    store, engine = make_engine(tmp_path)
    store.create_rule("sensor-1", "temperature", ">", 30)

    first = engine.evaluate("sensor-1", [{"metric": "temperature", "value": 31}])
    assert len(first) == 1
    assert "temperature = 31 > 30" in first[0]["message"]

    # 持续超标不重复触发
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 32}]) == []
    assert store.list_alerts() == [store.list_alerts()[0]]

    # 恢复正常后再超标，应再次触发（新的上升沿）
    engine.evaluate("sensor-1", [{"metric": "temperature", "value": 25}])
    second = engine.evaluate("sensor-1", [{"metric": "temperature", "value": 35}])
    assert len(second) == 1
    assert len(store.list_alerts()) == 2


def test_rule_scoping_by_device_and_global(tmp_path):
    store, engine = make_engine(tmp_path)
    store.upsert_device("sensor-2", "传感器2", "sensor", {})
    store.create_rule("sensor-1", "humidity", "<", 40)          # 仅 sensor-1
    store.create_rule(None, "temperature", ">=", 30, note="全局高温")  # 所有设备

    fired = engine.evaluate("sensor-2", [{"metric": "temperature", "value": 31},
                                         {"metric": "humidity", "value": 20}])
    assert len(fired) == 1  # 只命中全局温度规则
    assert "全局高温" in fired[0]["message"]


def test_global_rule_edge_is_tracked_per_device(tmp_path):
    """全局规则在多设备交替上报时，每台设备独立触发一次，不互相重置。"""
    store, engine = make_engine(tmp_path)
    store.upsert_device("sensor-2", "传感器2", "sensor", {})
    store.create_rule(None, "temperature", ">", 24)

    # 两台设备都超标，各触发一次
    assert len(engine.evaluate("sensor-1", [{"metric": "temperature", "value": 25}])) == 1
    assert len(engine.evaluate("sensor-2", [{"metric": "temperature", "value": 26}])) == 1

    # 交替持续上报超标：不应再触发（此前按 rule_id 记状态会每 2 秒刷一条告警）
    for _ in range(3):
        assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 25.5}]) == []
        assert engine.evaluate("sensor-2", [{"metric": "temperature", "value": 26.5}]) == []
    assert len(store.list_alerts()) == 2


def test_disabled_rule_not_evaluated(tmp_path):
    store, engine = make_engine(tmp_path)
    rule = store.create_rule("sensor-1", "temperature", ">", 30)
    store.update_rule(rule["id"], enabled=False)
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 99}]) == []
