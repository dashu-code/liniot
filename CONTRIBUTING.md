# 贡献指南

感谢关注 LinIoT。以下约定帮助 PR 快速合并。

## 开发环境

```bash
git clone https://github.com/OWNER/liniot.git && cd liniot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v           # 全部通过后再提交
```

启动开发服务（改动自动生效需重启，无热重载依赖）：

```bash
liniot run & liniot simulate
```

## 代码约定

- Python：类型注解覆盖公开函数；docstring 写"为什么"，不写"是什么"；
  遵循现有模块的命名与错误处理风格。
- 前端：保持零构建、零 npm 依赖；ES2019+ 语法（`node --check web/app.js` 可校验）。
- 注释与文档、日志统一中文；标识符用英文。

## 提交约定

- 一个 PR 只做一件事；提交信息用祈使句，如 `fix: 全局规则按设备独立做上升沿判定`。
- 新功能必须带测试；修复必须带能复现原 bug 的回归测试。
- 涉及协议/API 变更时同步更新 `docs/api.md` / `docs/mqtt-protocol.md`。

## 测试清单

- `pytest -v`：存储、规则、服务、API、MQTT 解析、AI、事件总线、模拟器共 40+ 用例。
- 手动冒烟：`liniot run` + `liniot simulate` 后检查概览曲线、灯开关闭环、AI 对话。

## 报告 Issue

请附：启动命令、环境变量（脱敏）、复现步骤、日志片段。功能建议请说明使用场景。
