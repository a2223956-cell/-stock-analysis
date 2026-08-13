# Stock Analysis Framework

融合两套A股分析系统精华的统一股票分析方法论。

---

## 版本历史

### V4.0.0 (2026-08-13) ← 当前版本

**核心变更: 拆分为4个子skill, 解决长skill截断问题**

| Skill | 行数 | 职责 | 何时加载 |
|-------|------|------|----------|
| `stock-analysis-core` | 154行 | 红线规则+核心理念+流程概览+评分引用 | 每次分析必加载 |
| `stock-analysis-deep` | 538行 | 步骤-1历史复盘+9步法详细流程+评分体系+10节输出模板 | 用户说"深度分析XX" |
| `stock-analysis-templates` | 1121行 | 持仓分析/新仓评估/加仓决策/暴跌复盘/多票对比等模板 | 对应场景触发 |
| `stock-analysis-reference` | 2144行+33文件 | 技术形态速查+数据源参考+50+条历史教训 | 需要参考时 |

**V4.0 改进清单:**
- ✅ 解决4025行单体skill被截断的问题(核心规则在前154行,一定不截断)
- ✅ 统一0-100分制评分体系(删除旧0-5分制)
- ✅ 清除所有`watchlist.json`/`focus_items.json`残留引用
- ✅ `a-stock-data`清理为纯数据源(不再包含分析方法论)
- ✅ 跨skill引用路径修正(`stock-analysis-reference/references/...`)
- ✅ 深度分析报告统一为10节标准模板(core/deep/templates一致)
- ✅ 量价评分(X/5)→综合评分(0-100)换算说明
- ✅ Codex 3轮审查16/16通过

**迁移指南:**
```bash
# 回滚到旧版
git checkout v3-backup
```

### V3.1.0 (2026-08-06)

- 新增`deep_analysis.py` 10步数据采集器
- 5维度100分制评分
- 3日组合形态检测(双针探底/看涨吞没/放量滞涨)
- 资金流API镜像重试(3域名)
- Codex审核修复24项

### V3.0 (2026-07-27)

- 波浪理论/缠论可量化部分整合
- Fibonacci回撤位(38.2%/50%/61.8%/78.6%)
- MACD背驰检测(顶背离/底背离)

### V2.2 (2026-07-27)

- 情绪周期分析、预期差分析、龙头识别框架
- 事件驱动分类、市场状态动态权重、箱体策略

---

## 分析流程: 9步法

| 步骤 | 内容 | 数据源 | 所在skill |
|------|------|--------|-----------|
| -1 历史复盘 | 检查stock-reports目录,验证上次结论 | 文件系统 | core+deep |
| 1 前复权 | 除权记录+手动复权计算 | mootdx xdxr | deep |
| **2 市场环境** | **大盘+北向+板块TOP+个股所属板块(sector_analysis.py)** | **腾讯+东财+脚本** | deep |
| 3 量价关系 | 逐日K线+成交量→判断主力阶段+3日组合形态 | 东财K线 | deep |
| 4 资金流向 | 主力/散户/超大单20日逐日 | 东财push2his | deep |
| 5 均线技术 | MA5/10/20/30+偏离度+排列+Fibonacci+MACD背驰 | K线计算 | deep |
| 6 情绪周期 | 换手率量化+情绪底部/顶部特征 | 腾讯行情 | deep |
| 7 估值基本面 | PE/PB/PEG+预期差分析 | 腾讯+akshare | deep |
| 8 概念板块 | 完整概念映射+龙头识别+核心vs蹭概念 | 同花顺+东财 | deep |
| 9 消息面 | 事件驱动分类+利好兑现出货+风险筛查 | news_analysis.py | deep |

---

## 文件结构

```
stock-analysis/
├── stock-analysis-core/           # V4.0 核心框架
│   └── SKILL.md                   # 154行: 红线+理念+流程+评分引用
├── stock-analysis-deep/           # V4.0 深度分析
│   └── SKILL.md                   # 538行: 步骤-1+9步法+评分+10节模板
├── stock-analysis-templates/      # V4.0 分析模板
│   └── SKILL.md                   # 1121行: 持仓/买入/加仓/暴跌/多票对比
├── stock-analysis-reference/      # V4.0 参考手册
│   ├── SKILL.md                   # 2144行: 技术形态+数据源+50+条教训
│   └── references/                # 33个参考文件
│       ├── kline-data-fabrication-case-study.md
│       ├── strategy-improvements-20260721.md
│       ├── trading-strategy-v5.md
│       ├── pitfalls.md
│       └── ... (共33个)
├── scripts/                       # 分析脚本
│   ├── deep_analysis.py           # 10步数据采集器
│   └── news_analysis.py           # 新闻情绪分析
├── strategies/                    # 15个策略YAML
├── templates/                     # 输出模板
└── v3-backup/                     # V3.x旧版备份(git分支)
```

