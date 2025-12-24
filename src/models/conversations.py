from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

class Conversation(Base):
    """用户会话表 - 存储对话元数据"""
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, index=True)
    
    # 归属权隔离 (核心字段)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 会话元数据
    title = Column(String(255), nullable=True)  # 自动生成的标题
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # 状态管理
    is_archived = Column(Boolean, default=False)  # 归档而非物理删除
    is_starred = Column(Boolean, default=False)   # 收藏/置顶
    
    # 上下文/配置 (重要)
    # 存储该会话特定的配置，如 override_model, temperature, focused_files 等
    metadata_ = Column("metadata", JSON, default={}) 
    
    # 状态持久化 (Deps State)
    # 存储 DeepAgentDeps 中的易变状态，如 todos, subagent_state
    # 格式: {"todos": [...], "subagents": {...}, "uploads": {...}}
    state = Column(JSON, default={})
    
    # 关联
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.step_order")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class Message(Base):
    """消息历史表 - 存储具体对话内容
    
    设计目标：兼容 PydanticAI 的消息结构 (ModelRequest, ModelResponse, ToolReturn)
    """
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, index=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id"), nullable=False, index=True)
    
    # 消息顺序 (非常重要，用于重组历史)
    step_order = Column(Integer, nullable=False, index=True)
    
    # 角色类型: 'system', 'user', 'model' (assistant), 'tool-return'
    role = Column(String(20), nullable=False)
    
    # 核心内容
    content = Column(Text, nullable=True)  # 文本内容
    
    # 工具调用相关 (PydanticAI 特性)
    # 如果 role='model'，这里存工具调用列表 [{"name": "read_file", "args": {...}}]
    tool_calls = Column(JSON, nullable=True)
    
    # 工具返回相关
    # 如果 role='tool-return'，这里存工具执行结果
    tool_return_content = Column(Text, nullable=True) # 序列化后的结果
    tool_name = Column(String(100), nullable=True)    # 哪个工具返回的
    tool_call_id = Column(String(100), nullable=True) # 对应哪个调用ID
    
    # 审计/元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    token_count = Column(Integer, nullable=True)  # 该条消息消耗的token (可选)
    
    # 关联
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', order={self.step_order})>"
