---
title: LangGraph Runtime Context：不要把配置塞进 State
date: 2026-07-19
tags:
  - LangGraph
  - Runtime Context
  - State
  - Ollama
summary: "用一个 CI/CD 发布流水线实验说明 State 与 Runtime Context 的职责边界：State 记录任务进展，Runtime Context 注入本次运行配置。"
---

# LangGraph Runtime Context：不要把配置塞进 State

这篇实验回答一个很容易在工程里写乱的问题：

```text
哪些信息应该放进 State？
哪些信息应该作为 Runtime Context 传给这次运行？
```

我们用一个 CI/CD 发布流水线做例子。它不是为了真正部署 Kubernetes 服务，而是为了把 State 和 Runtime Context 的边界看清楚。

实验里的流程是：

```text
run_tests
 -> security_scan
 -> build_image
 -> deploy
 -> write_release_note
```

同一张图会跑两次：

```text
第一次：staging dry-run，只演练，不真实部署
第二次：prod real deploy，走真实发布分支
```

这两次使用同一个初始 State，但传入不同的 Runtime Context。最后观察：运行行为变了，但 Runtime Context 里的配置字段不会混进最终 State。

## 1. 实验目标

配套代码在：

```text
labs/langgraph/foundations/experiments/22_runtime_context_cicd/main.py
```

当前项目实测使用：

```text
langgraph==1.2.0
langchain-ollama==1.1.0
```

模型固定使用本地 Ollama 的 `qwen3-coder:30b`。模型只在最后根据最终 State 生成一段发布摘要，不负责决定是否发布。

运行前需要确认本地 Ollama 已启动，并且模型已拉取：

```bash
ollama list
ollama pull qwen3-coder:30b
```

从仓库根目录运行：

```bash
uv run labs/langgraph/foundations/experiments/22_runtime_context_cicd/main.py
```

这篇实验的验收目标很明确：

1. 能说清 State 和 Runtime Context 分别保存什么。
2. 能指出 context 是在 `graph.invoke(..., context=...)` 传入，并在节点里通过 `runtime.context` 读取。
3. 能观察到同一份初始 State 在不同 context 下得到不同运行行为。
4. 能确认 Runtime Context 字段没有进入最终 State。

## 2. 先看业务场景

一个发布流水线通常会关心两类信息。

第一类是发布任务本身：

```text
这次发布哪个 commit？
测试是否通过？
安全扫描结果是什么？
构建出的镜像是什么？
部署结果是什么？
失败原因是什么？
```

这些信息描述“这次发布任务已经发生了什么”，适合放进 State。因为它们会随着图执行逐步更新，也适合被 checkpoint 保存下来。

第二类是这次运行时的外部条件：

```text
这次发布到 staging 还是 prod？
当前是哪台 runner 执行？
镜像推到哪个 registry？
kubectl 或发布平台连接哪个集群？
当前操作人是谁？
这次是不是 dry-run？
```

这些信息影响节点怎么执行，但它们不是发布任务的执行结果。它们更像“本次调用的环境和身份配置”，适合放进 Runtime Context。

可以先记住这个判断：

```text
State：任务进展和执行结果。
Runtime Context：本次运行的环境、身份和配置。
```

## 3. State 只描述发布任务本身

实验里的 State 定义如下：

```python
class DeployState(TypedDict, total=False):
    commit_sha: str
    change_summary: str
    test_result: Literal["passed", "failed"]
    security_scan_result: str
    image_tag: str
    deploy_status: Literal["pending", "success", "failed", "skipped"]
    error_message: str
    release_note: str
    audit_log: list[str]
```

这里的字段都和“发布任务本身”有关。

`commit_sha` 是本次要处理的代码提交。`test_result` 是测试节点跑出来的结果。`security_scan_result` 是安全扫描节点跑出来的结果。`image_tag` 是构建节点产出的镜像。`deploy_status` 是部署节点写回的部署状态。

这些字段的共同点是：

```text
它们要么是任务输入，要么是节点执行后的产物。
```

所以它们应该进入 State。

实验一开始的初始 State 很小：

```python
initial_state = {
    "commit_sha": "abc123",
    "change_summary": "修复登录接口超时，并补充异常处理日志",
    "deploy_status": "pending",
    "audit_log": [],
}
```

后续节点会逐步补充测试结果、扫描结果、镜像地址、部署状态和发布摘要。

## 4. Runtime Context 描述本次运行环境

Runtime Context 的结构单独声明：

```python
class DeployContext(TypedDict):
    target_env: Literal["dev", "staging", "prod"]
    runner_id: str
    docker_registry: str
    kube_context: str
    current_operator: str
    dry_run: bool
```

