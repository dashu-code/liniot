<!-- 提交前请确认以下事项 -->

## 变更说明

<!-- 做了什么、为什么（关联 Issue：fixes #123） -->

## 变更类型

- [ ] 新功能（feat）
- [ ] 修复（fix）
- [ ] 文档（docs）
- [ ] 重构（refactor）
- [ ] 测试（test）
- [ ] 构建/CI（build）

## 自查清单

- [ ] `pytest -v` 全部通过，新功能/修复附带测试
- [ ] 涉及 API / MQTT 协议变更时已同步 `docs/api.md` / `docs/mqtt-protocol.md`
- [ ] 涉及用户可见变更时已更新 `CHANGELOG.md`
- [ ] 前端改动通过 `node --check web/app.js`，保持零构建、零 npm 依赖
