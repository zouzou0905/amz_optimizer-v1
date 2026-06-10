# 项目结构说明

本项目是一个分阶段的 Amazon 商品优化流程，主要覆盖商品信息抓取、关键词语义提取、竞品数据采集和 AI Listing 优化。

运行环境：Python 3.11。当前项目内的 `venv/` 是 Python 3.11.2。

## 当前目录

- `cli.py`：统一命令入口，支持 `stage1/stage2/stage3/stage4/all`。
- `app.py`：Stage 1 的应用编排逻辑。
- `config.py`：项目路径、模型名称和环境变量配置。
- `core/`：可复用的核心业务模块。
  - `scraper.py`：Playwright 商品标题和图片抓取逻辑。
  - `data_handler.py`：Excel 读取和增量保存。
  - `organizer.py`：Stage 2 关键词语义提取和断点续跑。
  - `market.py`：UK/DE 市场配置。
- `scripts/`：真实阶段脚本。
  - `stage1_scrape_products.py`
  - `stage2_build_keyword_sheet.py`
  - `stage3_collect_competitors.py`
  - `stage4_ai_optimize_listing.py`
- `market/`：独立市场分析工具。
- `data/input/`：原始输入文件，默认是 `my-products.xlsx`。
- `data/output/`：所有阶段输出文件。
  - `my-products_stage1.xlsx`
  - `my-products_stage2.xlsx`
  - `my-products_stage3.xlsx`
  - `my-products_stage4.xlsx`

## 推荐入口

项目已清理旧入口，统一使用 `cli.py`：

```powershell
python cli.py stage1
python cli.py stage2 --market UK
python cli.py stage3 --market UK
python cli.py stage4 --market UK
python cli.py all --market UK
```

德国市场：

```powershell
python cli.py all --market DE
```

## 配置方式

密钥从环境变量或 `.env` 文件读取：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`

可以参考 `.env.example` 创建本地 `.env`。

## 后续建议

1. 为 CLI 增加 `--input`、`--output`、`--limit` 参数，方便测试和多文件处理。
2. 增加基础测试，覆盖 CLI 参数、市场配置、Stage 2 关键词兜底逻辑。
3. 明确哪些 Excel 示例数据可以提交，哪些真实业务数据应加入 `.gitignore`。
