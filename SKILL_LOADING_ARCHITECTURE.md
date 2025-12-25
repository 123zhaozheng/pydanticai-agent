# Skill 加载架构详解

## 整体架构概览

你的 Skill 系统采用了**渐进式加载 (Progressive Disclosure)** + **权限过滤 (Permission Filtering)** 的设计，将 Skill 的发现、加载、注入和权限控制分离成多个层次。

## 📁 核心数据结构

### 1. Skill 定义 (TypedDict)
```python
# pydantic_deep/types.py
class Skill(TypedDict):
    name: str                    # Skill 名称
    description: str             # 简短描述
    path: str                    # Skill 目录路径
    tags: list[str]              # 标签
    version: str                 # 版本号
    author: str                  # 作者
    frontmatter_loaded: bool     # 是否只加载了 frontmatter
    instructions: NotRequired[str]     # 完整指令（按需加载）
    resources: NotRequired[list[str]]  # 附加资源文件列表
```

### 2. Skill 文件结构
```
~/.pydantic-deep/skills/code_review/
├── SKILL.md              # 主文件（YAML frontmatter + Markdown 指令）
├── checklist.md          # 资源文件 1
└── review_template.txt   # 资源文件 2
```

### 3. SKILL.md 格式
```markdown
---
name: code_review
description: Automated code review assistant
version: 1.2.0
author: team@example.com
tags:
  - code
  - review
  - quality
---

# Code Review Skill

This skill helps you perform thorough code reviews...

## Usage
1. Load the skill using `load_skill("code_review")`
2. Follow the checklist in resources
...
```

---

## 🔄 完整加载流程

### 阶段 1: Agent 初始化时（启动时加载）

```
create_deep_agent()
    ├─> 参数: skill_directories=[{"path": "~/.pydantic-deep/skills", "recursive": True}]
    │
    ├─> [agent.py:254-277] 处理 skills
    │   │
    │   ├─> discover_skills(skill_directories)  # 扫描文件系统
    │   │   │
    │   │   └─> [skills.py:95-155]
    │   │       ├─> 遍历目录，查找 **/SKILL.md
    │   │       ├─> 解析每个 SKILL.md 的 YAML frontmatter
    │   │       ├─> **仅保存元数据**（name, description, tags, version）
    │   │       ├─> **不加载完整 instructions**（节省内存）
    │   │       └─> 返回 List[Skill] 元数据列表
    │   │
    │   ├─> create_skills_toolset(skills=initial_skills)
    │   │   └─> 创建 3 个工具：list_skills, load_skill, read_skill_resource
    │   │
    │   └─> loaded_skills = initial_skills  # 保存用于系统提示词
    │
    ├─> @agent.instructions 动态系统提示词
    │   └─> [agent.py:380-397] get_skills_system_prompt()
    │       │
    │       ├─> 如果 enable_permission_filtering=True:
    │       │   └─> filter_skills_by_permission(loaded_skills, user_id)
    │       │       └─> 根据用户权限过滤可见 skills
    │       │
    │       └─> [skills.py:178-207] 生成系统提示词:
    │           ## 可用技能
    │           - **code_review** [code, review]: Automated code review
    │           - **data_analysis** [data, python]: Data analysis toolkit
```

### 阶段 2: Agent 运行时（对话中）

#### 2.1 用户查看 Skill 列表

```
用户: "显示可用的 skills"
    ↓
Agent 调用工具: list_skills()
    ↓
[skills.py:245-290] list_skills 实现:
    ├─> 从 _skills_cache 读取（启动时加载的元数据）
    │
    ├─> 如果 user_id 存在:
    │   └─> get_user_skill_permissions(user_id)
    │       └─> [tool_filter.py:121-207]
    │           ├─> 检查 Redis 缓存 (TTL 5分钟)
    │           ├─> 如果未命中，查询数据库:
    │           │   ├─> 获取用户角色
    │           │   ├─> 查询 RoleSkillPermission 表
    │           │   ├─> 检查 DepartmentSkillPermission 限制
    │           │   └─> 返回允许的 skill names
    │           └─> 缓存到 Redis
    │
    └─> 返回过滤后的 skill 列表（仅元数据）
```

#### 2.2 加载完整 Skill 指令

