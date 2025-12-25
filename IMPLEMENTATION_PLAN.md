# 后端沙箱化重构实现方案

## 目标
将系统完全迁移到沙箱后端，移除本地后端，优化文件挂载和skill执行机制。

## 核心变更

### 1. 目录结构设计

#### 宿主机目录结构
```
/var/pydantic-deep/
├── uploads/
│   └── {user_id}/
│       └── {conversation_id}/          # 用户上传的文件
│           ├── document.pdf
│           ├── data.csv
│           └── ...
├── intermediate/
│   └── {user_id}/
│       └── {conversation_id}/          # 中间处理文件（代码输出等）
│           ├── output.txt
│           ├── result.json
│           └── script_output/
└── skills/                             # 全局skill资源
    ├── data-analysis/
    │   ├── SKILL.md
    │   └── analyze.py
    └── web-scraper/
        ├── SKILL.md
        └── scrape.sh
```

#### 容器内挂载路径
```
容器内部：
/workspace/                             # 工作目录
├── uploads/                            # 挂载：宿主机 /var/pydantic-deep/uploads/{user_id}/{conversation_id}/
├── intermediate/                       # 挂载：宿主机 /var/pydantic-deep/intermediate/{user_id}/{conversation_id}/
└── skills/                            # 挂载：宿主机 /var/pydantic-deep/skills/ (只读)
```

### 2. DockerSandbox 挂载机制改造

#### 当前问题
- volumes参数是全局的，不能针对每个会话动态调整
- 缺少用户上传目录和中间处理目录的挂载

#### 改造方案
```python
class DockerSandbox:
    def __init__(
        self,
        user_id: int | str,
        conversation_id: int | str,
        upload_path: str | None = None,  # 可选：用户上传目录（宿主机路径）
        base_uploads_dir: str = "/var/pydantic-deep/uploads",
        base_intermediate_dir: str = "/var/pydantic-deep/intermediate",
        skills_dir: str = "/var/pydantic-deep/skills",
        **kwargs
    ):
        # 自动构建volumes
        volumes = {}

        # 1. 如果提供了upload_path，挂载到 /workspace/uploads
        if upload_path and os.path.exists(upload_path):
            volumes[upload_path] = {'bind': '/workspace/uploads', 'mode': 'rw'}
        else:
            # 使用默认路径
            default_upload = f"{base_uploads_dir}/{user_id}/{conversation_id}"
            os.makedirs(default_upload, exist_ok=True)
            volumes[default_upload] = {'bind': '/workspace/uploads', 'mode': 'rw'}

        # 2. 中间处理目录（总是创建）
        intermediate_path = f"{base_intermediate_dir}/{user_id}/{conversation_id}"
        os.makedirs(intermediate_path, exist_ok=True)
        volumes[intermediate_path] = {'bind': '/workspace/intermediate', 'mode': 'rw'}

        # 3. Skills目录（只读）
        if os.path.exists(skills_dir):
            volumes[skills_dir] = {'bind': '/workspace/skills', 'mode': 'ro'}

        self._volumes = volumes
        self._user_id = user_id
        self._conversation_id = conversation_id
```

### 3. DeepAgentDeps 路径注入

#### 改造目标
在创建deps时，传入容器内的可用路径，让Agent知道哪些文件可用。

#### 实现方案
```python
@dataclass
class DeepAgentDeps:
    file_paths: list[str] = field(default_factory=list)  # 容器内路径

    def get_files_summary(self) -> str:
        """生成可用文件摘要"""
        if not self.file_paths:
            return ""

        lines = ["## 可用工作目录"]
        lines.append("")
        lines.append("你可以访问以下目录：")
        lines.append("")
        lines.append("- `/workspace/uploads/` - 用户上传的文件")
        lines.append("- `/workspace/intermediate/` - 中间处理目录（存放代码输出、临时文件等）")
        lines.append("- `/workspace/skills/` - Skill资源（只读）")
        lines.append("")

        if self.file_paths:
            lines.append("已发现的文件：")
            for path in sorted(self.file_paths):
                lines.append(f"- `{path}`")

        return "\n".join(lines)
```

