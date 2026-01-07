# X Feed Digest

[English](README.md) | 中文

> 将你的 X/Twitter 关注列表转化为 AI 精选的每日摘要

X Feed Digest 是一个开源工具，可以从你的 X/Twitter 关注列表中获取推文，并使用 AI 生成智能摘要。它利用 Grok 的实时 X 数据访问能力来收集推文，并使用 Claude 的分析能力生成编辑级别的精选摘要。

## 功能特性

- **CSV 上传**：导入从 X/Twitter 导出的关注列表 CSV 文件
- **实时推文获取**：使用 Grok API 获取过去 24 小时的推文
- **多线程处理**：并发批处理，加速数据收集
- **AI 智能摘要**：Claude 生成分类整理的精选摘要
- **历史记录**：追踪和查看所有历史任务
- **现代化界面**：简洁的 Vue 3 界面，实时进度显示

## 工作流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  上传 CSV   │ ──▶ │   Grok API  │ ──▶ │  Claude AI  │ ──▶ │   摘要输出  │
│  (关注列表) │     │  (获取24h)  │     │   (总结)    │     │            │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **上传** 你的 X/Twitter 关注列表 CSV（从 X 导出）
2. **获取** 过去 24 小时内每个用户的推文（通过 Grok）
3. **分析** 使用 Claude 和编辑级 Prompt 分析收集到的推文
4. **输出** 结构化的摘要，包含亮点、分类和推荐

## 技术栈

### 后端
- **Python 3.10+** + FastAPI
- **OpenAI 兼容 API 客户端**
- **ThreadPoolExecutor** 并发处理
- **YAML 配置**

### 前端
- **Vue 3** Composition API
- **TypeScript**
- **Pinia** 状态管理
- **Element Plus** UI 组件
- **Vite** 构建工具

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Grok 和 Claude API 访问权限（或兼容的 API 端点）

### 安装

1. **克隆仓库**
```bash
git clone https://github.com/ChineseLsh/x-feed-digest.git
cd x-feed-digest
```

2. **安装后端依赖**
```bash
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd frontend
npm install
cd ..
```

4. **配置 API 提供商**

复制示例配置并添加你的 API 密钥：
```bash
cp config/providers.example.yaml config/providers.yaml
```

编辑 `config/providers.yaml`：
```yaml
providers:
  grok:
    type: openai_compatible
    api_key: 你的-grok-api-key
    base_url: https://api.x.ai/v1
    model: grok-2

  claude:
    type: openai_compatible
    api_key: 你的-claude-api-key
    base_url: https://api.anthropic.com/v1
    model: claude-sonnet-4-20250514
```

### 运行

1. **启动后端**
```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 5001 --reload
```

2. **启动前端**（新终端）
```bash
cd frontend
npm run dev
```

3. **打开浏览器** 访问 `http://localhost:3000`

## 配置说明

### `config/app.yaml`

```yaml
storage:
  root: data
  uploads: data/uploads      # 上传的 CSV 文件
  outputs: data/outputs      # 获取的推文 CSV
  summaries: data/summaries  # 生成的摘要
  jobs: data/jobs            # 任务状态文件

batching:
  default_batch_size: 10     # 每批用户数
  max_batch_size: 50         # 最大批次大小
  max_workers: 5             # API 调用并发线程数

retry:
  max_retries: 3             # 失败重试次数
  backoff_base_s: 0.5        # 基础退避时间
  backoff_max_s: 8.0         # 最大退避时间

grok:
  provider: grok             # providers.yaml 中的提供商名称
  timeout_s: 120             # 请求超时
  temperature: 0.2           # LLM 温度

claude:
  provider: claude
  timeout_s: 120
  temperature: 0.3
```

## CSV 格式

输入 CSV 应包含你的 X/Twitter 关注列表。必需列：
- `Handle` 或 `username` 或 `screen_name` - Twitter 用户名

可选列（传递给 Grok 作为上下文）：
- `Name` - 显示名称
- `Bio` - 用户简介
- `Location` - 位置
- `FollowersCount` - 粉丝数
- `FollowingCount` - 关注数

示例：
```csv
Handle,Name,Bio,FollowersCount
elonmusk,Elon Musk,Mars & Cars,180000000
sama,Sam Altman,OpenAI CEO,3000000
```

## API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/jobs` | 创建新的摘要任务（multipart 表单上传 CSV） |
| `GET` | `/api/jobs` | 获取所有历史任务列表 |
| `GET` | `/api/jobs/{job_id}` | 获取任务状态 |
| `GET` | `/api/jobs/{job_id}/summary` | 获取生成的摘要文本 |
| `GET` | `/api/jobs/{job_id}/download` | 下载推文 CSV |

## 摘要输出格式

AI 生成的结构化摘要包括：

1. **今日要点摘要（Deep Brief）** - 100-200 字的精华综述
2. **编辑精选（Editor's Choice）** - 3-5 条分类整理的精华内容：
   - 🔧 硬核工具 - 新的开发工具和实用程序
   - 💡 深度洞察 - 深度技术或行业见解
   - 📰 重大动态 - 重要公告和更新
   - 📚 优质资源 - 学习材料和参考资料
3. **高价值推文完整清单** - 所有有价值的推文及评级（1-3 星）

## 开发

### 后端开发
```bash
# 带自动重载运行
python -m uvicorn backend.app:app --reload --port 5001
```

### 前端开发
```bash
cd frontend

# 开发服务器
npm run dev

# 生产构建
npm run build
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request