---

## 评分体系(100分制)

| 维度 | 权重 | 说明 | 数据源 |
|------|------|------|--------|
| 量价关系 | 30% | 主力行为阶段+量价评分(步骤3) | K线+成交量 |
| 技术面 | 25% | 均线排列(MA5/10/20/30)+趋势强度 | K线计算 |
| 资金面 | 20% | 主力资金流向验证(空值→中性10分) | 东财API |
| 消息面 | 15% | 情绪+催化+风险 | news_analysis.py |
| 估值面 | 10% | PE/PEG/基本面安全边际 | 腾讯+akshare |

**评分→操作映射:**
| 评分 | 等级 | 操作 |
|------|------|------|
| 80-100 | 🟢 强烈推荐 | 可重仓 |
| 60-79 | 🟡 谨慎推荐 | 可小仓 |
| 40-59 | 🟠 观望 | 等待信号 |
| 20-39 | 🔴 不推荐 | 回避 |
| 0-19 | 🔴 极度不推荐 | 远离 |

---

## 10节标准报告模板

深度分析报告必须包含以下章节(按顺序):

1. **核心数据速览** — 腾讯API实时行情
2. **历史复盘** — 对比上次报告结论vs实际走势
3. **市场环境分析** — 大盘指数+板块强弱
4. **量价关系深度分析** — K线形态+阶段判断
5. **资金流向分析** — 20日逐日资金流
6. **均线与技术面分析** — MA5/10/20/30
7. **估值与基本面分析** — PE/PB+概念板块
8. **综合评分与操作建议** — 5维度加权
9. **风险提示** — 5-6条
10. **附录: 完整K线数据**

---

## 红线规则(不可违反)

1. **深度分析前必须先搜stock-reports目录做历史复盘**
2. **所有行情必须基于实时数据, 不依赖文件中的静态数据**
3. **接到分析任务后, 第一步必须告知用户将调用哪些skill**
4. **K线数据必须交叉验证**(腾讯行情 vs 东财K线)
5. **子agent禁止编造K线数据, 必须调用API验证**
6. **复盘必须诚实**: 上次判断对了就说对了, 错了就说错了
7. **止损位/支撑位/阻力位的有效突破必须以收盘价为准**

---

## 使用示例

### 深度分析
```
用户: 深度分析许继电气
Agent:
  1. 加载 stock-analysis-core (红线+流程)
  2. 搜索 stock-reports/许继电气_000400/ 做历史复盘
  3. 加载 stock-analysis-deep (9步法详细流程)
  4. 调用 a-stock-data 获取K线/资金流/新闻
  5. 按10节模板输出报告
  6. 运行 add_to_pool.py 加入选股池
```

### 持仓分析
```
用户: 还拿不拿四方达?
Agent:
  1. 加载 stock-analysis-core
  2. 用 clarify 确认成本价
  3. 加载 stock-analysis-templates (持仓成本分析模板)
  4. 调用 a-stock-data 获取实时数据
  5. 结论先行 + R:R计算
```

---

## 数据源

| 数据类型 | 首选API | 备选API | 所在skill |
|----------|---------|---------|-----------|
| 实时行情 | 腾讯(qt.gtimg.cn) | 新浪 | a-stock-data |
| K线数据 | 东财push2his | 新浪(WSL 100%) | a-stock-data |
| 资金流向 | 东财push2his | em_api.py | a-stock-data |
| 新闻情绪 | news_analysis.py | web_search | a-stock-data |
| 研报数据 | 东财reportapi | - | a-stock-data |
| 板块数据 | 东财push2 | datacenter | a-stock-data |

---

## 相关项目

| 项目 | 说明 | 路径 |
|------|------|------|
| a-stock-data | 纯数据源skill | `~/.hermes/skills/a-stock-data/` |
| mx-moni | 模拟仓管理系统 | `~/.hermes/skills/mx-moni/` |
| stock-reports | 历史分析报告 | `/home/harry/stock-reports/` |
| Obsidian知识库 | 销售+股票笔记 | `/mnt/e/Harry 知识库/` |

---

## 免责声明

本框架仅供学习和研究使用，不构成投资建议。

---

*最后更新: 2026-08-13*
*Codex审查: 3轮16/16通过*
