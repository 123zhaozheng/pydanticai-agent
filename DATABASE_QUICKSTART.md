# Quick Start: Database Setup

## 🚀 一键初始化数据库

运行以下命令即可完成所有设置：

```bash
python setup_db.py
```

这个脚本会：
1. ✅ 创建所有数据库表（users, roles, departments, mcp_tools, skills等）
2. ✅ 初始化基础数据：
   - 4个角色（admin, developer, data_analyst, user）
   - 3个部门（Engineering, Data Science, Operations）
   - 7个内置工具（read_file, write_file, execute等）
   - 2个示例技能（python_analyzer, sql_optimizer）
   - 4个测试账号
   - Admin权限配置

## 📝 测试账号

| 用户名 | 密码 | 角色 | 部门 |
|--------|------|------|------|
| admin | admin123 | 管理员 | - |
| developer1 | dev123 | 开发者 | Engineering |
| analyst1 | analyst123 | 数据分析师 | Data Science |
| user1 | user123 | 普通用户 | Operations |

## 🗂️ 数据库表结构

### 用户管理
- `users` - 用户表
- `roles` - 角色表
- `departments` - 部门表
- `user_role` - 用户-角色关联表
- `menus` - 菜单表
- `buttons` - 按钮权限表
- `role_menu` - 角色-菜单关联
- `role_button` - 角色-按钮关联

### 工具与技能
- `mcp_tools` - MCP工具表
- `skills` - 技能表
- `role_tool_permissions` - 角色-工具权限
- `role_skill_permissions` - 角色-技能权限
- `department_tool_permissions` - 部门-工具权限
- `department_skill_permissions` - 部门-技能权限

## 🔧 手动步骤（可选）

如果你想分步执行：

### 1. 创建表
```python
from src.database import init_db
init_db()
```

### 2. 仅初始化用户数据
```python
from src.database import SessionLocal
from src.models.seed_user_data import seed_user_management_all

db = SessionLocal()
seed_user_management_all(db)
db.close()
```

### 3. 仅初始化工具/技能数据
```python
from src.database import SessionLocal
from src.models.seed_data import seed_all

db = SessionLocal()
seed_all(db)
db.close()
```

### 4. 完整初始化
```python
from src.seed_all import seed_all
seed_all()
```

## 📊 验证数据

```python
from src.database import SessionLocal
from src.models import User, Role, McpTool, Skill

db = SessionLocal()

# 检查用户
users = db.query(User).all()
print(f"Users: {len(users)}")

# 检查角色
roles = db.query(Role).all()
print(f"Roles: {len(roles)}")

# 检查工具
tools = db.query(McpTool).all()
print(f"Tools: {len(tools)}")

# 检查技能
skills = db.query(Skill).all()
print(f"Skills: {len(skills)}")

db.close()
```

## 🧹 重置数据库

如果需要重新开始：

```bash
# 删除数据库文件（如果使用SQLite）
rm your_database.db

# 重新初始化
python setup_db.py
```

## ⚙️ 配置数据库连接

确保 `src/config.py` 中的 `DATABASE_URL` 配置正确：

```python
# SQLite (默认)
DATABASE_URL = "sqlite:///./pydantic_deep.db"

# PostgreSQL
# DATABASE_URL = "postgresql://user:password@localhost/dbname"

# MySQL
# DATABASE_URL = "mysql+pymysql://user:password@localhost/dbname"
```

## 🎯 下一步

数据库设置完成后，你可以：
1. 启动应用程序
2. 使用测试账号登录
3. 测试工具权限筛选功能
4. 开发 Phase 3: Tool Filter 实现
