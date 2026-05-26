# EcoBio Daily 当前工作任务记录

记录日期：2026-05-26

## 项目研究方向（重要：scope 已锁定）

**森林 / 农田 / 草地 土壤微生物 + 微生物驱动的生物地球化学循环。**

明确排除：
- 宿主关联微生物组（人/动物的 gut/oral/skin/airway/maternal/infant）
- 临床微生物学
- 水体 / 大气微生物（不在用户研究方向里）
- 广义生态学（不带微生物维度的生物多样性/全球变化）

未来加 source、改 query、扩 keyword 时都要锚在这个 scope 上，不要扩散。

## 当前管线状态

```
15+ 数据源
  ├── RSS：bioRxiv ×2，Nature 系 ×4
  ├── API（query 已收紧到 soil/terrestrial bgc）：
  │     OpenAlex / Europe PMC / PubMed / Semantic Scholar
  └── Crossref by ISSN（10 个期刊）：
        Ecology Letters / GCB / Microbiome / Trends in Micro / TREE
        Soil Biology & Biochemistry / Applied Soil Ecology /
        FEMS Microbiology Ecology / Biology and Fertility of Soils /
        Agriculture, Ecosystems & Environment
        ↓
日期窗口过滤（lookback_days=2）
  ↓
去重（按 URL）
  ↓
主题打分（标题 ×2 + 摘要 ×1，topic 级 excludes）
  ↓
5 个主题：
  forest_soil_microbiology / cropland_soil_microbiology /
  grassland_soil_microbiology / soil_biogeochemistry / env_micro_methods
  ↓
min_relevance_score=1（源端已主筛，topic 只做分类）
  ↓
渲染中文 Markdown 日报
```

测试：23 passed。

实测精度（Live 数据）：
- PubMed soil_micro query：6/10 通过，全部为土壤相关
- Crossref Soil Biology & Biochemistry：7/8 通过

## 已完成（按 commit 倒序）

```
613260c config: narrow scope to forest/cropland/grassland soil microbiology
f5e3338 config: refocus pipeline on pure environmental microbiology
06aa7ca config: expand topic keywords and exclude clinical microbiome noise
1fbd9f7 feat: weight title keyword hits and support per-topic excludes
8e9e2f5 config: expand sources with key ecology and microbiology journals
7d569ce feat: add Crossref and Semantic Scholar source backends
6414634 chore: ignore local .omc session state
d718073 Add EcoBio daily report: 2026-05-25
351097e ci: add daily digest generation workflow
ef9cc7d docs: refresh current work tasks log
5038f22 feat: extend literature sources and add per-source resilience
```

## 当前瓶颈

1. **日报正文仍是英文 RSS 摘要直拼**，不是中文研究简报。
2. **关键词系统已到精度上限**。边界论文（土壤化学 vs 土壤微生物、农药 vs 微生物生防）无法靠关键词精准判定。
3. **没有相关性评分**，只有"命中即通过"的硬阈值。

## 下一步（P1）：接入 LLM

目标：用 LLM 同时解决"相关性评分"和"中文凝练"两件事。`config/llm.yaml` 已配好 DeepSeek / Kimi / Qwen / OpenAI profile，只差代码和 API key。

### 设计草图

**文件：**

```
src/ecobio_daily/llm.py          ← 新增，包装 OpenAI-compatible client
templates/prompts/                ← 新增目录
  ├── relevance_score.md.j2       ← 评相关性的 prompt
  └── digest_section_zh.md.j2     ← 写中文研究简报的 prompt
tests/test_llm.py                 ← 新增，mock 网络调用的单元测试
tests/fixtures/llm_responses/     ← 录制 LLM 响应（脱敏后）做回归
```

**流程：**

```
打分通过的候选条目
  → LLM 评相关性（0–10 分，标准：soil + microbe + forest/cropland/grassland）
    使用 deepseek_fast，便宜，最多 12 条
  → 过 relevance >= 6 的 8–12 条
  → 按 topic_id 分组
  → 每个 topic 调一次 LLM 写中文研究简报
    使用 kimi_long_context 或 qwen_balanced（中文 + 长上下文）
    输出 JSON：{ section_title, highlights, items: [{title, summary_zh, why_it_matters, caveat}] }
  → 渲染进 templates/digest_zh.md.j2
```

**关键设计要点：**

1. **API key 走环境变量**（`config/llm.yaml` 已经是这个约定）。`llm.py` 启动时检查 key，缺 key 时 fall back 到 `use_rss_summary`（保留旧行为）。

2. **Fallback 策略**：单条 LLM 调用失败时该条目降级用 RSS 摘要原文，整个日报不中断。错误信息按 `llm.yaml.fallback.error_dir` 写到 `data/cache/llm_errors/<date>/`。

3. **缓存**：按 `(item.id, prompt_template_version)` 哈希缓存到 `data/cache/llm/`，重跑同一天不重复花 token。`llm.yaml.budget.cache_llm_outputs: true` 已经预留。

4. **JSON 结构化输出**：用 `response_format=json_object`（DeepSeek/Kimi/Qwen 都支持），避免解析 Markdown 时翻车。

5. **prompt 设计**：
   - 相关性 prompt 把 scope（森林/农田/草地土壤微生物 + bgc）和排除项（gut/clinical/marine/atmosphere）写死
   - 简报 prompt 强调：区分实验/模型/综述，保留研究对象/尺度/方法/限制，不夸大相关性

6. **TDD**：用 fixture（录制过的 JSON 响应）做单元测试，不打真实 API。Mock `httpx.post`。

### 启动顺序建议

1. **先做 `llm.py` 的 client wrapper**（OpenAI-compatible，30 行）+ 一个最小 prompt + mock 测试。
2. **接相关性评分**，先只对已通过关键词筛的候选评分，看新 ranking 是否合理。
3. **再接中文简报**，逐个 topic 渲染。
4. **接 fallback / 缓存 / 错误处理**。
5. **跑一次真实日报对比新旧差异**。

### 需要先确认的事

- **选哪个 model profile 做相关性**？默认 `deepseek_fast`（便宜、快、足够），用户可在 `llm.yaml.routing.relevance_scoring` 里改。
- **选哪个 model profile 做中文简报**？默认 `kimi_long_context`（中文质量好、长上下文）或 `qwen_balanced`（中文好、便宜）。下次决定时再选。
- **DEEPSEEK_API_KEY / MOONSHOT_API_KEY / DASHSCOPE_API_KEY** 哪个先配？至少要一个。

## 常用命令

```bash
# 激活环境（或直接用绝对路径 Python）
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python

# 跑测试
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python -m pytest -q

# 跑日报（任意日期）
/Users/liuyue/miniforge3/envs/ecobio-daily/bin/python scripts/run_daily.py --date 2026-05-26

# 看 git 状态
git status --short
git log --oneline -10
```

## 已知问题

- **Semantic Scholar 无 key 时常被 429**：`pipeline.py` 的 per-source try/except 会自动 skip。等后续接 LLM 时再决定要不要顺手加上 S2 API key。
- **本机 HTTP 代理可能干扰 TLS**：`HTTP_PROXY=http://127.0.0.1:7897`。如果本地手动跑遇到 TLS 错误，先 unset 代理变量再试。CI（GitHub Actions）不受影响。
