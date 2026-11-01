# 贡献指南

感谢关注 LinIoT。以下约定帮助 PR 快速合并。**第一次参与？先看
[你的第一个 PR：十分钟上手指南](docs/first-pr.md)**，再回来读流程约定。

## 开发环境

```bash
git clone https://github.com/kevin1779/liniot.git && cd liniot
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

## 认领与协作流程

1. 在 [ROADMAP](ROADMAP.md) 或 Issue 列表挑任务（`good first issue` 标签适合上手）；
2. 在 Issue 下评论认领，避免重复劳动；维护者会把 Issue 指派给你；
3. 从最新 `main` 切分支开发：`git checkout -b feat/xxx`；
4. 提交 PR（模板会引导自查），CI 通过后 48 小时内会有评审回复；
5. 评审意见以代码为准讨论，合并后你的 GitHub 头像会出现在贡献者列表。

标签约定：`bug` / `enhancement` / `good first issue` / `help wanted` /
`documentation` / `wontfix`。

## 发布流程

- 遵循语义化版本：`major.minor.patch`；
- 每次发布：更新 `CHANGELOG.md` → 打 `vX.Y.Z` tag → GitHub Release 附变更说明；
- 破坏性变更提前一个版本在 Issue 公示讨论。

## 测试清单

- `pytest -v`：存储、规则、服务、API、MQTT 解析、AI、事件总线、模拟器、异常检测、场景联动共 57 用例。
- 手动冒烟：`liniot run` + `liniot simulate` 后检查概览曲线、灯开关闭环、AI 对话。

## 报告 Issue

请附：启动命令、环境变量（脱敏）、复现步骤、日志片段。功能建议请说明使用场景。
