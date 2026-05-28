# EcoBio Daily 当前工作任务记录

记录日期：2026-05-28

## 项目研究方向（scope 已锁定）

**森林 / 农田 / 草地 土壤微生物 + 微生物驱动的生物地球化学循环。**

明确排除：

- 宿主关联微生物组（人/动物的 gut/oral/skin/airway/maternal/infant）
- 临床微生物学
- 水体 / 大气微生物（不在用户研究方向里）
- 广义生态学（不带微生物维度的生物多样性/全球变化）

未来加 source、改 query、扩 keyword 时都要锚在这个 scope 上，不要扩散。

## 当前管线（P1 自动化与质量闭环推进中）

```
fetch（15+ sources）
  ├── RSS：bioRxiv ×2，Nature 系 ×4
  ├── API：OpenAlex / Europe PMC / PubMed（已收紧到 soil/terrestrial bgc）
  └── Crossref by ISSN（10 个期刊）
      ↓
日期窗口过滤（lookback_days=2）
  ↓
去重（按 URL）
  ↓
关键词打分（标题 ×2 + 摘要 ×1，topic 级 excludes）
  ↓
LLM 相关性评分（deepseek-v4-flash，threshold >= 6；不足 5 条时用 >=4 的条目回补）  ← 命中缓存不重花 token
  ↓
build_digest（按 topic 分组，按 LLM 评分排序，目标 5-8 条）
  ↓
LLM 章节简报（deepseek-v3.2，per-section 失败降级，不阻断）  ← 命中缓存
  ↓
渲染中英文 Markdown 日报
  Highlights / 本节要点 / 每条 (summary_zh + why_it_matters + evidence_type + caveat)
  ↓
保存 data/runs/YYYY-MM-DD.json 与 data/state/seen_dois.json
```

测试：当前期望 `118+` passed；每次改动后以本机 pytest 输出为准。

## 2026-05-28 接管维护进展

- GitHub Actions 已补齐 `CSTCLOUD_API_KEY` secret 注入。
- GitHub Actions 先执行 `Validate LLM secret`，随后使用 `--require-llm`；缺少 `CSTCLOUD_API_KEY` 时会在生成日报前失败并停止提交，避免降级日报进入仓库。
- GitHub Actions 已改为提交日报、`data/runs` 和 `data/state`。
- GitHub Actions 在提交前运行 `scripts/validate_daily.py`，检查 5-8 条目标、grounding 失败数和中英文输出文件。
- `.github/workflows/ci.yml` 已添加 push / pull request 测试工作流，持续验证 pytest 全绿。
- Daily workflow 的 `workflow_dispatch` 已支持可选 `digest_date`，补跑/重跑时生成、校验、提交会使用同一个日期变量。
- Daily workflow 已设置 `concurrency.group: ecobio-daily`，定时运行和手动补跑会排队串行，避免同时写 `data/state`。
- Daily workflow 在提交前会 `git pull --rebase --autostash origin main`，避免 LLM 生成期间远端 `main` 更新导致最后 `git push` 被拒绝。
- `docs/operations.md` 已添加日常运维手册，覆盖 secret 配置、手动触发、validator、常见失败与排查入口。
- `scripts/summarize_runs.py` 已添加，用于查看 `data/runs` 历史并验证某日期后的连续运行是否都满足 5-8 条和 grounding 要求。
- 因 `data/runs/*` 和 `data/state/*` 被 `.gitignore` 忽略，workflow 使用 `git add -f data/runs data/state` 强制提交运行指标和跨日 DOI 状态。
- `config/digest.yaml` 已设置：
  - `target_items_min: 5`
  - `max_items: 8`
- `config/llm.yaml` 已将 `budget.max_items_per_run` 调到 `24`，让 LLM 有更大的候选池。
- LLM 筛选策略：先保留 `llm_score >= 6`，如果少于 5 条，则用 `llm_score >= 4` 的候选按分数回补。
- README 已补充 GitHub Secret、自动运行和提交文件说明。

## P1 LLM 集成产出（2026-05-27 收尾）

按 5 个串行 goal（`doc/goals/G1.md` ~ `G5.md`）+ 1 个收尾迭代，7 个 commit：

```
9cd1c4a feat: chinese-ify top-level Highlights via llm_brief_item
5a1ac31 feat: render LLM Chinese brief in daily digest per G5
03350e2 feat: add Chinese digest section generator per G4
e9fd899 feat: cache LLM responses on disk per G3
f77d7c8 feat: wire LLM relevance scoring into pipeline per G2
4be5b10 feat: add LLM relevance scoring per G1
24aadbb feat: add LLM client foundation with CSTCloud gateway
```

关键文件：

```
src/ecobio_daily/llm.py              ← LLMClient（OpenAI 兼容 + 缓存）
src/ecobio_daily/llm_scoring.py      ← LLM 相关性评分
src/ecobio_daily/llm_digest.py       ← LLM 中文简报（含 markdown 围栏剥离）
src/ecobio_daily/llm_cache.py        ← 内容寻址 JSON 缓存
templates/prompts/relevance_score.md.j2
templates/prompts/digest_section_zh_system.md.j2
templates/prompts/digest_section_zh_user.md.j2
templates/digest_zh.md.j2            ← 已改成 LLM brief 优先 + 老路径降级
config/llm.yaml                       ← CSTCloud uni-api，已 enabled
.env (gitignored)                     ← CSTCLOUD_API_KEY
```

性能：冷跑（无缓存）≈ 2m54s，热跑（缓存命中）≈ 1m12s。

## 当前已知问题

- **Semantic Scholar 无 key 时常被 429**：已从默认 sources 中移除；后续有 API key 再恢复。
- **本机 HTTP 代理可能干扰 TLS**：`HTTP_PROXY=http://127.0.0.1:7897`。本地手跑遇到 TLS 错先 unset 代理。CI 不受影响
- **LLM 产出数量仍需观察**：目标改为 5-8 条，但需要连续几天运行 metrics 证明稳定。

## 下一阶段（P2 候选）

- **连续运行观察**：检查 `data/runs/*.json` 中 `llm_relevance.kept` 是否稳定在 5-8。
- **embedding 去重**：当前只按 URL 去重，跨源同篇论文不同 URL 不会合并。`config/llm.yaml.embeddings` 配置已就绪（bge-large-zh / qwen3-embedding）
- **rerank**：candidate 量大时按 `qwen3-reranker` / `bge-reranker-v2-m3` 重排
- **更多源**：FEMS / Microbiome / ISME J 之类的 Crossref ISSN
- **Web of Science**：具备 Clarivate API key 与机构权限后作为增强来源。

## 常用命令

```bash
# 跑测试
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python -m pytest -q

# 跑日报
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-05-28

# 看 git 状态
git status --short
git log --oneline -10

# 清缓存重跑（验证非缓存路径）
rm -rf data/cache/llm && /Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-05-27
```
