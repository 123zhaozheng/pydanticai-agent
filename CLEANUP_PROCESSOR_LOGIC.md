# Cleanup Processor 清理逻辑说明

## 🎯 核心原则

**只删除在系统提示词中已完整体现的工具调用，保留包含独特信息的调用。**

---

## 📊 工具分类对比表

| 工具名称 | 系统提示词包含内容 | 对话历史包含内容 | 是否删除 | 原因 |
|---------|------------------|-----------------|---------|------|
| **write_todos** | ✅ 当前完整的 todos 列表 | ⚠️ 历史的 todos 修改过程 | ✅ **删除** | 系统提示词有最终状态，历史是冗余的 |
| **read_todos** | ✅ 当前完整的 todos 列表 | 🔄 读取返回的 todos（同样内容） | ✅ **删除** | 完全重复 |
| **list_skills** | ✅ Skills 名称和简短描述 | 🔄 Skills 名称和简短描述（同样） | ✅ **删除** | 完全重复 |
| **load_skill** | ❌ 只有名称和描述 | ✅ **完整的 skill 指令**（几千字） | ❌ **保留** | 系统提示词没有详细内容！ |
| **read_skill_resource** | ❌ 无 | ✅ 资源文件完整内容 | ❌ **保留** | 独特信息 |

---

## 🔍 详细分析

### 1️⃣ **write_todos / read_todos - 应该删除** ✅

#### 系统提示词内容：
```markdown
## 当前待办事项

1. ✅ 读取配置文件 (completed)
2. 🔄 分析代码结构 (in_progress)
3. ⏳ 生成测试报告 (pending)
```

#### 对话历史内容（将被删除）：
```
User: 创建任务列表
Assistant: write_todos([...])
Tool Return: Updated 3 todos: 0 completed, 1 in_progress, 2 pending

User: 标记第一个任务完成
Assistant: write_todos([...])
Tool Return: Updated 3 todos: 1 completed, 1 in_progress, 1 pending

User: 现在的任务状态？
Assistant: read_todos()
Tool Return:
1. ✅ 读取配置文件 (completed)
2. 🔄 分析代码结构 (in_progress)
3. ⏳ 生成测试报告 (pending)
```

#### 为什么删除？
- ✅ 系统提示词已经显示**最终状态**（3 个 todos 的当前状态）
- ❌ 历史记录是**中间过程**（创建 → 更新 → 读取）
- 🔄 `read_todos` 返回的内容和系统提示词**完全相同**
- 💰 删除可节省大量 token（历史可能有 10+ 次 todos 操作）
- 🎯 LLM 只需要看最终状态，不需要看修改历史

---

### 2️⃣ **list_skills - 应该删除** ✅

#### 系统提示词内容：
```markdown
## 可用技能

您可以访问扩展您能力的技能。
使用 `list_skills` 查看可用技能，使用 `load_skill` 加载技能说明。

- **code_review** [code, review]: Automated code review assistant
- **data_analysis** [data, python]: Data analysis and visualization toolkit
- **security_audit** [security]: Security vulnerability scanner
```

#### 对话历史内容（将被删除）：
```
User: 有哪些可用的 skills？
Assistant: list_skills()
Tool Return:
Available Skills:

**code_review** (v1.2.0)
  Description: Automated code review assistant
  Tags: code, review
  Path: ~/.pydantic-deep/skills/code_review

**data_analysis** (v2.0.0)
  Description: Data analysis and visualization toolkit
  Tags: data, python
  Path: ~/.pydantic-deep/skills/data_analysis

**security_audit** (v1.5.0)
  Description: Security vulnerability scanner
  Tags: security
  Path: ~/.pydantic-deep/skills/security_audit
```

#### 为什么删除？
- ✅ 系统提示词已经列出所有 skills（名称、描述、标签）
- 🔄 `list_skills` 返回的信息和系统提示词**基本相同**（只多了版本号和路径）
- 💰 版本号和路径信息**价值不高**，删除可节省 token
- 🎯 如果真需要版本号，可以再次调用 `list_skills`（很少见）

---

### 3️⃣ **load_skill - 不应该删除** ❌

#### 系统提示词内容（只有简短描述）：
```markdown
## 可用技能

- **code_review** [code, review]: Automated code review assistant
```

#### 对话历史内容（完整指令，必须保留）：
```
User: 帮我审查代码
Assistant: load_skill("code_review")
Tool Return:
# Skill: code_review
Version: 1.2.0
Path: ~/.pydantic-deep/skills/code_review

## Instructions

This skill provides comprehensive code review capabilities including:
- Static code analysis
- Security vulnerability detection
- Performance optimization suggestions
- Best practice validation

### Step-by-step Process:

1. **Read the target file**
   ```
   Use read_file(path) to load the code you want to review
   ```

2. **Analyze code structure**
   - Check for proper error handling
   - Verify input validation
   - Look for potential memory leaks
   - Identify unused variables/functions

3. **Security audit**
   - SQL injection vulnerabilities
   - XSS attack vectors
   - Insecure deserialization
   - Weak authentication/authorization
   - Sensitive data exposure

4. **Performance review**
   - Algorithmic complexity (Big O)
   - Database query optimization
   - Caching opportunities
   - Resource cleanup

5. **Generate detailed report**
   Use the following format:

   ## Code Review Report

   **File**: [filename]
   **Reviewed**: [timestamp]

   ### 🔴 Critical Issues
   - Line X: SQL injection vulnerability in user input

   ### 🟡 Warnings
   - Line Y: Missing error handling

   ### ✅ Strengths
   - Good code organization

   ### 💡 Suggestions
   - Consider using prepared statements

### Checklist

Before submitting your review, ensure you've covered:
- [ ] Code style consistency
- [ ] Error handling completeness
- [ ] Security best practices
- [ ] Performance considerations
- [ ] Test coverage recommendations
- [ ] Documentation quality

### Example Usage

```python
# Good example
def process_user_input(user_id: int) -> User:
    if not isinstance(user_id, int):
        raise ValueError("Invalid user ID")

    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,)).fetchone()

