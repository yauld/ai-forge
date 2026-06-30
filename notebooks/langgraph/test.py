#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 1.x 生产级完整示例

演示功能：
1. Checkpoint (检查点) - 状态持久化
2. Durable Execution (持久化执行) - 断点续传
3. Human-in-the-loop (人工干预) - 关键节点人工审核
4. Production-grade Routing (生产级路由) - LLM 决策逻辑
"""

from typing import TypedDict, List, Literal, Dict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
import os


# ==========================================
# 第一部分：定义状态结构 (State Definition)
# ==========================================

class AgentState(MessagesState):
    """
    消息状态继承自 LangGraph 的 MessagesState
    添加自定义字段用于控制流程
    """
    should_review: bool = False  # 是否需要人工审核
    review_notes: str = ""       # 审核备注
    approval_status: str = ""    # 审批状态


# ==========================================
# 第二部分：路由函数 (Router Function)
# ==========================================

def should_intervene(state: AgentState) -> Literal["review", "continue"]:
    """
    生产级路由逻辑 - 基于用户输入内容决定是否需人工审核
    
    Args:
        state: 当前图状态
        
    Returns:
        "review" 或 "continue" 字符串，对应节点名称
    """
    last_message = state["messages"][-1] if state["messages"] else None
    
    if not last_message:
        return "continue"
    
    content = last_message.content.lower()
    
    # 定义触发人工审核的条件
    sensitive_keywords = ["转账", "支付", "敏感信息", "个人隐私"]
    
    for keyword in sensitive_keywords:
        if keyword in content:
            print(f"🔍 检测到敏感内容，触发人工审核：{keyword}")
            return "review"
    
    # 检查消息数量是否超过阈值（防无限循环）
    if len(state["messages"]) > 10:
        print("⚠️ 消息过多，自动继续")
        return "continue"
    
    print(f"✅ 正常流程，无需审核")
    return "continue"


# ==========================================
# 第三部分：节点定义 (Node Definition)
# ==========================================

def agent_node(state: AgentState):
    """模拟 AI 代理节点"""
    
    # 确保 messages 列表不为空，并处理 None 情况
    if not state.get("messages"):
        last_message = None
    else:
        last_message = state["messages"][-1]

    # 安全的字符串访问方法（防止 print 报错）
    message_preview = last_message.content[:30] if last_message else "No messages"
    
    print(f"\n🤖 [Agent Node] 处理请求：{message_preview}...")
    
    response_msg = SystemMessage(
        content="根据您的要求，我已完成任务。请审核下一步操作。"
    )
    
    return {
        "messages": state["messages"] + [response_msg],
        "should_review": True,
    }



def reviewer_node(state: AgentState):
    """模拟人工审核节点 - 此处会暂停等待干预"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    print(f"\n👤 [Reviewer Node] 等待人工审核：{last_message.content[:30]}...")
    
    # 【关键】在这里暂停，等待人工介入
    # 返回 Command 触发中断机制
    return {
        "should_review": False,  # 重置标记
    }


def finalize_node(state: AgentState):
    """最终节点 - 完成所有任务"""
    last_message = state["messages"][-1] if state["messages"] else None
    
    print(f"\n✅ [Finalize Node] 完成所有流程")
    
    response_msg = SystemMessage(
        content="任务已完成，流程结束。"
    )
    
    return {
        "messages": state["messages"] + [response_msg],
    }


# ==========================================
# 第四部分：构建图 (Graph Building)
# ==========================================

def build_graph(checkpointer):
    """
    生产级 LangGraph 构建函数
    
    Args:
        checkpointer: CheckpointSaver实例，如 MemorySaver()
        
    Returns:
        编译好的 StateGraph实例
    """
    workflow = StateGraph(AgentState)
    
    # 添加所有节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("finalize", finalize_node)
    
    # 设置入口点
    workflow.set_entry_point("agent")
    
    # 【关键】配置条件边（路由）
    workflow.add_conditional_edges(
        "agent",
        should_intervene,  # 路由函数引用，非 Lambda
        {
            "review": "reviewer",
            "continue": "finalize"
        }
    )
    
    # 【关键】配置从reviewer节点出发的边
    # 这里演示如何从中断点恢复
    workflow.add_edge("reviewer", "finalize")
    workflow.add_edge("finalize", END)
    
    # 【核心】编译图时传入 checkpointer，启用 Durable Execution
    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["reviewer"]  # 在 reviewer 节点前暂停（人工审核）
    )
    
    return compiled_graph


