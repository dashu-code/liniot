# 你的第一个 PR：十分钟上手指南

这份指南面向第一次参与 LinIoT 的贡献者。全程不需要任何 IoT 硬件，
跟着命令复制粘贴即可。卡住了随时在 Issue 里 @ 维护者。

## 第 0 步：认领任务（1 分钟）

打开 [Issue 列表](https://github.com/kevin1779/liniot/issues)，挑一个
**good first issue** 标签的任务，在 Issue 下评论「认领 + 我的 GitHub ID」，
维护者会指派给你。当前适合上手的：

| Issue | 内容 | 预计用时 |
|---|---|---|
| #1 暗色主题 | 抽取 CSS 变量为双主题 + 切换按钮 | 1–2 小时 |
| #2 CSV 导出 | 流式导出接口 + 详情页导出按钮 | 1–2 小时 |
| #3 设备分组 | 注册表单加 group 字段 + 列表过滤 | 1–2 小时 |

## 第 1 步：跑起来（5 分钟）

```bash
git clone https://github.com/kevin1779/liniot.git && cd liniot
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q          # 应显示 57 passed
```

另开两个终端，看到真实效果：

```bash
liniot run         # 平台 → http://127.0.0.1:8000
liniot simulate    # 虚拟设备（曲线开始滚动）
```

## 第 2 步：开发（以 CSV 导出为例）

```bash
git checkout -b feat/csv-export     # 分支名随意，feat/ 或 fix/ 开头即可
# ...写代码...
pytest -q                           # 新功能必须带测试
node --check web/app.js             # 动了前端就跑这个
```

写代码时对照现有风格：中文注释、类型注解、零 npm 依赖。
有拿不准的设计，直接在 Issue 里问，不要自己憋。

## 第 3 步：提交与 PR（3 分钟）

```bash
git add 你的文件          # 明确列出，不要 git add -A
git commit -m "feat: 支持遥测数据 CSV 流式导出"
git push origin feat/csv-export
```

打开 GitHub 会看到分支提示，点 **Compare & pull request**：

- 标题写清做了什么；正文关联 Issue（写 `fixes #2` 可自动关闭）；
- PR 模板的自查清单逐项勾选；
- CI 绿灯 + 维护者 approve 后即合并，你的头像会出现在仓库贡献者列表。

## 常见问题

**测试挂了但不是我改的？** 先 `git pull origin main` 同步最新代码再跑。

**CI 等 CRON？** 不需要，PR 会自动触发，约 1 分钟出结果。

**想做的任务被人认领了？** 换一个，或在原 Issue 下留言协作——
多人合领一个任务也欢迎，大任务可以拆。

**我的改动很小（改错别字）也值得 PR 吗？** 值得，文档类 PR 同样欢迎。
