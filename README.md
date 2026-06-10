# Amazon Optimizer

Amazon 商品优化流程工具，用于分阶段完成商品信息抓取、关键词表整理、竞品数据采集和 AI Listing 优化。

## 运行环境

- Python 3.11
- Playwright Chromium
- DeepSeek API Key

项目推荐使用本地虚拟环境 `venv/`。当前项目约定 Python 版本见 `.python-version`。

## 新电脑首次安装

### Windows PowerShell

在项目根目录执行：

```powershell
py -3.11 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m playwright install chromium
```

检查 Python 版本：

```powershell
venv\Scripts\python.exe --version
```

### PyCharm 终端

先在 PyCharm 中选择项目解释器：

```text
Settings > Project > Python Interpreter > Add Interpreter > Existing
```

选择：

```text
F:\amazon_optimizer-v1\venv\Scripts\python.exe
```

如果还没有 `venv/`，可以在 PyCharm Terminal 中执行：

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

如果 PyCharm 已经自动激活虚拟环境，终端前面通常会出现 `(venv)`，这时也可以用：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### VS Code 终端

先选择解释器：

```text
Ctrl+Shift+P > Python: Select Interpreter > .\venv\Scripts\python.exe
```

如果还没有 `venv/`，在 VS Code Terminal 中执行：

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

如果 VS Code 已经自动激活虚拟环境，可以直接执行：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 环境变量

复制 `.env.example` 为 `.env`，并填写 DeepSeek 密钥：

```env
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.env` 不要提交到 Git。

## 输入文件

默认输入文件：

```text
data/input/my-products.xlsx
```

主要路径配置在 `config.py`：

- `DEFAULT_INPUT_FILE`
- `STAGE1_OUTPUT_FILE`
- `STAGE2_OUTPUT_FILE`
- `STAGE3_OUTPUT_FILE`
- `STAGE4_OUTPUT_FILE`

## 推荐运行方式

现在推荐统一使用 `cli.py` 作为命令入口。

### Windows PowerShell

```powershell
venv\Scripts\python.exe cli.py stage1
venv\Scripts\python.exe cli.py stage2 --market UK
venv\Scripts\python.exe cli.py stage3 --market UK
venv\Scripts\python.exe cli.py stage4 --market UK
```

一口气跑完整流程：

```powershell
venv\Scripts\python.exe cli.py all --market UK
```

### PyCharm 终端

如果 PyCharm 已经激活项目 `venv`：

```powershell
python cli.py stage1
python cli.py stage2 --market UK
python cli.py stage3 --market UK
python cli.py stage4 --market UK
```

如果没有自动激活虚拟环境：

```powershell
.\venv\Scripts\python.exe cli.py stage1
.\venv\Scripts\python.exe cli.py stage2 --market UK
.\venv\Scripts\python.exe cli.py stage3 --market UK
.\venv\Scripts\python.exe cli.py stage4 --market UK
```

### VS Code 终端

如果 VS Code 已经选择并激活 `venv`：

```powershell
python cli.py stage1
python cli.py stage2 --market UK
python cli.py stage3 --market UK
python cli.py stage4 --market UK
```

如果没有自动激活虚拟环境：

```powershell
.\venv\Scripts\python.exe cli.py stage1
.\venv\Scripts\python.exe cli.py stage2 --market UK
.\venv\Scripts\python.exe cli.py stage3 --market UK
.\venv\Scripts\python.exe cli.py stage4 --market UK
```

### VS Code 里最简写法

如果 VS Code 已经激活 `venv`，直接使用下面四步即可：

```powershell
python cli.py stage1
python cli.py stage2 --market UK
python cli.py stage3 --market UK
python cli.py stage4 --market UK
```

德国市场只需要把 `UK` 换成 `DE`：

```powershell
python cli.py stage1
python cli.py stage2 --market DE
python cli.py stage3 --market DE
python cli.py stage4 --market DE
```

现在旧入口已经清理，项目统一使用 `cli.py`。

## 阶段说明

### Stage 1：抓取商品标题和图片

```powershell
python cli.py stage1
```

默认输入：

```text
data/input/my-products.xlsx
```

默认输出：

```text
data/output/my-products_stage1.xlsx
```

