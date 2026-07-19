from typing import Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


MODEL_NAME = "qwen3-coder:30b"


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


class DeployContext(TypedDict):
    target_env: Literal["dev", "staging", "prod"]
    runner_id: str
    docker_registry: str
    kube_context: str
    current_operator: str
    dry_run: bool


def run_tests(state: DeployState) -> DeployState:
    audit_log = state.get("audit_log", [])
    commit_sha = state["commit_sha"]

    print(f"[run_tests] 测试 commit: {commit_sha}")

    return {
        "test_result": "passed",
        "audit_log": audit_log + [f"测试通过：{commit_sha}"],
    }


def security_scan(state: DeployState) -> DeployState:
    audit_log = state.get("audit_log", [])

    print("[security_scan] 扫描依赖和镜像风险")

    return {
        "security_scan_result": "未发现阻断发布的高危问题",
        "audit_log": audit_log + ["安全扫描通过"],
    }


def build_image(state: DeployState, runtime: Runtime[DeployContext]) -> DeployState:
    context = runtime.context
    audit_log = state.get("audit_log", [])

    image_tag = f"{context['docker_registry']}/demo-api:{state['commit_sha']}" # type: ignore

    print(f"[build_image] runner: {context['runner_id']}")
    print(f"[build_image] 镜像: {image_tag}")

    return {
        "image_tag": image_tag,
        "audit_log": audit_log + [f"构建镜像：{image_tag}"],
    }


def deploy(state: DeployState, runtime: Runtime[DeployContext]) -> DeployState:
    context = runtime.context
    audit_log = state.get("audit_log", [])

    if context["dry_run"]:
        print(f"[deploy] dry_run=true，只演练发布到 {context['target_env']}")

        return {
            "deploy_status": "skipped",
            "error_message": "dry_run=true，本次没有执行真实部署",
            "audit_log": audit_log + [
                f"演练部署：{context['target_env']} / {context['kube_context']}"
            ],
        }

    print(f"[deploy] 发布到环境: {context['target_env']}")
    print(f"[deploy] Kubernetes 集群: {context['kube_context']}")
    print(f"[deploy] 操作人: {context['current_operator']}")

    return {
        "deploy_status": "success",
        "audit_log": audit_log + [
            f"真实部署：{context['target_env']} / {context['kube_context']}"
        ],
    }


def write_release_note(state: DeployState) -> DeployState:
    print(f"[write_release_note] 调用本地 Ollama：{MODEL_NAME}")

    model = ChatOllama(model=MODEL_NAME, temperature=0)
    prompt = f"""
你是 CI/CD 发布助手。请根据下面的发布 State 写一段简短中文发布摘要。

要求：
- 只基于 State，不要编造运行环境配置。
- 说明 commit、测试结果、扫描结果、镜像、部署状态。
- 控制在 80 字以内。

State:
commit_sha: {state.get("commit_sha")}
change_summary: {state.get("change_summary")}
test_result: {state.get("test_result")}
security_scan_result: {state.get("security_scan_result")}
image_tag: {state.get("image_tag")}
deploy_status: {state.get("deploy_status")}
error_message: {state.get("error_message", "")}
"""

    response = model.invoke(prompt)

    return {
        "release_note": response.content.strip(), # type: ignore
    }


def build_graph():
    graph_builder = StateGraph(DeployState, context_schema=DeployContext)

    graph_builder.add_node("run_tests", run_tests)
    graph_builder.add_node("security_scan", security_scan)
    graph_builder.add_node("build_image", build_image)
    graph_builder.add_node("deploy", deploy)
    graph_builder.add_node("write_release_note", write_release_note)

    graph_builder.add_edge(START, "run_tests")
    graph_builder.add_edge("run_tests", "security_scan")
    graph_builder.add_edge("security_scan", "build_image")
    graph_builder.add_edge("build_image", "deploy")
    graph_builder.add_edge("deploy", "write_release_note")
    graph_builder.add_edge("write_release_note", END)

    return graph_builder.compile()


def print_final_state(title: str, final_state: DeployState) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

    for key, value in final_state.items():
        print(f"{key}: {value}")

    context_keys = {
        "target_env",
        "runner_id",
        "docker_registry",
        "kube_context",
        "current_operator",
        "dry_run",
    }
    leaked_keys = sorted(context_keys.intersection(final_state.keys()))

    print("\nRuntime Context 字段是否进入最终 State？")
    print(f"泄漏字段: {leaked_keys if leaked_keys else '无'}")


def main() -> None:
    graph = build_graph()

    initial_state = {
        "commit_sha": "abc123",
        "change_summary": "修复登录接口超时，并补充异常处理日志",
        "deploy_status": "pending",
        "audit_log": [],
    }

    staging_context = {
        "target_env": "staging",
        "runner_id": "github-runner-02",
        "docker_registry": "test-registry.company.local",
        "kube_context": "staging-cluster",
        "current_operator": "bob",
        "dry_run": True,
    }

    prod_context = {
        "target_env": "prod",
        "runner_id": "github-runner-07",
        "docker_registry": "registry.company.local",
        "kube_context": "prod-cluster",
        "current_operator": "alice",
        "dry_run": False,
    }

    print("\n同一个初始 State，第一次使用 staging dry-run Runtime Context")
    staging_result = graph.invoke(initial_state, context=staging_context) # type: ignore
    print_final_state("第一次运行结果：staging dry-run", staging_result) # type: ignore

    print("\n同一个初始 State，第二次使用 prod Runtime Context")
    prod_result = graph.invoke(initial_state, context=prod_context) # type: ignore
    print_final_state("第二次运行结果：prod real deploy", prod_result) # type: ignore


if __name__ == "__main__":
    main()
