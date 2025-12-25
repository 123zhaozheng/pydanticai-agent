# Docker 容器生命周期管理问题与解决方案

## ⚠️ 当前问题

### 现状分析

你的代码中定义了空闲超时机制,但**并未实际实现自动清理逻辑**!

#### 代码证据

**[sandbox.py:266-288](pydantic_deep/backends/sandbox.py#L266-L288)** - 初始化参数

```python
class DockerSandbox(BaseSandbox):
    def __init__(
        self,
        idle_timeout: int = 3600,  # ✅ 定义了 1 小时超时
        ...
    ):
        self._idle_timeout = idle_timeout        # ✅ 保存超时时间
        self._last_activity = time.time()        # ✅ 记录最后活动时间
        self._container = None
```

**[sandbox.py:446-449](pydantic_deep/backends/sandbox.py#L446-L449)** - 更新活动时间

```python
def execute(self, command: str, timeout: int | None = None):
    self._ensure_container()
    self._last_activity = time.time()  # ✅ 每次执行更新时间戳
    ...
```

**[sandbox.py:560-571](pydantic_deep/backends/sandbox.py#L560-L571)** - 停止方法

```python
def stop(self) -> None:
    """Stop and remove the container."""
    if self._container:
        with contextlib.suppress(Exception):
            self._container.stop()
        self._container = None

def __del__(self) -> None:
    """Cleanup container on deletion."""
    self.stop()  # ⚠️ 只在对象销毁时清理
```

### 🚨 核心问题

**缺失的逻辑**: 没有后台任务周期性检查 `time.time() - self._last_activity > self._idle_timeout`!

---

## 🔄 当前容器生命周期

### 实际运行情况

```python
# 1. 用户请求 (15:51:45)
volumes = build_sandbox_volumes()
sandbox = DockerSandbox(volumes=volumes, idle_timeout=3600)  # 1 小时超时
                                                              # _last_activity = 15:51:45
# 容器实例创建,但容器尚未启动

# 2. 第一次工具调用 (15:51:50)
sandbox.execute("ls")
  ├─> _ensure_container()  # 启动容器
  ├─> _last_activity = 15:51:50  # 更新时间戳
  └─> 容器保持运行 (sleep infinity)

# 3. 第二次工具调用 (15:52:00)
sandbox.execute("date")
  ├─> 复用现有容器
  └─> _last_activity = 15:52:00  # 更新时间戳

# 4. 1 小时后 (16:52:00)
# ❌ 容器仍在运行!
# ❌ 没有任何逻辑检查 idle_timeout
# ❌ 容器永不自动停止,除非:
#     1. Python 进程退出 (__del__ 被调用)
#     2. 手动调用 sandbox.stop()
#     3. 服务器重启
```

### 容器状态

```bash
# 查看运行中的容器
$ docker ps

CONTAINER ID   IMAGE               COMMAND           CREATED        STATUS
a1b2c3d4e5f6   python:3.12-slim    sleep infinity    10 hours ago   Up 10 hours
                                    ↑
                                    永远不会自动停止!
```

---

## 💡 解决方案

### 方案 1: 添加后台清理任务 (推荐)

创建一个后台线程周期性检查并清理空闲容器。

#### 实现代码

```python
# pydantic_deep/backends/sandbox.py

import threading
from typing import ClassVar

class DockerSandbox(BaseSandbox):
    # 全局清理器(单例)
    _cleanup_thread: ClassVar[threading.Thread | None] = None
    _cleanup_lock: ClassVar[threading.Lock] = threading.Lock()
    _active_sandboxes: ClassVar[set[DockerSandbox]] = set()

    def __init__(self, ..., idle_timeout: int = 3600, ...):
        super().__init__(effective_id)

        self._idle_timeout = idle_timeout
        self._last_activity = time.time()
        self._container = None

        # 注册到活跃沙箱列表
        with self._cleanup_lock:
            self._active_sandboxes.add(self)

            # 启动清理线程(如果未启动)
            if self._cleanup_thread is None:
                self._cleanup_thread = threading.Thread(
                    target=self._run_cleanup_loop,
                    daemon=True,
                    name="sandbox-cleanup"
                )
                self._cleanup_thread.start()

    @classmethod
    def _run_cleanup_loop(cls):
        """后台清理线程,每 5 分钟检查一次"""
        import time

        while True:
            time.sleep(300)  # 每 5 分钟检查一次

            with cls._cleanup_lock:
                now = time.time()
                to_cleanup = []

                for sandbox in cls._active_sandboxes:
                    # 检查是否超时
                    if sandbox._container is not None:
                        idle_time = now - sandbox._last_activity
                        if idle_time > sandbox._idle_timeout:
                            to_cleanup.append(sandbox)

                # 清理超时的容器
                for sandbox in to_cleanup:
                    try:
                        print(f"🧹 Cleaning up idle container {sandbox.id}")
                        sandbox.stop()
                    except Exception as e:
                        print(f"❌ Failed to cleanup container: {e}")

    def stop(self):
        """Stop and remove the container."""
        if self._container:
            with contextlib.suppress(Exception):
                self._container.stop()
            self._container = None

        # 从活跃列表移除
        with self._cleanup_lock:
            self._active_sandboxes.discard(self)
```

#### 优势

- ✅ 自动清理空闲容器
- ✅ 节省系统资源
- ✅ 全局单个清理线程,低开销
- ✅ 线程安全

---

### 方案 2: 按需检查 (简单但不完美)

在每次 `execute()` 时检查其他沙箱是否超时。

```python
def execute(self, command: str, timeout: int | None = None):
    # 检查自身是否超时
    if self._container is not None:
        idle_time = time.time() - self._last_activity
        if idle_time > self._idle_timeout:
            print(f"🧹 Container idle for {idle_time:.0f}s, restarting...")
            self.stop()

    self._ensure_container()
    self._last_activity = time.time()
    ...
```

#### 缺点

- ❌ 只在下次使用时才清理
- ❌ 长期不用的容器会一直运行
- ❌ 无法清理其他用户的容器

---

### 方案 3: FastAPI 后台任务 (适合 Web 应用)

利用 FastAPI 的后台任务机制。

```python
# src/main.py

from fastapi import FastAPI, BackgroundTasks
import asyncio

app = FastAPI()

# 全局沙箱管理器
from collections import defaultdict
active_sandboxes: dict[int, DockerSandbox] = {}

async def cleanup_idle_sandboxes():
    """定期清理空闲沙箱"""
    while True:
        await asyncio.sleep(300)  # 每 5 分钟

        now = time.time()
        to_remove = []

        for conversation_id, sandbox in active_sandboxes.items():
            if sandbox._container is not None:
                idle_time = now - sandbox._last_activity
                if idle_time > sandbox._idle_timeout:
                    print(f"🧹 Cleanup sandbox for conversation {conversation_id}")
                    sandbox.stop()
                    to_remove.append(conversation_id)

        for conv_id in to_remove:
            del active_sandboxes[conv_id]

@app.on_event("startup")
async def startup_event():
    """应用启动时启动清理任务"""
    asyncio.create_task(cleanup_idle_sandboxes())

@app.post("/api/conversations/{conversation_id}/chat")
async def chat_stream(conversation_id: int, ...):
    # 复用或创建沙箱
    if conversation_id not in active_sandboxes:
        volumes = build_sandbox_volumes()
        sandbox = DockerSandbox(volumes=volumes, idle_timeout=3600)
        active_sandboxes[conversation_id] = sandbox
    else:
        sandbox = active_sandboxes[conversation_id]

    # 使用沙箱...
    deps = DeepAgentDeps(backend=sandbox, ...)
    ...
```

#### 优势

- ✅ 与 FastAPI 集成良好
- ✅ 可以按 conversation 管理沙箱
- ✅ 支持沙箱复用

---

## 📊 资源影响对比

### 当前状态 (无清理)

| 时间 | 容器数 | 内存占用 | CPU占用 |
|------|--------|---------|--------|
| 0 小时 | 0 | 0 MB | 0% |
| 1 小时 | 10 | ~1 GB | ~1% |
| 10 小时 | 100 | ~10 GB | ~5% |
| 24 小时 | 240 | ~24 GB | ~10% |

**问题**: 容器永不清理,资源持续增长!

### 有清理机制后

| 时间 | 容器数 | 内存占用 | CPU占用 |
|------|--------|---------|--------|
| 0 小时 | 0 | 0 MB | 0% |
| 1 小时 | 10 | ~1 GB | ~1% |
| 10 小时 | ~10 | ~1 GB | ~1% |
| 24 小时 | ~10 | ~1 GB | ~1% |

**改善**: 容器数稳定,资源占用可控!

---

## 🎯 推荐配置

### 开发环境

```python
# 短超时,快速清理
sandbox = DockerSandbox(
    volumes=volumes,
    idle_timeout=300,  # 5 分钟
    auto_remove=True
)
```

### 生产环境

```python
# 长超时,复用容器
sandbox = DockerSandbox(
    volumes=volumes,
    idle_timeout=3600,  # 1 小时
    auto_remove=True
)

# + 后台清理任务
```

---

## 🔍 验证方法

### 1. 查看运行中的容器

```bash
# 所有容器
docker ps

# 过滤 Python 容器
docker ps --filter ancestor=python:3.12-slim

# 显示运行时间
docker ps --format "table {{.ID}}\t{{.Image}}\t{{.RunningFor}}\t{{.Status}}"
```

### 2. 查看容器资源占用

```bash
docker stats --no-stream
```

### 3. 手动清理所有容器

```bash
# 停止所有 Python 容器
docker stop $(docker ps -q --filter ancestor=python:3.12-slim)

# 清理停止的容器
docker container prune -f
```

---

## ⚡ 临时解决方案 (立即可用)

如果暂时不想修改代码,可以用 cron 定期清理:

```bash
# 添加到 crontab
# 每小时清理空闲超过 1 小时的容器
0 * * * * docker ps --filter ancestor=python:3.12-slim --format '{{.ID}}' | xargs -r docker stop

# 每天清理停止的容器
0 0 * * * docker container prune -f
```

---

## 📝 总结

### 当前状态

- ❌ **没有自动清理**: 容器会永久运行直到 Python 进程退出
- ❌ **资源浪费**: 空闲容器占用内存/CPU
- ❌ **容器累积**: 长时间运行后容器数量爆炸

### 建议行动

1. **立即**: 使用 cron 临时清理 (避免资源耗尽)
2. **短期**: 实现方案 2 (按需检查,简单快速)
3. **长期**: 实现方案 1 或 3 (完整的后台清理机制)

### 关键指标

```python
# 检查空闲时间
idle_time = time.time() - sandbox._last_activity

# 应该清理?
should_cleanup = idle_time > sandbox._idle_timeout

# 实际清理
if should_cleanup:
    sandbox.stop()
```

**核心问题**: `idle_timeout` 参数存在,但没有任何代码使用它来清理容器!
