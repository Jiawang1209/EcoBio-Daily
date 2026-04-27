# EcoBio Daily

EcoBio Daily 是一个本地优先的生态学与微生物学研究进展日报生成系统。

## 第一版能力

- 从配置的数据源抓取最新研究条目。
- 按生态学和微生物学主题进行关键词筛选。
- 选择高相关内容生成中文 Markdown 日报。
- 将日报保存到 `YYYY/MM/` 目录。

## 环境

```bash
mamba activate ecobio-daily
```

## 运行方式

```bash
python scripts/run_daily.py --date 2026-04-28
```

## 输出文件

```text
2026/04/ecobio_digest_1d_2026-04-28_zh.md
```

## 人工发布流程

1. 运行生成器：

   ```bash
   python scripts/run_daily.py --date YYYY-MM-DD
   ```

2. 根据 `docs/digest-quality-checklist.md` 复核生成的 Markdown。

3. 提交日报：

   ```bash
   git add YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md
   git commit -m "Add EcoBio daily report: YYYY-MM-DD"
   ```