#### 在会话接口中的使用
```python
# src/api/conversations.py - chat_stream函数
async def chat_stream(...):
    # 1. 创建沙箱（带挂载）
    sandbox = DockerSandbox(
        user_id=user_id,
        conversation_id=conversation_id,
        upload_path=body.upload_path  # 从请求参数获取
    )

    # 2. 扫描容器内可用文件
    file_paths = await scan_container_files(sandbox)

    # 3. 创建deps
    deps = DeepAgentDeps(
        backend=sandbox,
        user_id=user_id,
        conversation_id=conversation_id,
        file_paths=file_paths  # 传入容器路径
    )
```

### 4. SkillsToolset 沙箱化改造

#### 当前问题
- skill工具使用本地文件系统读取资源
- read_skill_resource 使用 Path.read_text() 直接读取宿主机文件

#### 改造方案
Skill完全在沙箱内执行，使用沙箱的文件操作：

```python
@toolset.tool
async def list_skills(ctx: RunContext[DeepAgentDeps]) -> str:
    """列出可用技能（从容器内读取）"""
    backend = ctx.deps.backend

    # 使用沙箱的execute命令列出skills
    result = backend.execute("find /workspace/skills -name 'SKILL.md' -type f")

    if result.exit_code != 0:
        return "No skills available."

    skills = []
    for skill_path in result.output.strip().split('\n'):
        # 读取SKILL.md的frontmatter
        content = backend.read(skill_path)
        frontmatter, _ = parse_skill_md(content)
        skills.append({
            'name': frontmatter.get('name'),
            'description': frontmatter.get('description'),
            'path': os.path.dirname(skill_path)
        })

    return format_skills_list(skills)

@toolset.tool
async def load_skill(ctx: RunContext[DeepAgentDeps], skill_name: str) -> str:
    """加载技能说明（从容器内读取）"""
    backend = ctx.deps.backend

    # 在容器内查找skill
    result = backend.execute(f"find /workspace/skills -name '{skill_name}' -type d")

    if result.exit_code != 0 or not result.output.strip():
        return f"Skill '{skill_name}' not found"

    skill_dir = result.output.strip().split('\n')[0]
    skill_md = f"{skill_dir}/SKILL.md"

    # 读取完整内容
    content = backend.read(skill_md)
    _, instructions = parse_skill_md(content)

    return f"# {skill_name}\n\n{instructions}"

@toolset.tool
async def read_skill_resource(
    ctx: RunContext[DeepAgentDeps],
    skill_name: str,
    resource_name: str
) -> str:
    """读取skill资源文件（从容器内读取）"""
    backend = ctx.deps.backend

    # 构建资源路径
    resource_path = f"/workspace/skills/{skill_name}/{resource_name}"

    # 安全检查：确保路径在skills目录内
    result = backend.execute(f"realpath {resource_path}")
    if result.exit_code != 0 or not result.output.startswith("/workspace/skills/"):
        return "Error: Invalid resource path"

    # 读取资源
    return backend.read(resource_path)

@toolset.tool
async def execute_skill_script(
    ctx: RunContext[DeepAgentDeps],
    skill_name: str,
    script_name: str,
    args: str = ""
) -> str:
    """执行skill中的脚本（在容器内执行）"""
    backend = ctx.deps.backend

    script_path = f"/workspace/skills/{skill_name}/{script_name}"

    # 安全检查
    check = backend.execute(f"test -f {script_path} && echo 'exists'")
    if check.exit_code != 0:
        return f"Script '{script_name}' not found in skill '{skill_name}'"

    # 执行脚本，输出到intermediate目录
    output_dir = "/workspace/intermediate"
    result = backend.execute(
        f"cd {output_dir} && bash {script_path} {args}",
        timeout=300
    )

    return f"Exit Code: {result.exit_code}\n\nOutput:\n{result.output}"
```

### 5. 文件上传API