这些字段不描述发布任务“已经做到哪一步”，而是描述“这次怎么运行”。

例如：

- `target_env` 表示这次发布目标是 dev、staging 还是 prod。
- `runner_id` 表示当前由哪台 CI runner 执行。
- `docker_registry` 表示镜像要写入哪个镜像仓库。
- `kube_context` 表示部署动作应该面向哪个 Kubernetes 集群。
- `current_operator` 表示当前触发或批准发布的人。
- `dry_run` 表示这次是否只演练，不执行真实发布分支。

图创建时用 `context_schema` 告诉 LangGraph：这张图运行时可以接收这样的 context。

```python
graph_builder = StateGraph(DeployState, context_schema=DeployContext)
```

这一步只是声明结构。真正传入 context，是在调用图的时候。

## 5. 同一个 State，传入两个 context

实验里准备了两个 Runtime Context。

第一个是 staging dry-run：

```python
staging_context = {
    "target_env": "staging",
    "runner_id": "github-runner-02",
    "docker_registry": "test-registry.company.local",
    "kube_context": "staging-cluster",
    "current_operator": "bob",
    "dry_run": True,
}
```

第二个是 prod real deploy：

```python
prod_context = {
    "target_env": "prod",
    "runner_id": "github-runner-07",
    "docker_registry": "registry.company.local",
    "kube_context": "prod-cluster",
    "current_operator": "alice",
    "dry_run": False,
}
```

调用时，两次传入的是同一个 `initial_state`：

```python
staging_result = graph.invoke(initial_state, context=staging_context)
prod_result = graph.invoke(initial_state, context=prod_context)
```

这里要注意一件事：`context=...` 不是 State 更新。它不会把 `target_env`、`runner_id` 这些字段塞进 State。

LangGraph 会把传入的 context 放到节点可读取的 runtime 对象里。节点如果需要读取运行时配置，就在函数参数里接收 `runtime`：

```python
def build_image(state: DeployState, runtime: Runtime[DeployContext]) -> DeployState:
    context = runtime.context
```

这就是 context 被使用的地方。

## 6. build_image 如何使用 context

构建镜像节点既需要 State，也需要 Runtime Context。

它从 State 里读取 commit：

```python
state["commit_sha"]
```

它从 Runtime Context 里读取镜像仓库：

```python
context["docker_registry"]
```

然后组合出镜像地址：

```python
image_tag = f"{context['docker_registry']}/demo-api:{state['commit_sha']}"
```

这段代码背后的职责边界很清楚：

```text
commit_sha 来自 State：我要发布哪个代码提交。
docker_registry 来自 Runtime Context：这次运行要把镜像推到哪个仓库。
image_tag 写回 State：构建节点产出的发布产物。
```

所以 staging dry-run 会得到：

```text
test-registry.company.local/demo-api:abc123
```

prod real deploy 会得到：

```text
registry.company.local/demo-api:abc123
```

同一个 commit，因为 context 不同，构建产物地址不同。

但最终 State 里只保存构建出来的 `image_tag`，不会保存完整的 context 配置。

## 7. deploy 如何使用 context

部署节点也同时读取 State 和 Runtime Context。

它从 State 里读取要部署的镜像：

```python
state["image_tag"]
```

它从 Runtime Context 里读取发布环境、集群和 dry-run 开关：

```python
context["target_env"]
context["kube_context"]
context["dry_run"]
```

核心判断是：

```python
if context["dry_run"]:
    return {
        "deploy_status": "skipped",
        "error_message": "dry_run=true，本次没有执行真实部署",
    }
```

如果 `dry_run=True`，这次运行只演练，不进入真实部署分支。节点把结果写回 State：

```text
deploy_status = skipped
error_message = dry_run=true，本次没有执行真实部署
```

如果 `dry_run=False`，节点进入真实发布分支：

```python
return {
    "deploy_status": "success",
}
```

本实验为了安全和可复现，没有真的调用 Kubernetes、Argo CD 或公司发布平台。真实业务里，部署节点通常会在这里调用外部系统：

```python
result = release_platform.create_release(
    image_tag=state["image_tag"],
    environment=context["target_env"],
    operator=context["current_operator"],
)
```

然后把外部系统返回的结果写回 State：

```python
return {
    "deploy_status": result.status,
    "release_id": result.release_id,
    "error_message": result.error_message,
}
```

也就是说，真正触发外部系统的是节点函数里的代码。State 和 Runtime Context 只是给这个节点提供输入。

## 8. 运行并观察结果

运行脚本：

```bash
uv run labs/langgraph/foundations/experiments/22_runtime_context_cicd/main.py
```

