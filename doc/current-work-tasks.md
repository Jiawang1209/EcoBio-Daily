# EcoBio Daily 当前工作任务记录

记录日期：2026-04-28

## 当前目标

构建一个生态学与微生物学领域的每日研究进展日报系统。

第一阶段目标不是自动发布，也不是完整网站，而是先跑通 MVP：

```text
获取研究数据
→ 筛选生态学/微生物学相关内容
→ 生成中文 Markdown 日报草稿
→ 人工检查内容质量
```

## 已完成工作

- 已在 `EcoBio-Daily` 根目录初始化 Git 仓库。
- 已创建 Miniforge 环境：`ecobio-daily`。
- 已安装 Python 依赖：
  - `pytest`
  - `pydantic`
  - `pyyaml`
  - `feedparser`
  - `httpx`
  - `jinja2`
- 已创建 MVP 项目结构：
  - `config/`
  - `scripts/`
  - `src/ecobio_daily/`
  - `templates/`
  - `tests/`
  - `data/`
- 已实现基础流水线：
  - 读取数据源配置
  - 读取主题关键词配置
  - 抓取 RSS 数据
  - 标准化为统一 `SourceItem`
  - 去重
  - 按关键词进行主题打分
  - 构建日报结构
  - 渲染中文 Markdown
- 已生成一篇真实数据日报草稿：
  - `2026/04/ecobio_digest_1d_2026-04-28_zh.md`
- 已添加日报质量检查清单：
  - `docs/digest-quality-checklist.md`
- 已添加中文实施计划：
  - `docs/superpowers/plans/2026-04-28-ecology-microbiology-daily-pipeline-zh.md`
- 已完成初始提交：
  - `30664a3 feat: add ecobio daily mvp`
- 已实现日报日期窗口过滤：
  - `--date 2026-04-28`
  - `lookback_days: 2`
  - 保留 `2026-04-26` 到 `2026-04-28` 的条目
- 已修复 bioRxiv RSS 日期解析：
  - 优先使用 `published`
  - 兼容 `updated`
  - 兼容 `prism_publicationdate`
- 已保存每次运行的候选数据：
  - `data/raw/YYYY-MM-DD-items.json`
  - `data/processed/YYYY-MM-DD-scored.json`
- 已完成日期过滤与候选数据保存合并：
  - `471cf5c Merge branch 'codex/date-filtering'`
- 已添加 LLM 配置模板：
  - `config/llm.yaml`
  - API key 通过环境变量配置，不写入仓库

## 当前验证结果

本地测试通过：

```bash
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python -m pytest -q
```

结果：

```text
13 passed
```

真实 RSS 抓取已跑通，并生成日报：

```bash
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-04-28
```

输出：

```text
Wrote digest: 2026/04/ecobio_digest_1d_2026-04-28_zh.md
```

真实运行后生成候选数据：

```text
data/raw/2026-04-28-items.json
data/processed/2026-04-28-scored.json
```

## 当前重要问题

### 1. 当前中文日报还不是高质量中文凝练综述

现在的正文主要来自 RSS 摘要原文，系统只做了：

- 数据获取
- 关键词筛选
- 板块组织
- Markdown 渲染

下一阶段需要接入 LLM，将英文摘要压缩、翻译并改写为真正的中文研究综述。

### 2. 当前数据源还比较少

目前主要数据源是：

- bioRxiv Ecology
- bioRxiv Microbiology
- Nature Ecology & Evolution RSS

后续可以增加：

- PubMed
- Europe PMC
- Crossref
- Semantic Scholar
- PNAS / Nature / Science / Cell 相关 RSS
- 生态学和微生物学重点期刊
- 机构新闻源

## 下一阶段任务建议

### 优先级 P1：接入 LLM 生成中文凝练版

目标：把 RSS 摘要变成真正的中文日报内容。

建议流程：

```text
候选条目
→ 按主题分组
→ LLM 生成 Highlights
→ LLM 生成每个板块的凝练综述
→ 保留 References
```

需要新增：

- `src/ecobio_daily/llm.py`
- `templates/prompts/digest_zh.md.j2`
- LLM mock 测试

已先创建：

- `config/llm.yaml`

### 优先级 P1：优化主题分类

当前关键词匹配比较粗糙。

后续可以改成：

- 关键词加权
- 标题匹配权重大于摘要匹配
- 排除词
- 手动置顶主题
- LLM 相关性评分

### 优先级 P2：增加更多数据源

建议分批增加，不要一次全加。

第一批建议：

- PubMed ecology/microbiology query
- Europe PMC
- Crossref recent works
- 重点期刊 RSS

## 常用命令

激活环境：

```bash
mamba activate ecobio-daily
```

如果 `mamba run` 在当前沙箱里遇到权限问题，可以直接使用环境 Python：

```bash
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python
```

运行测试：

```bash
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python -m pytest -q
```

生成日报：

```bash
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-04-28
```

查看生成日报：

```bash
sed -n '1,220p' 2026/04/ecobio_digest_1d_2026-04-28_zh.md
```

查看 Git 状态：

```bash
git status --short
```

## 当前建议的下一步

下一次继续开发时，建议先做：

1. 接入 LLM，生成真正中文凝练版日报。
2. 优化主题分类，例如标题加权、排除词和 LLM 相关性评分。
3. 增加更多数据源，例如 PubMed、Europe PMC、Crossref 和重点期刊 RSS。

这三步完成后，EcoBio Daily 会从“能获取和整理数据的草稿系统”升级为“可读性较强、覆盖更完整的研究日报系统”。
