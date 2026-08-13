# stock-analysis 常见陷阱

## 1. 深度分析报告必须按标准模板输出 (2026-08-05)

**症状**: 用户说"你的报告跟之前的格式不太一样"。主agent直接输出报告时,跳过了skill中的标准模板,用了完全不同的格式和评分体系。

**根因**: stock-analysis skill内容很长(100KB+),主agent只读了预览部分,没读到输出模板章节。

**标准模板(12章节)**:
```
标题 → 元数据 → 历史复盘 → 一、市场环境 → 二、量价关系(核心) → 
三、核心数据 → 四、消息面 → 五、资金面 → 六、技术面 → 
七、情绪周期 → 八、估值+基本面 → 九、风险筛查 → 
十、综合评分(五维加权) → 十一、操作建议 → 十二、横向对比
```

**评分体系**: 量价×权重 + 技术×权重 + 资金×权重 + 消息×权重 + 估值×权重 → 100分制

**规则**:
1. 分析完成后,必须用read_file读取skill的输出模板章节(offset 150-400)
2. 或读取/home/harry/stock-reports/下的历史报告确认格式
3. 按模板生成报告并保存为.md文件
4. 主agent直接输出时更容易跳过模板——必须自查

**PITFALL**: 禁止跳过模板直接输出!用户会对比历史报告格式,不一致会被纠正。

## 2. 子agent delegate_task模型指定方式 (2026-08-05)

**症状**: 用户要求用DeepSeek审计,但delegate_task的task dict中指定model参数不生效,子agent仍用默认xiaomi模型。

**根因**: delegate_task的子agent模型不能按调用指定,只能通过config.yaml全局设置:
```yaml
delegation:
  provider: deepseek  # 或 xiaomi
  model: deepseek-chat
```

**正确做法**: 临时修改config.yaml → 执行任务 → 改回原provider

**⚠️ 完成后必须改回原provider,否则后续所有subagent都会用错误的模型!**

## 3. 东财push2.eastmoney.com HTTPS在WSL下返回空响应 (2026-08-05)

**症状**: em_api.py的concept_top功能调用push2.eastmoney.com HTTPS时返回"Empty reply from server"。

**验证**: 
- push2.eastmoney.com HTTPS → Empty reply ❌
- push2.eastmoney.com HTTP → 正常 ✅
- push2his.eastmoney.com HTTPS → 正常 ✅

**修复**: em_api.py中concept_top的URL改为HTTP(无敏感数据传输)

## 4. DeepSeek API Key配置 (2026-08-05)

**路径**: ~/.hermes/.env
**环境变量**: DEEPSEEK_API_KEY
**用途**: sub agent用于代码和逻辑验证

**配置方式**: 在.env中添加 `DEEPSEEK_API_KEY=sk-xxx`
**使用方式**: 修改config.yaml的delegation.provider为deepseek