第一次运行使用 staging dry-run context，关键输出如下：

```text
同一个初始 State，第一次使用 staging dry-run Runtime Context
[run_tests] 测试 commit: abc123
[security_scan] 扫描依赖和镜像风险
[build_image] runner: github-runner-02
[build_image] 镜像: test-registry.company.local/demo-api:abc123
[deploy] dry_run=true，只演练发布到 staging
[write_release_note] 调用本地 Ollama：qwen3-coder:30b
```

最终 State 的关键部分：

```text
commit_sha: abc123
test_result: passed
security_scan_result: 未发现阻断发布的高危问题
image_tag: test-registry.company.local/demo-api:abc123
deploy_status: skipped
error_message: dry_run=true，本次没有执行真实部署
Runtime Context 字段是否进入最终 State？
泄漏字段: 无
```

这说明 staging dry-run 的语义是：

```text
测试通过，扫描通过，镜像已构建，但部署动作被跳过。
```

后续业务系统可以把它标记为“演练完成”，展示给研发或测试人员，并允许进入正式发布审批。

第二次运行使用 prod context，关键输出如下：

```text
同一个初始 State，第二次使用 prod Runtime Context
[run_tests] 测试 commit: abc123
[security_scan] 扫描依赖和镜像风险
[build_image] runner: github-runner-07
[build_image] 镜像: registry.company.local/demo-api:abc123
[deploy] 发布到环境: prod
[deploy] Kubernetes 集群: prod-cluster
[deploy] 操作人: alice
[write_release_note] 调用本地 Ollama：qwen3-coder:30b
```

最终 State 的关键部分：

```text
commit_sha: abc123
test_result: passed
security_scan_result: 未发现阻断发布的高危问题
image_tag: registry.company.local/demo-api:abc123
deploy_status: success
Runtime Context 字段是否进入最终 State？
泄漏字段: 无
```

这说明 prod context 改变了部署节点的行为：它不再跳过部署，而是进入成功发布分支。

真实业务系统拿到这个 State 后，通常会继续做这些事：

```text
更新发布任务状态
记录线上版本
写入审计日志
通知团队
启动发布后监控
必要时触发回滚图
```

这些后续动作通常在 LangGraph 外层业务系统里完成，或者继续由下一张图编排。

## 9. 为什么不要把配置塞进 State

假设把配置也塞进 State，初始输入可能变成这样：

```python
initial_state = {
    "commit_sha": "abc123",
    "deploy_status": "pending",
    "target_env": "staging",
    "docker_registry": "test-registry.company.local",
    "kube_context": "staging-cluster",
    "dry_run": True,
}
```

短期看，这样也能跑。但问题是 State 会被当成图内状态持续传递，甚至可能被 checkpoint 保存和恢复。

这会带来几个麻烦：

第一，业务状态和运行配置混在一起。读 State 时很难判断哪些字段是节点应该更新的结果，哪些字段只是本次调用的外部条件。

第二，恢复历史执行时可能恢复出旧配置。比如某次 staging dry-run 的 checkpoint 里保存了 `dry_run=True` 和 `staging-cluster`，后来你想用 prod 配置继续处理同一个 commit，就容易出现旧配置污染新运行的问题。

第三，同一张图复用能力变差。同一张发布图应该能在 staging、prod、dry-run、真实发布之间切换。如果这些差异都写进 State，图的输入会变得又重又混乱。

所以更清楚的做法是：

```text
State 保存任务事实：
commit、测试结果、扫描结果、镜像、部署状态。

Runtime Context 保存运行条件：
环境、runner、registry、集群、操作人、dry-run。
```

## 10. 小结

这篇实验的核心不是 CI/CD，而是 LangGraph 的状态边界。

`graph.invoke(initial_state, context=...)` 里的 context 会进入运行时对象。节点函数如果声明了 `runtime: Runtime[DeployContext]`，就可以通过 `runtime.context` 读取这些运行配置。

但 Runtime Context 不会自动写入 State。只有节点返回的字典才会更新 State。

用一句话收束：

```text
State 记录这次任务已经发生了什么；
Runtime Context 告诉这次运行应该在什么环境、用什么身份、按什么配置执行。
```

完成实验后，应该能说清楚三件事：

1. `commit_sha`、`test_result`、`image_tag`、`deploy_status` 这类任务事实应该放 State。
2. `target_env`、`runner_id`、`docker_registry`、`kube_context`、`dry_run` 这类运行配置应该放 Runtime Context。
3. 真实外部系统调用发生在节点函数里，调用结果再写回 State，而不是由某个 State 字段自动触发。

