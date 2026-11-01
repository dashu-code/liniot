"""EWMA 基线异常检测：无需配置规则，指标突变自动告警。

对每个 (设备, 指标) 维护指数加权移动均值与方差：
    mean_t = (1-α)·mean_{t-1} + α·x_t
    var_t  = (1-α)·var_{t-1}  + α·(x_t - mean_t)²
当 |x - mean| > sensitivity·σ 且样本量达到 warmup 时判定为异常；
与阈值规则相同，采用边沿触发：持续异常只告警一次，恢复后再次突增才重新告警。
"""
from __future__ import annotations

import math
from typing import Any


class AnomalyDetector:
    def __init__(self, sensitivity: float = 3.0, warmup: int = 10,
                 alpha: float = 0.3) -> None:
        self.sensitivity = sensitivity
        self.warmup = warmup
        self.alpha = alpha
        # (device_id, metric) -> {"mean", "var", "count", "active"}
        self._state: dict[tuple[str, str], dict[str, Any]] = {}

    def evaluate(self, device_id: str,
                 points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """处理一批遥测点，返回新产生的异常列表（含 σ 偏离信息）。"""
        fired: list[dict[str, Any]] = []
        for point in points:
            try:
                value = float(point["value"])
                metric = str(point["metric"])
            except (KeyError, TypeError, ValueError):
                continue
            key = (device_id, metric)
            state = self._state.setdefault(
                key, {"mean": None, "var": 0.0, "count": 0, "active": False})

            if state["mean"] is None:
                state["mean"] = value
                state["count"] = 1
                continue

            std = math.sqrt(state["var"])
            deviation = abs(value - state["mean"])
            is_anomaly = (state["count"] >= self.warmup and std > 1e-9
                          and deviation > self.sensitivity * std)

            if is_anomaly and not state["active"]:
                state["active"] = True
                fired.append({
                    "metric": metric,
                    "value": value,
                    "mean": round(state["mean"], 3),
                    "sigma": round(deviation / std, 1),
                })
            elif not is_anomaly and state["active"]:
                state["active"] = False

            # 判定之后再更新基线：异常点缓慢纳入，避免基线被单点带偏
            alpha = self.alpha
            state["var"] = (1 - alpha) * state["var"] + alpha * (value - state["mean"]) ** 2
            state["mean"] = (1 - alpha) * state["mean"] + alpha * value
            state["count"] += 1
        return fired

    def forget(self, device_id: str) -> None:
        """设备删除后清空其基线状态。"""
        for key in [k for k in self._state if k[0] == device_id]:
            self._state.pop(key, None)
