# EcoBio Daily 当前工作任务记录

记录日期：2026-05-27

## 项目研究方向（scope 已锁定）

**森林 / 农田 / 草地 土壤微生物 + 微生物驱动的生物地球化学循环。**

明确排除：

- 宿主关联微生物组（人/动物的 gut/oral/skin/airway/maternal/infant）
- 临床微生物学
- 水体 / 大气微生物（不在用户研究方向里）
- 广义生态学（不带微生物维度的生物多样性/全球变化）

未来加 source、改 query、扩 keyword 时都要锚在这个 scope 上，不要扩散。

## 当前管线（P1 LLM 集成已完成 2026-05-27）

```
fetch（15+ sources）
  ├── RSS：bioRxiv ×2，Nature 系 ×4
  ├── API：OpenAlex / Europe PMC / PubMed / Semantic Scholar（已收紧到 soil/terrestrial bgc）
  └── Crossref by ISSN（10 个期刊）
      ↓
日期窗口过滤（lookback_days=2）
  ↓
去重（按 URL）
  ↓
关键词打分（标题 ×2 + 摘要 ×1，topic 级 excludes）
  ↓
LLM 相关性评分（deepseek-v4-flash，threshold >= 6）  ← 命中缓存不重花 token
  ↓
build_digest（按 topic 分组，按相关性排序，取 max_items）
  ↓
LLM 章节简报（deepseek-v3.2，per-section 失败降级，不阻断）  ← 命中缓存
  ↓
渲染全中文 Markdown 日报
  Highlights / 本节要点 / 每条 (summary_zh + why_it_matters + evidence_type + caveat)
```

测试：77 passed。

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

- **PubMed 偶发日期解析失败**：`"2026 May-Jun"` 格式 RSS 时间戳，`fetch.py` 现有 per-source try/except 会跳过该源（不影响整体）
- **Semantic Scholar 无 key 时常被 429**：同样靠 per-source try/except 自动 skip
- **本机 HTTP 代理可能干扰 TLS**：`HTTP_PROXY=http://127.0.0.1:7897`。本地手跑遇到 TLS 错先 unset 代理。CI 不受影响

## 可选的下一阶段（P2 候选）

- **GitHub Actions CI 加 CSTCLOUD_API_KEY secret**：让每日定时跑也走 LLM
- **embedding 去重**：当前只按 URL 去重，跨源同篇论文不同 URL 不会合并。`config/llm.yaml.embeddings` 配置已就绪（bge-large-zh / qwen3-embedding）
- **rerank**：candidate 量大时按 `qwen3-reranker` / `bge-reranker-v2-m3` 重排
- **更多源**：FEMS / Microbiome / ISME J 之类的 Crossref ISSN
- **跨日 dedup**：今天的论文跟昨天的重叠时合并而不是各自一篇

## 常用命令

```bash
# 跑测试
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python -m pytest -q

# 跑日报
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-05-27

# 看 git 状态
git status --short
git log --oneline -10

# 清缓存重跑（验证非缓存路径）
rm -rf data/cache/llm && /Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-05-27
```
