# 安装

## 要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (推荐) 或 pip

## 使用 uv 安装（推荐）

```bash
uv add pydantic-deep
```

## 使用 pip 安装

```bash
pip install pydantic-deep
```

## 可选依赖

### Docker 沙箱

用于 Docker 容器中的隔离代码执行：

```bash
uv add pydantic-deep[sandbox]
# 或
pip install pydantic-deep[sandbox]
```

### 开发

用于运行测试和构建文档：

```bash
uv add pydantic-deep[dev]
# 或
pip install pydantic-deep[dev]
```

## 环境设置

### API 密钥

pydantic-deep 使用支持多种模型提供商的 Pydantic AI。设置您的 API 密钥：

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY=your-api-key
    ```

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY=your-api-key
    ```

=== "Google"

    ```bash
    export GOOGLE_API_KEY=your-api-key
    ```

### Docker（可选）

用于使用 `DockerSandbox`：

1. 安装 Docker: [获取 Docker](https://docs.docker.com/get-docker/)
2. 确保 Docker 守护进程正在运行
3. 拉取 Python 镜像：

```bash
docker pull python:3.12-slim
```

## 验证安装

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    result = await agent.run("Say hello!", deps=deps)
    print(result.output)

asyncio.run(main())
```

## 故障排除

### 导入错误

如果遇到导入错误，请确保您拥有正确的 Python 版本：

```bash
python --version  # 应该是 3.10+
```

### 未找到 API 密钥

确保您的 API 密钥已在环境中设置：

```bash
echo $ANTHROPIC_API_KEY
```

### Docker 权限被拒绝

在 Linux 上，您可能需要将用户添加到 docker 组：

```bash
sudo usermod -aG docker $USER
```

然后注销并重新登录。

## 下一步

- [核心概念](concepts/index.md) - 了解基础知识
- [基本用法示例](examples/basic-usage.md) - 您的第一个 deep agent
- [API 参考](api/index.md) - 完整的 API 文档
