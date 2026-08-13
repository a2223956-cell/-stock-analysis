# Cron Job Integration Pattern for Stock Analysis Workflow

## Problem Discovered (2026-07-30)

The "A股每日大盘复盘" cron job was running successfully but NOT calling scan_candidate.py, so actionable_pool.txt was never generated automatically.

## Root Cause

The cron job prompt included roles 1-5 (data collection, fund analysis, sector analysis, technical analysis, strategy advisory) but was missing role 6 (stock pool scanning).

## Solution Applied

Updated the cron job prompt to add role 6 with explicit scan_candidate.py execution:

```
━━ 角色6: 📋 选股池扫描(每次必做!) ━━

## 执行步骤:
1. 运行scan_candidate.py扫描unified_pool:
   # 使用mx-moni skill目录
   ~/.hermes/hermes-agent/venv/bin/python3 scan_candidate.py

2. 汇报扫描结果:
   - 扫描总数 + 信号A/B触发数量
   - 🟢建仓候选(评分≥3.5): 代码+名称+评分+缩量比+R:R
   - 🟡观望(2.5-3.4分): 代码+名称+评分
   - 🔴不推荐(<2.5分): 仅报数量
```

## Cron Job IDs

| Job Name | Job ID | Schedule | Purpose |
|----------|--------|----------|---------|
| A股每日大盘复盘 | d3daa84f475b | 35 15 * * 1-5 | Daily复盘 + 扫描 |
| 统一选股池每周更新 | 5094c731bd16 | 0 16 * * 5 | Weekly unified_pool |
| 模拟仓持仓检查-上午 | bc5ddec77069 | 0 10 * * 1-5 | Portfolio check AM |
| 模拟仓持仓检查-下午 | ef005805364f | 30 14 * * 1-5 | Portfolio check PM |

## Execution Flow

```
周五16:00 → generate_unified_pool.py → unified_pool.txt (506只)
每日15:35 → scan_candidate.py → actionable_pool.txt (通常<20只)
每日10:00/14:30 → 持仓检查 + 扫描actionable_pool
```

## Key Files

- unified_pool.txt: ~/.hermes/skills/mx-moni/references/unified_pool.txt
- actionable_pool.txt: ~/.hermes/skills/mx-moni/references/actionable_pool.txt
- scan_candidate.py: ~/.hermes/skills/mx-moni/scripts/scan_candidate.py

## Pitfall

When updating cron job prompts, always verify that ALL required scripts are included. The prompt may look complete but miss critical execution steps like scan_candidate.py.