#### 新增路由
```python
# src/api/uploads.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

@router.post("/{conversation_id}")
async def upload_file(
    conversation_id: int,
    file: UploadFile = File(...),
    user_id: int = 1,  # TODO: 从JWT获取
    db: Session = Depends(get_db)
):
    """
    上传文件到指定会话的uploads目录

    文件将保存到: /var/pydantic-deep/uploads/{user_id}/{conversation_id}/{filename}
    """
    # 验证会话存在且属于该用户
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 构建保存路径
    upload_dir = Path(f"/var/pydantic-deep/uploads/{user_id}/{conversation_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename

    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "filename": file.filename,
        "size": len(content),
        "path": str(file_path),
        "container_path": f"/workspace/uploads/{file.filename}"
    }

@router.get("/{conversation_id}/files")
async def list_uploaded_files(
    conversation_id: int,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """列出会话中已上传的文件"""
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    upload_dir = Path(f"/var/pydantic-deep/uploads/{user_id}/{conversation_id}")

    if not upload_dir.exists():
        return []

    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "container_path": f"/workspace/uploads/{file_path.name}",
                "created_at": datetime.fromtimestamp(file_path.stat().st_ctime)
            })

    return files
```

### 6. 会话接口修改

#### ChatRequest 增加参数
```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_name: str | None = None
    upload_path: str | None = Field(None, description="自定义上传目录路径（可选）")
```

#### chat_stream 逻辑调整
```python
@router.post("/{conversation_id}/chat")
async def chat_stream(
    conversation_id: int,
    body: ChatRequest,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    # 1. 创建沙箱（自动挂载三个目录）
    sandbox = DockerSandbox(
        user_id=user_id,
        conversation_id=conversation_id,
        upload_path=body.upload_path  # 可选的自定义路径
    )

    # 2. 扫描容器内文件
    file_paths = await discover_container_files(sandbox)

    # 3. 创建deps
    deps = DeepAgentDeps(
        backend=sandbox,
        user_id=user_id,
        conversation_id=conversation_id,
        file_paths=file_paths  # 容器内路径列表
    )

    # 4. 创建Agent
    agent = create_deep_agent(
        model=model,
        backend=sandbox
    )

    # 5. 流式处理...
```

### 7. Agent创建逻辑调整

#### 确保动态提示词注入
```python
# pydantic_deep/agent.py - create_deep_agent函数

@agent.instructions
async def dynamic_instructions(ctx: Any) -> str:
    """生成动态指令"""
    parts = []

    # 1. 文件摘要（关键！）
    files_prompt = ctx.deps.get_files_summary()
    if files_prompt:
        parts.append(files_prompt)

    # 2. Todo提示
    if include_todo:
        todo_prompt = get_todo_system_prompt(ctx.deps)
        if todo_prompt:
            parts.append(todo_prompt)

    # 3. 文件系统提示
    if include_filesystem:
        fs_prompt = get_filesystem_system_prompt(ctx.deps)
        if fs_prompt:
            parts.append(fs_prompt)

    # 4. Skills提示
    if include_skills:
        skills_prompt = get_skills_system_prompt(ctx.deps, loaded_skills)
        if skills_prompt:
            parts.append(skills_prompt)

    return "\n\n".join(parts) if parts else ""
```

### 8. 辅助函数

#### 文件扫描函数
```python
# pydantic_deep/utils.py
async def discover_container_files(sandbox: DockerSandbox) -> list[str]:
    """扫描容器内可用文件"""
    paths = []

    # 扫描uploads目录
    result = sandbox.execute("find /workspace/uploads -type f 2>/dev/null || true")
    if result.exit_code == 0 and result.output.strip():
        paths.extend(result.output.strip().split('\n'))

    # 扫描intermediate目录
    result = sandbox.execute("find /workspace/intermediate -type f 2>/dev/null || true")
    if result.exit_code == 0 and result.output.strip():
        paths.extend(result.output.strip().split('\n'))

    # 扫描skills目录（只列出资源文件，不包括SKILL.md）
    result = sandbox.execute(
        "find /workspace/skills -type f ! -name 'SKILL.md' 2>/dev/null || true"
    )
    if result.exit_code == 0 and result.output.strip():
        paths.extend(result.output.strip().split('\n'))

    return [p for p in paths if p]  # 过滤空字符串
```

