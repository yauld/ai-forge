# AI Forge Roadmap

这份 Roadmap 用来约束 AI Forge 的整理顺序：先把仓库变成清晰的公共入口，再逐步把历史实验升级成稳定学习单元。

## Phase 1: 仓库门面与结构

- 完成 README、内容地图、发布规范和文章模板。
- 建立 `labs/`、`examples/`、`assets/`、`drafts/` 的长期结构。
- 将旧 `notebooks/` 内容迁移到长期公开结构。

## Phase 2: 专题学习入口

- 在 README 和内容地图中维护 LangChain、LangGraph、RAG、MCP、Skills、Coding 的推荐学习入口。
- 每个专题入口包含学习目标、适合读者、推荐路线和关联实验。
- 优先整理已经成熟、读者价值高、能支撑公众号持续更新的主题。

## Phase 3: 可复现实验

- 将成熟 Notebook 提炼成 `labs/<topic>/<lesson>`。
- 每个实验至少包含 README、运行命令、关键代码入口和示例数据说明。
- 对需要独立运行的服务或脚本，迁移到 `examples/`。
- 迁移时不修改任何已有文章正文和 Notebook 内容。

## Phase 4: 公众号与 GitHub 联动

- 新文章先规划 GitHub 实验页，再发布公众号文章。
- 公众号文章保持短、清晰、有判断。
- GitHub 页面承担完整代码、截图、Notebook、运行说明和延伸阅读。

## Phase 5: 品牌化与长期维护

- 持续完善 `yauld/ai-forge` 的 About、Topics、README 和专题入口。
- 为高价值专题补充封面图、架构图和稳定示例。
- 持续把迁移后的基础内容拆分为更细的稳定实验单元。
