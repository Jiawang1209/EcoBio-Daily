# EcoBio Daily

EcoBio Daily 是一个本地优先的生态学与微生物学研究进展日报生成系统。

## 当前能力

- 从配置的数据源抓取最新研究条目，支持 RSS、OpenAlex、Europe PMC、PubMed、bioRxiv API、Crossref、Semantic Scholar 和可选 Web of Science Starter API。
- 聚焦森林、农田、草地土壤微生物，以及微生物驱动的生物地球化学循环。
- 通过关键词、排除词、跨源 DOI 去重、跨日 DOI 去重和 LLM 相关性评分筛选候选文献。
- 使用 LLM 生成中文研究简报，并进行 grounding check；未通过事实核查的条目会在日报中标注。
- 将中英文日报保存到 `YYYY/MM/`，并将运行指标保存到 `data/runs/`，跨日 DOI 状态保存到 `data/state/`。

## 环境

```bash
mamba activate ecobio-daily
```

## 运行方式

```bash
python scripts/run_daily.py --date YYYY-MM-DD --require-llm
python scripts/validate_daily.py --date YYYY-MM-DD
python scripts/check_ops.py --date YYYY-MM-DD --since YYYY-MM-DD
```

LLM 默认启用。需要在本地 `.env` 或 shell 环境中配置：

```bash
CSTCLOUD_API_KEY=...
```

## 文献来源配置

数据源在 `config/sources.yaml` 中维护。RSS 源使用 `url`，学术搜索源使用 `query` 和 `max_results`：

```yaml
sources:
  - id: openalex_ecobio
    name: OpenAlex EcoBio
    type: openalex
    query: ecology OR microbiome OR "microbial ecology"
    max_results: 50

  - id: pubmed_ecobio
    name: PubMed EcoBio
    type: pubmed
    query: '("microbiome"[Title/Abstract] OR "microbial ecology"[Title/Abstract])'
    max_results: 50

  - id: wos_soil_micro
    name: Web of Science Soil Microbiology
    type: wos_starter
    query: 'TS=("soil microbiome" OR "soil microbial community" OR rhizosphere)'
    database: WOS
    api_key_env: WOS_API_KEY
    max_results: 25
```

当前支持的 `type`：

- `rss`
- `openalex`
- `europe_pmc`
- `pubmed`
- `biorxiv_api`
- `crossref`（支持 `query` 或按 `issn` 订阅期刊）
- `semantic_scholar`
- `wos_starter`（可选增强源，需要 Clarivate Web of Science Starter API key）

Web of Science 通常需要 Clarivate API key 和机构权限，因此不作为默认运行依赖。拿到 key 后，可参考 `config/sources.wos.example.yaml` 把 `wos_starter` source 合并进 `config/sources.yaml`，并在本地或 GitHub Actions secret 中配置 `WOS_API_KEY`。

## 自动运行

GitHub Actions 工作流位于 `.github/workflows/daily.yml`，默认北京时间每天 08:00 运行，也支持手动触发。手动触发时可选填 `digest_date`，用于补跑或重跑指定日期。

`.github/workflows/ci.yml` 会在 push 和 pull request 时运行测试，确保代码改动不会破坏日报管线。

日常运维步骤见 `docs/operations.md`。

要让定时任务生成 LLM 中文简报，需要在 GitHub 仓库设置中添加 secret：

```text
CSTCLOUD_API_KEY
```

工作流会先执行 `Validate LLM secret`。若该 secret 缺失，GitHub Actions 会在生成日报前失败并停止提交。随后生成步骤也使用 `--require-llm`，避免把未经过 LLM 筛选与中文简报生成的降级日报写入仓库。

如果启用 Web of Science source，还需要额外添加：

```text
WOS_API_KEY
```

默认 `config/sources.yaml` 不启用 WoS，所以缺少 `WOS_API_KEY` 不会影响当前自动日报。

生成后还会运行 `scripts/validate_daily.py`，确认日报条目数在 5-8 条之间、LLM grounding 没有失败、中英文输出文件结构完整、References 数量足够，并且 `data/state/seen_dois.json` 存在且可解析；不满足条件时不会提交。

工作流会提交：

- `YYYY/MM/` 下的中英文日报。
- `data/runs/YYYY-MM-DD.json` 运行指标。
- `data/state/seen_dois.json` 跨日 DOI 去重状态。

当前默认目标是每天生成 5-8 条高质量文献条目：`config/digest.yaml` 中 `target_items_min: 5`，`max_items: 8`。

## 输出文件

```text
YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md
YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_en.md
data/runs/YYYY-MM-DD.json
data/state/seen_dois.json
```

## 人工发布流程

1. 运行生成器：

   ```bash
   python scripts/run_daily.py --date YYYY-MM-DD --require-llm
   ```

2. 运行提交前校验：

   ```bash
   python scripts/validate_daily.py --date YYYY-MM-DD
   python scripts/summarize_runs.py --since YYYY-MM-DD
   python scripts/check_ops.py --date YYYY-MM-DD --since YYYY-MM-DD
   ```

3. 快速复核生成的中英文 Markdown 和 `data/runs/YYYY-MM-DD.json`。

4. 提交日报与运行状态：

   ```bash
   git add YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md
   git add YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_en.md
   git add -f data/runs/YYYY-MM-DD.json data/state/seen_dois.json
   git commit -m "Add EcoBio daily report: YYYY-MM-DD"
   ```