### Stage 2：AI 语义提词并生成关键词分析表

```powershell
python cli.py stage2 --market UK
python cli.py stage2 --market DE
```

默认输出：

```text
data/output/my-products_stage2.xlsx
```

Stage 2 默认使用 DeepSeek 根据标题语义提取 3 个 Amazon 搜索关键词：

- `--market UK`：输出英语关键词，适配 Amazon UK 搜索习惯。
- `--market DE`：输出德语关键词，适配 Amazon.de 搜索习惯。

如果 DeepSeek 调用失败或没有配置 `DEEPSEEK_API_KEY`，程序会自动回退到本地规则切割，不会中断流程。

Stage 2 支持断点续跑：

- 如果输出文件已经存在，会按 `ASIN` 恢复已有的 `关键词1/关键词2/关键词3`。
- 已经有 3 个关键词的行会显示 `[跳过已有]`，不会重复调用 AI。
- 每处理完一行都会立即保存，避免中途失败后全部重跑。
- `_error` 列会记录本行是否使用了规则兜底，例如 `AI失败后兜底` 或 `AI不可用`。

### Stage 3：采集竞品详情

```powershell
python cli.py stage3 --market UK
python cli.py stage3 --market DE
```

这个阶段会打开 Playwright 浏览器窗口。第一次运行某个市场时，如果没有对应状态文件，程序会提示你手动设置 Amazon 配送地址，然后按回车继续。

相关状态文件：

- `amazon_uk_state.json`
- `amazon_de_state.json`

默认输出：

```text
data/output/my-products_stage3.xlsx
```

### Stage 4：AI Listing 优化

```powershell
python cli.py stage4 --market UK
python cli.py stage4 --market DE
```

该阶段会调用 DeepSeek，根据 Stage 3 的竞品数据生成最终优化结果。

默认输出：

```text
data/output/my-products_stage4.xlsx
```

Stage 4 的失败处理：

- 每个 ASIN 最多自动尝试 3 次。
- 三次失败之间分别等待 5 秒和 10 秒后重试。
- 连续失败后会写入 `分析状态=失败`、`尝试次数` 和 `错误信息`。
- 失败不会中断其他 ASIN 的处理。
- 下次重新运行 Stage 4 时，只跳过 `分析状态=成功` 的记录。
- 历史失败记录会自动重新分析，成功后替换原来的失败结果，不会产生重复行。
- 完整运行和报错信息同时记录在 `logs/stage4.log`。

## 市场切换

不再需要手动改代码，直接通过 `--market` 参数切换：

```powershell
python cli.py stage2 --market UK
python cli.py stage3 --market UK
python cli.py stage4 --market UK
```

或：

```powershell
python cli.py stage2 --market DE
python cli.py stage3 --market DE
python cli.py stage4 --market DE
```

如果运行完整流程：

```powershell
python cli.py all --market UK
python cli.py all --market DE
```

## 日志文件

通过 `cli.py` 运行任意阶段时，终端输出会同时写入日志文件：

- `logs/stage1.log`
- `logs/stage2.log`
- `logs/stage3.log`
- `logs/stage4.log`

例如运行：

```powershell
python cli.py stage2 --market UK
```

终端会显示：

```text
日志文件: logs\stage2.log
```

之后可以打开 `logs/stage2.log` 查看完整记录，包括：

- 当前使用 AI 还是规则兜底
- 每一行提取出的关键词
- 已跳过的断点续跑行
- 报错堆栈信息

日志文件用于本地排错，默认不会提交到 Git。

## 目录说明

- `cli.py`：统一命令入口。
- `app.py`：Stage 1 应用编排。
- `config.py`：项目路径和环境变量配置。
- `core/`：核心业务模块。
- `scripts/`：真实阶段脚本。
- `market/`：独立市场分析工具。
- `data/input/`：原始输入文件。
- `data/output/`：Stage 1 至 Stage 4 的输出文件。

## Git 提交前建议检查

```powershell
git status --short
venv\Scripts\python.exe cli.py --help
venv\Scripts\python.exe -c "import cli; print('imports ok')"
```

不要提交：

- `.env`
- `venv/`
- `__pycache__/`
- `logs/*.log`
- Excel 临时文件，例如 `~$xxx.xlsx`
