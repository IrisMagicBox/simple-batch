# Simple Batch - AI API批处理程序

一个高效的AI API批处理处理程序，支持OpenAI兼容接口的批量请求处理，具备Web UI界面管理、实时监控和性能统计功能。

## 🌟 主要功能

- **批处理管理**: 支持大规模API请求的批处理执行
- **多API配置**: 管理多个AI API配置，支持不同模型和参数
- **并发控制**: 可配置并发数，提升batch效率
- **智能重试**: 失败请求自动重试机制
- **实时监控**: Web界面实时显示处理进度和状态
- **性能统计**: 响应时间、成本分析、请求图表等统计
- **数据导出**: 支持结果导出
- **错误日志**: 详细的错误记录和分析

## 🚀 快速开始

### 从GitHub获取项目

#### 方法一：Git克隆（推荐）
```bash
# 克隆项目
git clone https://github.com/IrisMagicBox/simple-batch.git
```

#### 方法二：下载ZIP
1. 访问项目GitHub页面
2. 点击绿色的 "Code" 按钮
3. 选择 "Download ZIP"
4. 解压到本地目录

### 安装与配置

#### 1. 系统要求
- Python 3.8+
- 操作系统: Windows / macOS / Linux

#### 2. 创建虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```
或者使用清华源安装
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 启动应用

```bash
# 启动应用
python main.py
```

启动成功后，将在控制台看到类似输出：
```
2024-09-02 10:00:00 - main - INFO - 数据库初始化完成
2024-09-02 10:00:00 - main - INFO - 调度器已启动
2024-09-02 10:00:00 - main - INFO - 正在启动UI服务器...
Running on local URL:  http://127.0.0.1:7861
```

在浏览器中访问 http://127.0.0.1:7861 即可使用Web界面。

同样可以指定--port和--host自定义启动端口和地址。



## 🔧 配置说明

### 主要配置项 (settings.py)

```python
# 数据库配置
DATABASE_URL = "batch_processor.db"

# API配置默认值
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 60

# 批处理默认值
DEFAULT_CONCURRENCY = 5      # 默认并发数
DEFAULT_MAX_RETRIES = 3      # 默认重试次数

# 缓存配置
REQUEST_CACHE_BATCH_SIZE = 100        # 批量落库阈值
REQUEST_CACHE_FLUSH_INTERVAL = 5      # 定时刷写间隔(秒)
```

## 📖 使用指南

### 1. 配置API信息
在Web界面中添加AI API配置：
- API密钥 (API Key)
- API基础URL (API Base URL)  
- 模型名称 (Model Name)
- 参数设置 (温度、最大Token数等)

### 2. 创建批处理作业
- 上传包含请求数据的JSON文件
- 选择API配置
- 设置并发数和重试次数
- 启动作业

### 3. 监控进度
- 查看作业状态
- 监控成功/失败请求数
- 查看性能统计图表
- 检查错误日志

### 4. 导出结果
- 支持JSON格式导出
- 包含详细的响应数据和统计信息

## 📝 API请求格式

批处理请求文件应为JSON格式，包含请求数组：

```json
[
  {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ]
  },
  {
    "messages": [
      {"role": "user", "content": "What is Python?"}
    ]
  }
]
```

## 🔍 故障排除

### 常见问题

1. **端口占用**: 如果7861端口被占用，可在 `main.py` 中修改端口号
2. **权限问题**: 确保对项目目录有读写权限
3. **依赖冲突**: 建议使用虚拟环境安装依赖
4. **数据库问题**: 删除 `batch_processor.db` 文件重新初始化，删除前数据库若存在可用数据，可先导出后再删除

### 日志文件
查看 `logs/` 目录下的日志文件获取详细错误信息。

## 🤝 贡献

欢迎提交Issues和Pull Requests来改进项目！

## 📄 许可证

本项目采用 GNU Affero General Public License v3.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

**注意**: 使用前请确保遵守相关AI API服务商的使用条款和限制。