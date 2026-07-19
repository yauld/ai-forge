# 08 | LangGraph Runtime Context：尽量别把运行配置塞进State

刚开始搞LangGraph时的确很容易把所有东西都无脑塞进State

- 用户输入，放State。
- 中间结果，放State。
- 工具返回，放State。
- 模型配置、环境配置、用户身份。。。，这些也顺手放State。

这样是省事了，state里啥都有了，节点想用什么就拿什么，像点读笔，哪里不会点哪里？

但其实，同一张LangGraph图在不同运行场景下可能需要一些“外部配置”，但最好不要把他们都混进图的业务State里，而应该通过Runtime Context注入到graph里。

用一个CI/CD发布流水线的例子说一下这个事的逻辑。

## 1. 先看一个demo发布流水线

假设我们用LangGraph编排一个发布流程：

```text
run_tests
  ↓
security_scan
  ↓
build_image
  ↓
deploy
  ↓
write_release_note
```

这个流程里有两类信息。

第一类，是这次发布任务本身的进展和结果，比如

```text
commit_sha：这次发布哪个代码提交
test_result：测试是否通过
security_scan_result：安全扫描结果
image_tag：构建出来的镜像
deploy_status：部署状态
error_message：失败原因
release_note：发布摘要
```

这些适合放State

因为它们描述的是这次发布已经发生了啥，流程中断后恢复，也需要知道测试过没有、镜像构建到哪里、部署成功还是失败。

第二类，是这次运行时的外部配置，比如可能会存在

```text
target_env：发布到staging还是prod
runner_id：哪台CI runner在执行
docker_registry：镜像推到哪个仓库
kube_context：连哪个Kubernetes集群
current_operator：谁触发或批准发布
dry_run：是否只演练，不真实部署
```

而第二类的这些，就是我上面说的“外部配置”了，就是他们更适合放Runtime Context里

## 2. State和Runtime Context有啥区别，字段应该咋放

原则：

1、State放记录任务事实的东西

2、Runtime Context放提供运行条件的东西

如果这个字段负责的是：这次任务已经发生了什么？那它大概率是State。

如果这个字段负责的是：这次运行应该在什么环境下，怎么执行？那它大概率是Runtime Context。

而，实际分类的时候，哪些变量放state，哪些放runtime context里，还是要根据业务属性做具体判断（无非是多调试几次的事）

## 3. 代码里怎么写

比如我们这个ci/cd的案例中，State只放发布任务相关字段：

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

然后用一个Runtime Context单独声明下面这些

```python
class DeployContext(TypedDict):
    target_env: Literal["dev", "staging", "prod"]
    runner_id: str
    docker_registry: str
    kube_context: str
    current_operator: str
    dry_run: bool
```

创建图时，要手动把Context结构声明给LangGraph，就是context_schema=DeployContext这句

```python
graph_builder = StateGraph(
    DeployState,
    context_schema=DeployContext,
)
```

调用图时，State和Context分开传

```python
initial_state = {
    "commit_sha": "abc123",
    "change_summary": "修复登录接口超时，并补充异常处理日志",
    "deploy_status": "pending",
    "audit_log": [],
}

prod_context = {
    "target_env": "prod",
    "runner_id": "github-runner-07",
    "docker_registry": "registry.company.local",
    "kube_context": "prod-cluster",
    "current_operator": "alice",
    "dry_run": False,
}

result = graph.invoke(initial_state, context=prod_context)
```

然后，context传进去了，在哪里用？

答案是：在需要运行配置的节点里，通过runtime.context读取。

## 4. Context到底在哪里被用到

比如build_image节点：

```python
def build_image(state: DeployState, runtime: Runtime[DeployContext]) -> DeployState:
    context = runtime.context

    image_tag = f"{context['docker_registry']}/demo-api:{state['commit_sha']}"

    return {
        "image_tag": image_tag,
    }
```
1、先在build_image节点里通过runtime: Runtime[DeployContext]接收，然后把runtime.context给变量context

2、state["commit_sha"]：从state里取出我要发布哪个commit

3、context["docker_registry"]：从context里取出这次运行要推到哪个镜像仓库

4、image_tag：构建节点产生的新结果，写回State


再比如deploy节点也用到了runtime context

```python
def deploy(state: DeployState, runtime: Runtime[DeployContext]) -> DeployState:
    context = runtime.context

    if context["dry_run"]:
        return {
            "deploy_status": "skipped",
            "error_message": "dry_run=true，本次没有执行真实部署",
        }

    return {
        "deploy_status": "success",
    }
```

这个节点主要用了Runtime Context里的dry_run，决定是否发起真实的部署。

如果传入的是staging dry-run：

```python
staging_context = {
    "target_env": "staging",
    "docker_registry": "test-registry.company.local",
    "kube_context": "staging-cluster",
    "dry_run": True,
    ...
}
```

最终状态会是

```text
image_tag: test-registry.company.local/demo-api:abc123
deploy_status: skipped
error_message: dry_run=true，本次没有执行真实部署
```

如果传入的是prod

```python
prod_context = {
    "target_env": "prod",
    "docker_registry": "registry.company.local",
    "kube_context": "prod-cluster",
    "dry_run": False,
    ...
}
```

最终状态会是

```text
image_tag: registry.company.local/demo-api:abc123
deploy_status: success
```

到这里就会发现了，同一个commit，同一张图，换了Runtime Context，运行行为就变了！

## 5. 下一步，cicd真实发布系统怎么衔接上

> 是不是LangGraph输出某个字段，然后外部系统看到这个字段就自动部署？

不是

真实部署大多不是由某个State字段自动触发的，真正触发外部部署系统的是节点函数里的代码。

也就是deploy节点里可以调用Kubernetes API、Argo CD API、Jenkins API、GitHub Actions API，或者你们公司内部自研的发布平台API，等等吧。

这个是具体部署相关的，这里主要讲大致逻辑，细节不展开。

---
具体实验内容

```text
GitHub 仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/langgraph/foundations/22 | LangGraph Runtime Context：不要把配置塞进 State.md
```

实验代码：
```text
labs/langgraph/foundations/experiments/22_runtime_context_cicd/
```
