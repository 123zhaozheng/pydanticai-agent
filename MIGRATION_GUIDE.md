# Migration Guide: Sandbox-Only Backend

## Overview

从版本 0.2.0 开始，pydantic-deep 推荐只使用 `DockerSandbox` 作为后端。以下后端已被标记为废弃：

- `LocalSandbox` - 无隔离的本地子进程执行
- `FilesystemBackend` - 直接文件系统访问
- `CompositeBackend` - 多后端路由

## 为什么迁移？

### 优势
1. **更好的隔离性**：Docker 容器提供进程、文件系统和网络隔离
2. **一致的环境**：所有操作在相同的容器环境中执行
3. **简化架构**：不再需要复杂的后端路由和权限管理
4. **动态文件挂载**：基于 user_id 和 conversation_id 自动挂载目录
5. **Skills 沙箱化**：Skills 在容器内执行，更安全

### 新的目录结构

```
宿主机                                    容器内
{base_dir}/
├── uploads/{user_id}/{conversation_id}  → /workspace/uploads/       (读写)
├── intermediate/{user_id}/{conversation_id} → /workspace/intermediate/ (读写)
└── skills/                              → /workspace/skills/        (只读)
```

## 迁移步骤

### 1. 从 FilesystemBackend 迁移

**旧代码：**
```python
from pydantic_deep import create_deep_agent, FilesystemBackend

backend = FilesystemBackend(root_dir="/path/to/workspace")
agent = create_deep_agent(backend=backend)
```

**新代码：**
```python
from pydantic_deep import create_deep_agent, DockerSandbox

sandbox = DockerSandbox(
    user_id=user_id,
    conversation_id=conversation_id,
    # 可选：自定义基础目录
    base_dir="/path/to/data"
)
agent = create_deep_agent(backend=sandbox)
```

### 2. 从 CompositeBackend 迁移

**旧代码：**
```python
from pydantic_deep import CompositeBackend, FilesystemBackend, StateBackend

backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/uploads/": FilesystemBackend("/data/uploads"),
        "/temp/": StateBackend(),
    }
)
```

**新代码：**
```python
# DockerSandbox 自动处理多个挂载点
from pydantic_deep import DockerSandbox

sandbox = DockerSandbox(
    user_id=user_id,
    conversation_id=conversation_id,
    # 自动挂载三个目录：uploads, intermediate, skills
)
```

### 3. 从 LocalSandbox 迁移

**旧代码：**
```python
from pydantic_deep.backends.sandbox import LocalSandbox

sandbox = LocalSandbox(work_dir="/tmp/workspace")
```

**新代码：**
```python
from pydantic_deep import DockerSandbox

sandbox = DockerSandbox(
    user_id=user_id,
    conversation_id=conversation_id,
)
```

### 4. 自定义上传目录

**新功能：** 可以为每个会话指定自定义上传目录

```python
sandbox = DockerSandbox(
    user_id=user_id,
    conversation_id=conversation_id,
    upload_path="/custom/upload/path"  # 可选
)
```

## API 变更

### 1. DockerSandbox 新参数

```python
DockerSandbox(
    # 新增参数（自动挂载）
    user_id: int | str | None = None,
    conversation_id: int | str | None = None,
    upload_path: str | None = None,
    base_dir: str | None = None,

    # 原有参数
    image: str = "python:3.12-slim",
    sandbox_id: str | None = None,
    work_dir: str = "/workspace",
    auto_remove: bool = True,
    runtime: RuntimeConfig | str | None = None,
    session_id: str | None = None,
    idle_timeout: int = 3600,
    volumes: dict[str, dict[str, str]] | None = None,
)
```

### 2. 新的工具函数

```python
from pydantic_deep import discover_container_files, list_container_directories, get_file_info

# 发现容器内所有文件
files = discover_container_files(sandbox)
# 返回：['/workspace/uploads/data.csv', '/workspace/intermediate/output.txt', ...]

# 按目录列出文件
dirs = list_container_directories(sandbox)
# 返回：{'uploads': ['data.csv'], 'intermediate': ['output.txt'], ...}

# 获取文件详细信息
info = get_file_info(sandbox, '/workspace/uploads/data.csv')
# 返回：{'path': '...', 'size': 1024, 'permissions': '-rw-r--r--', ...}
```

### 3. DeepAgentDeps 自动注入文件路径

