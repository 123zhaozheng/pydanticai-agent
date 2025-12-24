# 安装指南

## 📦 安装步骤

### 1. 克隆项目（如果还没有）
```bash
git clone <your-repo>
cd pydantic-deepagents
```

### 2. 创建虚拟环境
```bash
python -m venv .venv

# Windows 激活
.venv\Scripts\activate

# Linux/Mac 激活
source .venv/bin/activate
```

### 3. 以开发模式安装项目（重要！）

**使用 UV（推荐）：**
```bash
# 安装核心依赖 + API 服务器依赖
uv sync --group api

# 或者安装所有组（api + dev + lint）
uv sync --all-groups
```

**使用 pip：**
```bash
# 安装核心依赖 + API 服务器依赖
pip install -e ".[api]"

# 这会安装：
# - pydantic-ai (核心框架)
# - fastapi (API 服务器)
# - sqlalchemy (数据库)
# - 以及所有其他必需的依赖

# 如果只需要核心功能（不需要 API 服务器）：
# pip install -e .
```

### 5. 初始化数据库
```bash
# 创建数据库表
python -c "from src.database import init_db; init_db()"

# 或者直接启动服务器（会自动初始化）
python src/main.py
```

---

## 🎯 为什么用 `pip install -e .`？

- ✅ **-e** (editable mode) 让你在开发时修改代码立即生效，无需重新安装
- ✅ 自动安装 `pyproject.toml` 中的所有依赖（pydantic-ai, pydantic, httpx, etc.）
- ✅ 让 `pydantic_deep` 包可以在任何地方导入

---

## 📝 依赖说明

**pyproject.toml（核心依赖）：**
- pydantic-ai
- pydantic
- httpx
- typer
- rich
- prompt-toolkit

**requirements.txt（API 服务器依赖）：**
- fastapi
- uvicorn
- sqlalchemy
- python-multipart

---

## 🚀 启动服务器

```bash
python src/main.py
```

然后访问：
- API 文档: http://localhost:8000/docs
- 根路径: http://localhost:8000/

---

## ⚠️ 常见错误

### 错误 1: `ModuleNotFoundError: No module named 'pydantic_deep'`
**原因：** 没有以开发模式安装项目

**解决：**
```bash
pip install -e .
```

### 错误 2: `ImportError: cannot import name 'FastMCPToolset'`
**原因：** pydantic-ai 版本太旧

**解决：**
```bash
pip install --upgrade pydantic-ai
```