# ==========================================
# 第五部分：主流程演示 (Main Demo)
# ==========================================

def run_production_example():
    """完整生产级示例主流程"""
    
    print("="*80)
    print("🚀 LangGraph 1.x 生产级示例")
    print("="*80)
    
    # 创建检查点存储（内存版，生产可用Postgres/Sqlite）
    checkpointer = MemorySaver()
    
    # 构建图实例
    graph = build_graph(checkpointer)
    
    # 线程ID配置 - Checkpoint的关键标识
    thread_config = {"configurable": {"thread_id": "user_chat_001"}}
    
    print(f"\n📍 线程ID：{thread_config['configurable']['thread_id']}")
    
    try:
        # ============================
        # 第一次运行：包含人工干预模拟
        # ============================
        print("\n" + "─"*80)
        print("🔄 [第一次运行] - 完整流程，触发人工审核")
        print("─"*80)
        
        initial_input = {
            "messages": [HumanMessage(content="帮我转账给张三1000元")]
        }
        
        # invoke会因interrupt_before而暂停在reviewer节点前
        result1 = graph.invoke(initial_input, config=thread_config)
        
        print("\n✅ 第一次运行结束")
        print(f"📝 消息数量：{len(result1['messages'])}")
        
    except Exception as e:
        print(f"❌ 运行时错误：{e}")
    
    # ============================
    # 模拟服务重启后恢复执行
    # ============================
    print("\n" + "─"*80)
    print("🔄 [模拟服务重启] - 重建图实例，使用相同thread_id")
    print("─"*80)
    
    # 重新创建 Graph（模拟服务进程重启）
    graph = build_graph(checkpointer)
    
    try:
        # 第二次运行：从上次 Checkpoint 恢复
        continuation_input = {
            "messages": [HumanMessage(content="请继续处理")]
        }
        
        result2 = graph.invoke(continuation_input, config=thread_config)
        
        print("\n✅ 第二次运行完成")
        print(f"📝 消息数量：{len(result2['messages'])}")
        
    except Exception as e:
        print(f"❌ 恢复时错误：{e}")
    
    # ============================
    # 展示 Checkpoint 状态
    # ============================
    print("\n" + "─"*80)
    print("📄 [Checkpointer 状态检查]")
    print("─"*80)
    
    try:
        # 获取所有 checkpoint IDs
        checkpoints = list(checkpointer.list(thread_config))
        print(f"🔹 Checkpoints 数量：{len(list(checkpoints))}")
        
        for check in checkpoints:
            config_id = check.config.get("configurable", {}).get("thread_id")
            state_snapshot = check.state
            print(f"   - Thread ID: {config_id}, Messages Count: {len(state_snapshot['messages'])}")
            
    except Exception as e:
        print(f"⚠️ 无法读取 Checkpoint：{e}")
    
    # ============================
    # 结束清理
    # ============================
    print("\n" + "─"*80)
    print("🎉 示例运行完成")
    print("="*80)


# ==========================================
# 第六部分：进阶 - 带中断的完整流程
# ==========================================

def run_with_interrupt_example():
    """演示更详细的人工干预中断流程"""
    
    print("\n\n" + "="*80)
    print("⚙️ 人工干预中断示例 (Human-in-the-Loop)")
    print("="*80)
    
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer)
    thread_config = {"configurable": {"thread_id": "interrupt_demo_001"}}
    
    # 第一步：请求人工介入（触发中断）
    print("\n🔶 [步骤1] 请求人工审核...")
    
    try:
        response = graph.invoke(
            {"messages": [HumanMessage(content="请审核转账申请")]},
            config=thread_config
        )
        
        print("✅ 请求已暂停，等待人工介入")
        
    except Exception as e:
        # LangGraph v1.x 在 interrupt 处会抛出异常或返回特殊响应
        print(f"⚠️ 中断触发：{type(e).__name__}")
    
    # 模拟人工批准（修改状态）
    print("\n🔶 [步骤2] 人工批准后恢复执行...")
    
    try:
        response = graph.invoke(
            Command(reset=True),  # 如果需要重置状态
            config=thread_config
        )
        
        print("✅ 人工干预完成，流程继续")
        
    except Exception as e:
        print(f"❌ 恢复执行失败：{e}")


# ==========================================
# 主入口
# ==========================================

if __name__ == "__main__":
    run_production_example()
    
    # 可选：运行中断示例
    # run_with_interrupt_example()
