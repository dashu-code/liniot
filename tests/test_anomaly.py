"""EWMA 异常检测测试。"""
from __future__ import annotations

from liniot.anomaly import AnomalyDetector


def feed(det: AnomalyDetector, device: str, values: list[float],
         metric: str = "temperature") -> list[dict]:
    out: list[dict] = []
    for value in values:
        out.extend(det.evaluate(device, [{"metric": metric, "value": value}]))
    return out


NORMAL = [22.0, 22.2, 21.8, 22.1, 21.9, 22.3, 21.7, 22.0, 22.2, 21.8, 22.1]


def test_normal_data_never_fires():
    det = AnomalyDetector()
    assert feed(det, "s1", NORMAL * 3) == []


def test_warmup_blocks_early_spikes():
    det = AnomalyDetector()
    # 样本量不足 warmup 时，即使数值偏大也不判定
    assert feed(det, "s1", [22.0] * 5 + [45.0]) == []


def test_spike_fires_once_then_edges():
    det = AnomalyDetector()
    feed(det, "s1", NORMAL)
    fired = feed(det, "s1", [45.0])
    assert len(fired) == 1
    assert fired[0]["metric"] == "temperature"
    assert fired[0]["sigma"] > 3
    assert fired[0]["mean"] > 21 and fired[0]["mean"] < 23

    # 持续异常不重复告警；回落恢复后再次突增重新触发
    assert feed(det, "s1", [45.0]) == []
    feed(det, "s1", NORMAL)
    assert len(feed(det, "s1", [45.0])) == 1


def test_devices_and_metrics_are_independent():
    det = AnomalyDetector()
    feed(det, "s1", NORMAL)
    feed(det, "s2", NORMAL)
    feed(det, "s2", [22.0, 45.0])  # s2 在 warmup 早期，不应触发
    assert len(feed(det, "s1", [45.0])) == 1

    det2 = AnomalyDetector()
    feed(det2, "s1", NORMAL, metric="temperature")
    assert len(feed(det2, "s1", [45.0], metric="humidity")) == 0  # 指标各自建基线


def test_forget_clears_device_state():
    det = AnomalyDetector()
    feed(det, "s1", NORMAL)
    det.forget("s1")
    det.forget("ghost")
    assert feed(det, "s1", [22.0] * 5 + [45.0]) == []  # 重新从 warmup 开始
