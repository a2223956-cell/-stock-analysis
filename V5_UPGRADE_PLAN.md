# stock-analysis V5 升级方案

## 核心架构: 脚本强制采集 + agent纯分析 + 校验闭环

```
用户: "深度分析XX"

阶段1: deep_analysis.py 强制采集(脚本, 15步)
  → 不可跳过, 每步都有print确认
  → 输出: /tmp/deep_analysis_<code>.json

阶段2: agent 纯分析(读JSON → 写报告)
  → 数据已准备好, 只需解读+评分+建议
  → 不需要自己调API/跑脚本

阶段3: validate_report.py 校验(脚本)
  → 检查报告是否11项完整
  → 缺项→agent补充
```

## deep_analysis.py 新旧步骤对比

| 步骤 | V4(旧) | V5(新) | 状态 |
|------|--------|--------|------|
| Step 0 | ❌ 无 | ✅ 前复权检查(除权记录) | **新增** |
| Step 1 | ✅ 核心数据速览 | ✅ 核心数据速览 | 保留 |
| Step 2 | ✅ 历史复盘 | ✅ 历史复盘 | 保留 |
| Step 3 | ✅ 市场环境 | ✅ 市场环境+板块 | 保留 |
| Step 1E | ❌ 无 | ✅ 板块分析(sector_analysis.py) | **新增** |
| Step 3B | ❌ 无 | ✅ 北向资金 | **新增** |
| Step 4 | ✅ 量价关系 | ✅ 量价关系 | 保留 |
| Step 5 | ✅ 资金流向 | ✅ 资金流向 | 保留 |
| Step 6 | ✅ 均线技术 | ✅ 均线技术 | 保留 |
| Step 7 | ✅ 估值基本面 | ✅ 估值基本面 | 保留 |
| Step 8 | ✅ 综合评分 | ✅ 综合评分 | 保留 |
| Step 9 | ✅ 基础风险(5项) | ✅ 7项风险清单 | **改进** |
| Step 10 | ❌ 无 | ✅ 情绪周期(换手率5档) | **新增** |
| Step 11 | ❌ 无 | ✅ 概念板块完整映射 | **新增** |
| Step 12 | ❌ 无 | ✅ 消息面(news_analysis.py) | **新增** |
| Step 14 | ❌ 无 | ✅ 风险筛查(7项清单) | **新增** |
| Step 15 | ✅ 附录 | ✅ 附录 | 保留 |

V5总计: 15步, 覆盖所有agent容易跳过的步骤。

## JSON输出结构(V5)

```json
{
  "code": "000400",
  "name": "许继电气",
  "version": "5.0",
  "steps_completed": ["step0","step1","step2","step3","step1e","step3b","step4","step5","step6","step10","step7","step11","step12","step8","step14","step15"],
  "quote": {...},
  "ex_right_check": {...},
  "indices": {...},
  "northbound": {...},
  "boards": [...],
  "sector_analysis": {...},
  "klines_30d": [...],
  "indicators": {...},
  "fund_flow": [...],
  "sentiment": {...},
  "concept_blocks": {...},
  "news_analysis": {...},
  "risks": [...],
  "scores": {...}
}
```

## validate_report.py 校验项(11项)

1. 历史复盘 — 报告是否包含"历史复盘"章节
2. 前复权说明 — 是否提及前复权或除权
3. 板块强弱对比 — 个股vs板块(强于/弱于/同步)
4. 量价分析 — 至少3处K线引用
5. 资金流向 — 净流入/净流出数据
6. 情绪周期 — 换手率5档或情绪底部特征
7. 概念纯度评级 — 核心概念+纯度+龙头识别
8. 消息面情绪 — 利好/利空条数+情绪评分
9. 风险筛查 — 至少3项风险
10. 操作建议 — 已持有+未持有两种场景
11. 关键价位交叉验证 — MA5等数值与JSON一致

## SKILL.md精简方案

V5下, SKILL.md应精简为:

**保留(500行)**:
- 红线规则(7条)
- 分析判断方法论(怎么解读数据)
- 评分体系(权重+映射+护栏)
- 输出模板(报告格式)
- 操作建议框架(已持有/未持有/加仓)

**删除(2500+行)**:
- 数据获取代码(API调用方法) — 已由脚本完成
- 脚本执行步骤 — agent不再需要
- pitfalls中的API相关问题
- 大量示例代码和伪代码

## V4 vs V5 对比

| 维度 | V4(模块化) | V5(脚本驱动) |
|------|-----------|-------------|
| 架构 | 4个skill拆分 | 1个skill + 2个脚本 |
| agent职责 | 采数据+分析 | 只做分析 |
| 漏项风险 | 高(漏加载skill) | 低(脚本强制执行) |
| 数据完整性 | 取决于agent | 15步全部执行 |
| 验证机制 | 无 | validate_report.py |
| token消耗 | core仅154行 | skill精简至500行 |
| 可维护性 | 好(模块化) | 好(脚本独立) |

## 验证方法

```bash
# 1. 运行V5数据采集
python3 ~/.hermes/skills/stock-analysis/scripts/deep_analysis.py 000400 许继电气
# 预期: 15/15步完成, JSON包含所有V5字段

# 2. 运行报告校验
python3 ~/.hermes/skills/stock-analysis/scripts/validate_report.py 报告.md /tmp/deep_analysis_000400.json
# 预期: 11/11通过

# 3. 检查JSON版本
python3 -c "import json; d=json.load(open('/tmp/deep_analysis_000400.json')); print(d.get('version'), len(d.get('steps_completed',[])))"
# 预期: 5.0 15
```

## 已知问题

1. Step 11 概念映射API返回400 — 需修复东财datacenter URL
2. Step 3B 北向资金返回raw格式 — 需agent人工解读
3. 风险筛查中5项标记为"需agent搜索确认" — agent需补充搜索

---
*V5升级完成: 2026-08-17*
*文件: deep_analysis.py(975行) + validate_report.py(155行)*