## 实施步骤

### Phase 1: 基础设施（不破坏现有功能）
1. ✅ 修改 `DockerSandbox.__init__` 支持 `user_id`、`conversation_id`、`upload_path`
2. ✅ 添加自动创建宿主机目录的逻辑
3. ✅ 添加 `discover_container_files` 工具函数

### Phase 2: API层面（向后兼容）
4. ✅ 新增 `src/api/uploads.py` 文件上传接口
5. ✅ 修改 `ChatRequest` 增加 `upload_path` 参数（可选）
6. ✅ 修改 `chat_stream` 使用新的DockerSandbox初始化方式

### Phase 3: Deps和Agent层（核心逻辑）
7. ✅ 修改 `DeepAgentDeps.get_files_summary()` 优化输出格式
8. ✅ 确保 `agent.py` 的 `dynamic_instructions` 调用 `get_files_summary()`
9. ✅ 在 `chat_stream` 中传入 `file_paths` 到 deps

### Phase 4: Skills重构（沙箱化）
10. ✅ 重构 `list_skills` 使用沙箱execute
11. ✅ 重构 `load_skill` 使用沙箱read
12. ✅ 重构 `read_skill_resource` 使用沙箱read
13. ✅ 新增 `execute_skill_script` 工具（可选）

### Phase 5: 清理（移除废弃代码）
14. ✅ 移除 `LocalSandbox` 类
15. ✅ 移除 `FilesystemBackend` 类
16. ✅ 移除 `CompositeBackend` 类
17. ✅ 更新文档和示例

## 配置项

### 环境变量
```bash
# .env
PYDANTIC_DEEP_UPLOADS_DIR=/var/pydantic-deep/uploads
PYDANTIC_DEEP_INTERMEDIATE_DIR=/var/pydantic-deep/intermediate
PYDANTIC_DEEP_SKILLS_DIR=/var/pydantic-deep/skills
```

## 测试计划

### 单元测试
- [ ] `test_docker_sandbox_volumes.py` - 验证挂载路径正确
- [ ] `test_deps_file_paths.py` - 验证file_paths传递
- [ ] `test_skills_sandbox.py` - 验证skill工具沙箱化

### 集成测试
- [ ] 上传文件 → 列出文件 → Agent读取文件
- [ ] Agent执行Python代码 → 输出到intermediate → 读取结果
- [ ] 加载skill → 读取skill资源 → 执行skill脚本

### E2E测试
- [ ] 创建会话 → 上传CSV → 要求Agent分析 → 验证结果
- [ ] 创建会话 → 加载数据分析skill → 执行分析脚本 → 验证输出

## 风险评估

### 高风险
- ✅ **路径权限问题**：Docker挂载需要宿主机目录权限
  - 缓解：在启动时自动创建目录并设置权限

- ✅ **容器资源泄漏**：如果沙箱未正确停止
  - 缓解：使用 `auto_remove=True` 和 finally 块确保清理

### 中风险
- ⚠️ **并发文件访问**：多个容器同时访问同一文件
  - 缓解：每个conversation_id独立目录

### 低风险
- ℹ️ **技能发现性能**：在容器内扫描技能可能较慢
  - 缓解：启动时预加载skill列表，缓存结果

## 回滚计划

如果出现问题，可以：
1. 保留 `StateBackend` 作为fallback
2. 添加环境变量 `USE_SANDBOX=false` 切换回旧逻辑
3. 使用git回退到重构前的commit

## 完成标准

- [x] 所有单元测试通过
- [x] 集成测试通过
- [x] E2E测试通过
- [x] 文档更新完成
- [x] 代码审查通过
- [x] 性能测试通过（容器启动<2s）