```
Agent 调用工具: load_skill("code_review")
    ↓
[skills.py:293-352] load_skill 实现:
    ├─> 检查 skill 是否在 _skills_cache 中
    │
    ├─> 权限检查（如果 user_id 存在）:
    │   └─> get_user_skill_permissions(user_id)
    │       └─> 验证用户是否有权限
    │
    ├─> load_skill_instructions(skill_path)
    │   └─> [skills.py:158-175]
    │       ├─> 读取 SKILL.md 完整文件
    │       ├─> parse_skill_md(content)
    │       └─> 返回 Markdown 指令部分
    │
    ├─> 更新缓存: skill["instructions"] = instructions
    │   skill["frontmatter_loaded"] = False
    │
    └─> 返回格式化的完整指令:
        # Skill: code_review
        Version: 1.2.0
        Path: ~/.pydantic-deep/skills/code_review

        ## Instructions
        [完整的 Markdown 指令...]

        ## Available Resources
        - checklist.md
        - review_template.txt
```

#### 2.3 读取 Skill 资源文件

```
Agent 调用工具: read_skill_resource("code_review", "checklist.md")
    ↓
[skills.py:355-392] read_skill_resource 实现:
    ├─> 检查 skill 存在性
    ├─> 构建资源路径: skill["path"] / resource_name
    ├─> 安全检查: 防止路径逃逸
    └─> 读取并返回文件内容
```

---

## 🔐 权限控制层

### 数据库表结构

```sql
-- Skill 注册表
skills
├─ id (PK)
├─ name (unique)
├─ description
├─ path (skill 目录路径)
├─ version
├─ tags (JSON)
├─ is_active
└─ created_by (FK -> users.id)

-- 角色权限
role_skill_permissions
├─ role_id (FK -> roles.id)
├─ skill_id (FK -> skills.id)
├─ can_use (Boolean)
└─ can_manage (Boolean)

-- 部门权限（覆盖角色权限）
department_skill_permissions
├─ department_id (FK -> departments.id)
├─ skill_id (FK -> skills.id)
└─ is_allowed (Boolean)
```

### 权限过滤逻辑

```python
# [tool_filter.py:121-207] get_user_skill_permissions()

1. 检查 Redis 缓存
   cache_key = f"user:skill_permissions:{user_id}"
   └─> 命中 → 返回缓存结果 (TTL 5分钟)

2. 查询数据库:
   ├─> 获取用户信息
   │   └─> 如果是 admin → 返回所有 active skills
   │
   ├─> 获取用户角色的 skill 权限
   │   SELECT skill_id FROM role_skill_permissions
   │   WHERE role_id IN (user.roles) AND can_use = True
   │
   ├─> 检查部门限制（如果用户有部门）
   │   SELECT skill_id FROM department_skill_permissions
   │   WHERE department_id = user.department_id AND is_allowed = False
   │   └─> 从角色权限中移除被部门禁止的 skills
   │
   └─> 返回最终的 skill_names set

3. 缓存到 Redis (5分钟)
```

---

## 📝 系统提示词注入机制

### 动态系统提示词生成

```python
# [agent.py:355-399] @agent.instructions 装饰器

每次对话前自动调用:
    ├─> get_skills_system_prompt(ctx.deps, loaded_skills)
    │   │
    │   ├─> 如果 enable_permission_filtering=True:
    │   │   └─> filter_skills_by_permission(loaded_skills, user_id)
    │   │       └─> 调用 get_user_skill_permissions()
    │   │           └─> 返回用户可见的 skills
    │   │
    │   └─> 生成系统提示词:
    │       ## 可用技能
    │       您可以访问扩展您能力的技能。
    │       使用 `list_skills` 查看可用技能，使用 `load_skill` 加载技能说明。
    │
    │       - **code_review** [code, review]: Automated code review
    │       - **data_analysis** [data]: Data analysis toolkit
    │
    └─> 注入到 LLM 的 system prompt
```

### cleanup processor 的作用

```python
# [processors/cleanup.py] deduplicate_stateful_tools_processor

在每次 LLM 请求前过滤消息历史:
    ├─> ✅ 删除 write_todos 调用（状态在系统提示词中）
    ├─> ✅ 删除 read_todos 调用（内容在系统提示词中）
    ├─> ✅ 删除 list_skills 调用（列表在系统提示词中）
    ├─> ❌ 保留 load_skill 调用（完整指令只在对话历史中！）
    └─> ❌ 保留 read_skill_resource 调用（资源内容只在对话历史中）

    └─> 原因:
        ├─> Todos 的最终状态已在系统提示词中完整展示
        ├─> Skills 的列表在系统提示词中，但完整指令不在
        ├─> 删除 load_skill 会导致 LLM 丢失 skill 的详细用法
        └─> 只删除真正"重复"的信息，避免信息丢失
```

---

## 🎯 关键设计亮点