# Bad example (vulnerable to SQL injection)
def process_user_input(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
```

## Available Resources
- checklist.md - Detailed review checklist
- review_template.txt - Report template
- security_patterns.md - Common security anti-patterns
```

#### 为什么不删除？
- ❌ 系统提示词**只有一句话描述**（"Automated code review assistant"）
- ✅ 对话历史包含**完整的几千字指令**（步骤、checklist、示例代码）
- 🚨 如果删除，LLM 会**丢失所有详细用法**
- 🎯 LLM 需要这些详细指令来正确执行代码审查任务
- 💡 这些内容**不在系统提示词中**，是独特信息

#### 删除后果演示：
```
# 删除 load_skill 后
User: 帮我审查这段代码
Assistant: 好的，我知道有 code_review skill...
          但我不知道具体怎么做（指令已被删除）
          我只知道它是 "Automated code review assistant"

# 保留 load_skill 后
User: 帮我审查这段代码
Assistant: 好的，根据 code_review skill 的指令：
          1. 我先 read_file 读取代码
          2. 检查安全问题（SQL 注入、XSS 等）
          3. 分析性能
          4. 生成详细报告（按照模板）
```

---

### 4️⃣ **read_skill_resource - 不应该删除** ❌

#### 系统提示词内容：
```markdown
（无相关内容）
```

#### 对话历史内容（资源文件，必须保留）：
```
Assistant: read_skill_resource("code_review", "checklist.md")
Tool Return:
# Code Review Checklist

## Security
- [ ] Input validation on all user inputs
- [ ] Parameterized queries (no string concatenation)
- [ ] Authentication required for sensitive operations
- [ ] Authorization checks before data access
- [ ] Secrets not hardcoded
- [ ] HTTPS enforced
- [ ] CSRF protection enabled
- [ ] XSS prevention (input sanitization)

## Performance
- [ ] Database queries optimized (no N+1 queries)
- [ ] Proper indexing on frequently queried columns
- [ ] Caching strategy implemented
- [ ] Resource cleanup (close connections, files)
- [ ] Async operations for I/O-bound tasks

## Code Quality
- [ ] Functions are single-purpose
- [ ] Variable names are descriptive
- [ ] Magic numbers avoided (use constants)
- [ ] Proper error handling
- [ ] Logging for debugging
- [ ] Comments for complex logic

## Testing
- [ ] Unit tests for critical functions
- [ ] Integration tests for API endpoints
- [ ] Edge cases covered
- [ ] Test coverage > 80%
```

#### 为什么不删除？
- ❌ 系统提示词**完全不包含**资源文件内容
- ✅ 资源文件是**独立的参考材料**（checklist、模板、示例）
- 🎯 LLM 需要这些内容来执行任务
- 💡 这是**纯粹的新增信息**，没有任何重复

---

## 📐 决策规则

```python
def should_delete_tool_call(tool_name: str) -> bool:
    """判断是否应该删除工具调用"""

    # 规则 1: 工具返回的内容已在系统提示词中完整体现
    if tool_returns_content_in_system_prompt(tool_name):
        return True  # 删除（例如：write_todos, read_todos）

    # 规则 2: 工具返回独特的、系统提示词没有的内容
    if tool_returns_unique_content(tool_name):
        return False  # 保留（例如：load_skill, read_skill_resource）

    # 规则 3: 不确定时，保留以避免信息丢失
    return False
```

---

## 🎯 最终配置

```python
# pydantic_deep/processors/cleanup.py

TOOLS_TO_FILTER = {
    "write_todos",         # ✅ 删除：最终状态在系统提示词
    "read_todos",          # ✅ 删除：返回内容 = 系统提示词
    "list_skills",         # ✅ 删除：skills 列表在系统提示词
    # "load_skill",        # ❌ 保留：完整指令不在系统提示词！
    # "read_skill_resource", # ❌ 保留：资源内容不在系统提示词！
}
```

---

## 💡 总结

| 情况 | 系统提示词 | 对话历史 | 清理策略 |
|-----|-----------|---------|---------|
| **Todos** | 完整的当前状态 | 历史修改过程 | 删除历史（已重复） |
| **Skills 列表** | Skills 名称+描述 | Skills 名称+描述 | 删除历史（已重复） |
| **Skill 指令** | 只有名称+描述 | **完整指令（几千字）** | **保留历史（独特信息）** |
| **Skill 资源** | 无 | 资源文件内容 | **保留历史（独特信息）** |

**核心原则：只删除真正重复的信息，保留独特内容，避免信息丢失。**