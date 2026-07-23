"""演示 LangGraph get_stream_writer() 的常见用法。

运行方式：

    uv run python labs/coding/examples/langgraph_get_stream_writer_demo.py

这个脚本只演示一个核心区别：

    writer({...})   -> 发送 custom streaming 事件，不写入 State
    return {...}    -> 写回 State，会出现在 updates 事件里

如果你只想理解 get_stream_writer() 是干什么的，看这个文件就够了。
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph


class ScanState(TypedDict):
    """这张图里流动的共享状态。

    LangGraph 的节点不是互相直接传参，而是围绕同一份 State 读写数据。
    每个节点接收当前 State，并返回要合并回 State 的增量字段。

    这里故意只放 4 个字段，避免例子被业务细节淹没：

    - asset_id：输入资产 ID，图启动时就有。
    - asset_profile：资产画像，由 load_asset_profile 节点写入。
    - exposed_ports：暴露端口，由 check_exposed_ports 节点写入。
    - risk_level：风险等级，由 summarize_risk 节点写入。
    """

    asset_id: str
    asset_profile: str
    exposed_ports: list[int]
    risk_level: str


def load_asset_profile(state: ScanState) -> dict[str, str]:
    """读取资产画像，并把过程进度通过 custom stream 发出去。"""
    # get_stream_writer() 只能在 LangGraph 节点执行期间调用。
    # 它返回一个 writer 函数，用来向当前 graph.stream(...) 调用发送 custom 事件。
    #
    # 你可以把 writer 理解成“当前节点的进度广播器”。
    # 它不是日志库，也不是 State 更新接口。
    writer = get_stream_writer()

    # writer({...}) 发出去的是过程事件。
    #
    # 这条消息只会被 stream_mode="custom" 捕获；
    # 它不会进入最终 State，也不会出现在 updates 事件里。
    #
    # 适合放这里的信息：
    # - 当前进入了哪个阶段；
    # - 正在处理哪个对象；
    # - 前端进度条或审计面板想即时看到的提示。
    writer(
        {
            "stage": "asset",
            "message": f"正在读取资产 {state['asset_id']} 的画像",
        }
    )

    # return {...} 才是真正写回 State 的内容。
    #
    # 这部分会被 LangGraph 合并进共享 State；
    # 如果外层开启 stream_mode="updates"，就能看到：
    #
    # {"load_asset_profile": {"asset_profile": "..."}}
    return {
        "asset_profile": "公网 Web 服务器，承载供应商门户",
    }


def check_exposed_ports(state: ScanState) -> dict[str, list[int]]:
    """模拟端口检查。"""
    # 每个节点都可以调用 get_stream_writer()。
    # 这里再次获取 writer，是为了强调：writer 绑定的是当前正在运行的节点上下文。
    writer = get_stream_writer()

    # 这条 custom 事件表达“正在做什么”，不是“检查结果是什么”。
    # 检查结果应该通过 return 写入 State。
    writer(
        {
            "stage": "exposure",
            "message": "正在检查公网暴露端口",
        }
    )

    # exposed_ports 是业务状态，后续 summarize_risk 节点需要读取它。
    # 所以它应该写入 State，而不是只发 custom 事件。
    return {
        "exposed_ports": [22, 443, 8080],
    }


def summarize_risk(state: ScanState) -> dict[str, str]:
    """根据已写入 State 的字段生成风险等级。"""
    writer = get_stream_writer()

    # 这条 custom 事件适合给人看：图已经进入风险汇总阶段。
    # 它不参与业务判断，也不会被下游节点读取。
    writer(
        {
            "stage": "summary",
            "message": "正在根据资产画像和暴露端口生成风险等级",
        }
    )

    # 这里读取的是前面节点写入 State 的 exposed_ports。
    # 这说明：节点之间真正传递业务数据，靠的是 State。
    #
    # 8080 常被用作调试/管理服务端口。这里用它模拟一个简单规则：
    # 如果公网暴露 8080，就把风险等级标成 high。
    risk_level = "high" if 8080 in state["exposed_ports"] else "medium"

    # risk_level 是后续可能要展示、保存或审计的业务结果，
    # 因此应该 return 写回 State。
    return {
        "risk_level": risk_level,
    }


def build_graph():
    """组装一张最小 LangGraph。

    这张图是线性的：

        START
          -> load_asset_profile
          -> check_exposed_ports
          -> summarize_risk
          -> END

    例子故意不用条件边、工具、LLM 和 checkpoint。
    这里唯一要观察的就是：

    - custom 事件来自 writer({...})
    - updates 事件来自节点 return {...}
    """

    builder = StateGraph(ScanState)

    # add_node 把普通 Python 函数注册成 LangGraph 节点。
    # 节点名会出现在 updates 事件里，例如：
    # {"check_exposed_ports": {"exposed_ports": [22, 443, 8080]}}
    builder.add_node("load_asset_profile", load_asset_profile)
    builder.add_node("check_exposed_ports", check_exposed_ports)
    builder.add_node("summarize_risk", summarize_risk)

    # add_edge 声明节点执行顺序。
    # START 和 END 是 LangGraph 预定义的入口和出口标记。
    builder.add_edge(START, "load_asset_profile")
    builder.add_edge("load_asset_profile", "check_exposed_ports")
    builder.add_edge("check_exposed_ports", "summarize_risk")
    builder.add_edge("summarize_risk", END)

    # compile 后才得到可运行的 graph。
    return builder.compile()


def main() -> None:
    graph = build_graph()

    # 初始 State 必须包含 ScanState 声明的字段。
    # 这里把后续节点会写入的字段先放成空值，方便观察它们如何一步步被更新。
    input_state: ScanState = {
        "asset_id": "asset-prod-supplier-portal-01",
        "asset_profile": "",
        "exposed_ports": [],
        "risk_level": "",
    }

    print("=== 同时观察 custom 事件和 updates 事件 ===\n")

    # graph.stream(...) 会边执行图，边把事件吐出来。
    #
    # stream_mode=["custom", "updates"] 表示我们同时关心两类事件：
    #
    # - custom：节点内部 writer({...}) 主动发出的过程事件；
    # - updates：节点 return {...} 写回 State 后产生的状态更新事件。
    #
    # version="v2" 会把不同 mode 统一成同一种结构：
    #
    # {
    #     "type": "custom" | "updates",
    #     "ns": (...),
    #     "data": ...
    # }
    #
    # 所以外层只要判断 event["type"]，就知道该如何处理 event["data"]。
    for event in graph.stream(
        input_state,
        # stream_mode=["custom", "updates"],
        stream_mode=["custom"],
        version="v2",
    ):
        if event["type"] == "custom":
            # custom 事件的 data 就是节点里 writer({...}) 传入的字典。
            # 它适合驱动进度提示、运行日志、前端状态条等。
            print("[custom 过程事件]")
            print(event["data"])
            print()

        elif event["type"] == "updates":
            # updates 事件的 data 是“节点名 -> 本节点写回的 State 增量”。
            # 它适合调试节点到底修改了哪些状态字段。
            print("[updates 状态更新]")
            print(event["data"])
            print()

    print("=== 对照理解 ===")
    print("writer({...}) 发出的内容只会出现在 custom 事件里。")
    print("return {...} 返回的内容才会写入 State，并出现在 updates 事件里。")


if __name__ == "__main__":
    main()
