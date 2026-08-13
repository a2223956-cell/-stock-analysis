# Stock Analysis Framework V4.0

股票综合分析框架 - 拆分版 (2026-08-13)

## 更新日志

### V4.0.0 (2026-08-13)
- 拆分为4个子skill, 解决长skill截断问题
- Codex 3轮审查16/16通过
- 统一0-100分制评分体系
- 清除所有watchlist/focus_items残留
- a-stock-data清理为纯数据源

### V3.x → V4.0 迁移
旧版单体skill(4025行)拆分为:
- `v3-backup` 分支保留旧版

## 目录结构

```
stock-analysis/
├── stock-analysis-core/       # 154行: 红线规则+核心理念+流程概览
├── stock-analysis-deep/       # 538行: 步骤-1+9步法+评分+10节模板
├── stock-analysis-templates/  # 1121行: 各类分析模板
├── stock-analysis-reference/  # 2144行+33个references
├── scripts/                   # 分析脚本
├── strategies/                # 策略YAML
└── templates/                 # 旧模板(兼容)
```

## 回滚

```bash
git checkout v3-backup  # 切换到旧版
```

## 使用

深度分析时按顺序加载:
1. `stock-analysis-core` (必加载, 红线+流程)
2. `stock-analysis-deep` (按需, 详细9步法)
3. `a-stock-data` (按需, 数据获取)