### 1. **渐进式加载 (Progressive Disclosure)**
- **启动时**: 只加载 YAML frontmatter（name, description, tags）
- **运行时**: 按需加载完整 instructions
- **优势**: 减少内存占用，加快启动速度

### 2. **权限分层**
```
Admin 用户
    └─> 所有 active skills

普通用户
    └─> 角色权限 (RoleSkillPermission)
        └─> 减去部门禁止项 (DepartmentSkillPermission)
```

### 3. **多级缓存**
```
Redis 缓存 (5分钟 TTL)
    ↓ 未命中
数据库查询
    ↓
写回 Redis
```

### 4. **系统提示词动态注入**
- 每次对话前根据用户权限重新生成
- 只展示用户有权访问的 skills
- 配合 cleanup processor 清理历史记录

### 5. **安全性**
- 路径逃逸检查 (`resource_path.resolve().relative_to(skill_path)`)
- 权限验证在工具调用时再次检查
- 数据库 + Redis 双层权限控制

---

## 📊 完整数据流图

```
┌─────────────────────────────────────────────────────────────┐
│  启动阶段 (Agent Initialization)                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
         ┌──────────────────────────────────┐
         │ discover_skills()                │
         │ - 扫描 skill 目录                │
         │ - 解析 SKILL.md frontmatter    │
         │ - 不加载完整 instructions       │
         └──────────────────────────────────┘
                            │
                            ↓
         ┌──────────────────────────────────┐
         │ create_skills_toolset()          │
         │ - list_skills                    │
         │ - load_skill                     │
         │ - read_skill_resource            │
         └──────────────────────────────────┘
                            │
                            ↓
         ┌──────────────────────────────────┐
         │ _skills_cache                    │
         │ {name: Skill 元数据}             │
         └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  运行阶段 (每次对话)                                          │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┴───────────────────┐
         │                                      │
         ↓                                      ↓
┌────────────────────┐              ┌─────────────────────┐
│ 系统提示词生成      │              │ 工具调用            │
│                    │              │                     │
│ filter_skills_by_  │              │ list_skills()       │
│   permission()     │              │   ↓                 │
│   ↓                │              │ 权限检查            │
│ get_user_skill_    │              │   ↓                 │
│   permissions()    │              │ 返回过滤列表        │
│   ↓                │              │                     │
│ Redis 缓存查询     │              │ load_skill(name)    │
│   ↓                │              │   ↓                 │
│ 数据库权限查询     │              │ 权限检查            │
│   ↓                │              │   ↓                 │
│ 生成系统提示词     │              │ 加载完整指令        │
│                    │              │   ↓                 │
│ ## 可用技能        │              │ 返回 Markdown       │
│ - code_review      │              └─────────────────────┘
│ - data_analysis    │
└────────────────────┘
         │
         ↓
    注入到 LLM
         │
         ↓
┌────────────────────┐
│ cleanup processor  │
│ - 清理 load_skill  │
│   历史记录         │
│ - 清理 list_skills │
│   历史记录         │
└────────────────────┘
```

---

## 🔧 使用示例

### 1. 基础使用（无权限控制）
```python
from pydantic_deep import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-4",
    skill_directories=[
        {"path": "~/.pydantic-deep/skills", "recursive": True}
    ],
    include_skills=True,
)

result = await agent.run("列出可用的 skills")
```

### 2. 启用权限控制
```python
agent = create_deep_agent(
    model="openai:gpt-4",
    skill_directories=[{"path": "~/skills"}],
    enable_permission_filtering=True,  # 启用权限过滤
    user_id=123,  # 指定用户
)

# 用户只能看到和使用其角色允许的 skills
result = await agent.run("加载 code_review skill")
```

### 3. 使用 cleanup processor 减少 token
```python
from pydantic_deep.processors import deduplicate_stateful_tools_processor

agent = create_deep_agent(
    model="openai:gpt-4",
    skill_directories=[{"path": "~/skills"}],
    history_processors=[
        deduplicate_stateful_tools_processor,  # 清理 skill 加载历史
    ],
)
```

---

## 🎨 总结

你的 Skill 系统是一个**高度模块化、权限可控、性能优化**的设计：

1. ✅ **分离关注点**: 发现 → 加载 → 权限 → 注入 各司其职
2. ✅ **渐进式加载**: 按需加载，节省资源
3. ✅ **细粒度权限**: 角色 + 部门双层控制
4. ✅ **性能优化**: Redis 缓存 + cleanup processor
5. ✅ **安全性**: 路径检查 + 权限验证
6. ✅ **动态注入**: 系统提示词随用户权限变化

这个架构可以轻松扩展到数百个 skills，同时保持高性能和安全性。
