# AI 编程教练

面向 **魔兽世界 OJ 大作业** 的本地桌面工具（PyQt6）：按版本管理任务树、中栏保存完整 `code.cpp`、右侧调用 **DeepSeek** 做分节教练与代码验证；Debug 阶段用预置样例在本地比对输出，不一致时再请求模型分析。

## 环境

- Python 3.10+
- 依赖见 `[requirements.txt](requirements.txt)`：`PyQt6`、`openai`（OpenAI 兼容协议访问 DeepSeek）

## 安装与运行

```bash
cd "warcraft-programming-coach"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

（macOS / Linux 将 `activate` 换为 `source .venv/bin/activate`。）

## DeepSeek API

1. 在应用**主页顶部**填写 API Key、选择模型，点击 **「保存」**；程序会做一次连通性检测（`ping_api`），通过后才可进入各题目版本页。
2. 也可预先设置环境变量（仍可在界面覆盖并保存到本机）：

```bash
set DEEPSEEK_API_KEY=你的密钥
set DEEPSEEK_MODEL=deepseek-v4-flash
```

- 默认模型（未设环境变量且未改界面时）为 `**deepseek-v4-flash**`；界面还提供 `deepseek-v4-pro`、`deepseek-chat`。
- 本机配置写入 `**data/app_settings.json**`（已在 `[.gitignore](.gitignore)` 中忽略，勿提交密钥）。

未通过保存后的连通性检测时，**无法进入版本页**（与早期「无 Key 仍可浏览」的占位行为不同）。

## 数据与持久化（概要）


| 路径                             | 说明                                           |
| ------------------------------ | -------------------------------------------- |
| `data/sections.json`           | 可选：根文件内按 `version1`…`version4` 分键的任务结构       |
| `data/versionN/sections.json`  | 若存在则**优先**作为该版本的章节与叶子定义（只读）                  |
| `data/versionN/samples.json`   | Debug 用样例列表（只读；用户经样例录入 UI 填写，AI 或框架落盘为 JSON） |
| `data/versionN/state.json`     | 勾选、树展开、Debug 当前样例索引等                         |
| `data/versionN/code.cpp`       | 中栏完整程序                                       |
| `data/versionN/history/*.json` | 各叶子任务对话历史（不含 system）                         |
| `prompts/versionN.txt`         | 各版本 System Prompt 基底文本                       |


## Cursor / VS Code

仓库可配合 `.vscode/settings.json` 使用项目虚拟环境：创建 `.venv` 并安装依赖后，在命令面板选择解释器为 `.venv/Scripts/python.exe`（Windows）或 `.venv/bin/python`。

## 仓库结构（节选）

- `main.py` / `main_window.py` / `version_page.py` / `chat_widget.py`：应用入口与界面
- `ai_coach.py`：DeepSeek 调用、教学 / 验证 / Debug 分析组装
- `data_manager.py`：JSON、`code.cpp`、历史路径读写
- `sections_loader.py`：`sections.json` 解析与进度分母
- `prompts/`：各版本基底 System Prompt
- `problems/`：题目原文
