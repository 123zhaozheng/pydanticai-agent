# 运行服务器的方法

## 方法 1: 使用 uv（推荐）
```bash
uv run src/main.py
```

## 方法 2: 使用 Python（从项目根目录）
```bash
# 激活虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 运行服务器
python src/main.py
```

## 方法 3: 使用 Python 模块方式
```bash
python -m src.main
```

---

## ✅ 现在应该可以正常运行了！

访问：
- API 文档: http://localhost:8000/docs
- 根路径: http://localhost:8000/