```python
from pydantic_deep import DeepAgentDeps, discover_container_files

# 扫描容器文件
file_paths = discover_container_files(sandbox)

# 注入到 deps
deps = DeepAgentDeps(
    backend=sandbox,
    user_id=user_id,
    conversation_id=conversation_id,
    file_paths=file_paths  # Agent 会自动在系统提示词中显示
)
```

### 4. Skills 完全沙箱化

Skills 现在从容器内动态加载：

```python
# 旧方式：从宿主机文件系统加载
from pydantic_deep.toolsets.skills import discover_skills

skills = discover_skills([{"path": "/host/skills", "recursive": True}])

# 新方式：从容器内自动发现（无需预加载）
from pydantic_deep import create_deep_agent

agent = create_deep_agent(
    include_skills=True,  # Skills 从 /workspace/skills/ 动态加载
)
```

**新增 Skill 工具：**
- `list_skills()` - 从容器扫描 skills
- `load_skill(skill_name)` - 从容器读取 SKILL.md
- `read_skill_resource(skill_name, resource_name)` - 从容器读取资源
- `execute_skill_script(skill_name, script_name, args)` - 在容器内执行脚本

## 文件上传 API

新增 RESTful API 用于文件上传：

```bash
# 上传文件到会话
POST /api/uploads/{conversation_id}
Content-Type: multipart/form-data

# 列出已上传文件
GET /api/uploads/{conversation_id}/files

# 删除文件
DELETE /api/uploads/{conversation_id}/files/{filename}
```

**使用示例：**
```python
import requests

# 上传文件
with open('data.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/uploads/123',
        files={'file': f}
    )
# 返回：{'filename': 'data.csv', 'container_path': '/workspace/uploads/data.csv', ...}

# 列出文件
response = requests.get('http://localhost:8000/api/uploads/123/files')
# 返回：[{'filename': 'data.csv', 'size': 1024, ...}, ...]
```

## 环境变量配置

```bash
# .env
PYDANTIC_DEEP_BASE_DIR=D:/pydantic-deep-data/  # Windows
# 或
PYDANTIC_DEEP_BASE_DIR=/var/pydantic-deep/     # Linux
```

**默认值（如果未设置）：**
- Windows: `D:/pydantic-deep-data`
- Linux/Mac: `/var/pydantic-deep`

## 完整示例

### 会话 API 集成

```python
# src/api/conversations.py
from pydantic_deep import create_deep_agent, DockerSandbox, discover_container_files
from pydantic_deep.deps import DeepAgentDeps

@router.post("/{conversation_id}/chat")
async def chat_stream(
    conversation_id: int,
    body: ChatRequest,
    user_id: int = 1,
):
    # 1. 创建沙箱（自动挂载目录）
    sandbox = DockerSandbox(
        user_id=user_id,
        conversation_id=conversation_id,
        upload_path=body.upload_path  # 可选
    )

    # 2. 发现容器文件
    file_paths = discover_container_files(sandbox)

    # 3. 创建 deps
    deps = DeepAgentDeps(
        backend=sandbox,
        user_id=user_id,
        conversation_id=conversation_id,
        file_paths=file_paths  # 自动注入到系统提示词
    )

    # 4. 创建 Agent
    agent = create_deep_agent(
        model=model,
        backend=sandbox,
        include_skills=True,  # Skills 从容器动态加载
    )

    # 5. 运行
    result = await agent.run(body.message, deps=deps)

    return result
```

## 常见问题

### Q: 旧的后端还能用吗？

A: 可以，但会显示废弃警告。建议尽快迁移到 `DockerSandbox`。

### Q: 如何处理现有的本地文件？

A: 使用文件上传 API 或在创建沙箱时通过 `upload_path` 参数挂载现有目录。

### Q: Skills 必须放在特定目录吗？

A: 是的，Skills 必须放在 `{base_dir}/skills/` 目录下，会被挂载到容器的 `/workspace/skills/`。

### Q: 容器会自动清理吗？

A: 会的，容器在会话结束时自动停止（`auto_remove=True`）。

### Q: 如何调试容器内的问题？

A: 使用 `sandbox.execute("ls -la /workspace")` 或其他命令检查容器状态。

## 兼容性

- **最低 Docker 版本**: 20.10+
- **Python 版本**: 3.10+
- **操作系统**: Windows, Linux, macOS (需要 Docker Desktop)

## 需要帮助？

查看完整文档：[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
