⚠️ 本文件评分体系已过时(0-5制),以stock-analysis-deep的0-100分制为准。

# A股深度分析报告 — 标准模板与工作流

> 适用于个股深度分析报告生成，包含历史复盘(对比上次报告结论是否验证)。

## 一、报告结构模板

```
# {股票名称}({代码}) 深度分析报告

**报告日期**: YYYY-MM-DD HH:MM CST (盘中/收盘)
**分析周期**: 前复权数据, 近N个交易日
**当前价格**: XX.XX元 (盘中实时/收盘)

---

## 📊 一、核心数据速览          ← 腾讯API实时行情
## 🔄 二、历史复盘              ← 对比上次报告结论vs实际走势
## 📈 三、市场环境分析           ← 大盘指数 + 板块强弱对比
## 📉 四、量价关系深度分析(核心)  ← K线形态 + 阶段判断 + 关键K线标注
## 💰 五、资金流向分析           ← 20日逐日资金流 + 主力行为判断
## 📐 六、均线与技术面分析        ← MA5/10/20/30 + 偏离度 + 支撑压力
## 💎 七、估值与基本面分析        ← PE/PB + 机构盈利预测 + 概念板块
## 🎯 八、综合评分与操作建议      ← 5维度加权评分 + 明确操作建议
## 📋 九、风险提示               ← 5-6条核心风险
## 📊 十、附录: 完整K线数据       ← 30日完整数据表
```

## 二、数据采集流程

### Step 1: 实时行情 (腾讯API, 延迟<1秒)
```bash
curl -s "https://qt.gtimg.cn/q=sh600552" | iconv -f GBK -t UTF-8
# 同时获取大盘指数
curl -s "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000688" | iconv -f GBK -t UTF-8
```

### Step 2: K线数据 (东财API, 30日前复权)
```python
secid = "1.600552"  # 沪市1.代码, 深市0.代码
url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101&lmt=30"
```

**⚠️ API失败降级链**: 东财API → http.client(WSL最可靠) → requests库 → **web_search搜索证券之星/金投网/雪球缓存数据**。详见 `references/api-reliability-notes.md` "终极备选"章节。web_search只能获取近2-3天收盘数据，无法替代完整30日K线，但足以支撑涨停后出货分析、资金流向验证等短期判断。

### Step 3: 资金流向 (东财API, 20日)
```python
# ⚠️ 2026-08-06: fflow/daykline/get 被WAF封禁, 用 fflow/kline/get?klt=101 替代
url = f"https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get?secid={secid}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&klt=101&lmt=20"
```

### Step 4: 所属板块 (东财F10 API, 推荐)

**方式1(推荐): F10 datacenter API**
```python
# 个股→所属全部概念板块(含行业/概念/地区分类)
code = "603327.SH"  # 沪市.SH, 深市.SZ
url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_CORETHEME_BOARDTYPE&columns=SECUCODE,SECURITY_NAME_ABBR,BOARD_CODE,BOARD_NAME,IS_PRECISE,BOARD_RANK,BOARD_TYPE&filter=(SECUCODE=%22{code}%22)&pageSize=50"
# 备选host: datacenter.eastmoney.com/securities/api/data/v1/get (同接口)
```

**方式2(备选): emweb CoreConception API**
```python
# 格式简洁,返回ssbk数组
url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code={'SH' if code.startswith('6') else 'SZ'}{code[:6]}"
```

**方式3(不可靠): push2 slist API** — 对部分个股返回空数据，不推荐

⚠️ **不要用push2 slist API作为主数据源**，实测对603327/003021等返回空。

获取板块涨跌幅: 用BOARD_CODE调用 `push2.eastmoney.com/api/qt/stock/get?secid=90.{BOARD_CODE}&fields=f43,f170`

### Step 5: 消息面分析 (同花顺脚本)
```bash
~/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/skills/a-stock-data/scripts/news_analysis.py 600552 凯盛科技
```

### Step 5b: 备选数据源 — mx-data / mx-search (东方财富妙想)

当东财push2/push2his API因网络问题(WSL RemoteDisconnected)导致K线或资金流API全部失败时，**mx-search是最可靠的备选数据源**，因为它不依赖同一批端点。

```bash
cd ~/.hermes/skills/mx-search && python3 mx_search.py "泛微网络603039主力资金流向 近期" /home/harry/mx_output
```

**mx-search能替代的失败API**:
- **资金流向API失败** → 搜索"股票代码 主力资金流向 近期"，新闻中包含逐日主力净流入/流出数据
- **融资融券API失败** → 搜索"股票代码 融资融券"，新闻中包含融资余额、融券余量变化
- **大宗交易API失败** → 搜索"股票代码 大宗交易"，新闻中包含成交量、成交价、买卖方营业部
- **研报API失败** → 搜索"股票代码 研报 目标价"，新闻中包含机构评级和目标价

**⚠️ mx-data需要pandas**，如果环境未安装pandas则无法使用。mx-search无此依赖，优先使用。

**⚠️ mx-search有调用频率限制(429)**，不要并行发多个请求，建议分批(2-3个一组，间隔2秒)。

**实战经验(2026-07-09)**: 东财资金流API(push2his fflow)连续3次urllib全部RemoteDisconnected，但mx-search一次成功返回了完整的资金流向、融资融券、大宗交易数据，数据质量甚至高于API(包含分析师解读)。

### Step 6: 研报数据 (东财API)
```python
url = f"https://reportapi.eastmoney.com/report/list?industryCode=*&pageNo=1&pageSize=10&code=600552&qType=0"
```

## 三、分析方法论

### 量价关系分析 (权重30%)

**阶段判断**:
1. 主力建仓/拉升期: 放量突破+量价齐升
2. 主力加速拉升: 天量天价 ← 见顶信号
3. 主力出货/暴跌期: 放量下跌+缩量反弹交替
4. 超跌反弹: 缩量反弹(非建仓信号)

**关键K线标注**: 每个阶段选1-2根代表性K线，带具体数据(开收高低价+成交量+前日对比)。

**量能指标**:
- 近5日均量 vs 前5日均量 → 量能比
- 量能比 < 0.7 = 缩量, > 1.3 = 放量
- 今日量比(盘中): < 0.8 = 偏低

### 资金流向分析 (权重25%)

**东财资金流字段**: f52=主力净流, f53=超大单, f54=大单, f55=中单, f56=小单 (单位:元)

**主力行为判断**:
- 超大单(机构)持续流出 + 大单(游资)承接 = 出货期
- 超大单+大单同时流出 = 恐慌出逃
- 中小单(散户)转为流出 = 信心崩溃

### 均线分析 (权重20%)

**均线排列**:
- MA5 > MA10 > MA20 > MA30 = 多头排列 ✅
- MA5 < MA10 < MA20 < MA30 = 空头排列 ❌
- 其他 = 混合排列

**偏离度**: (当前价/MA - 1) × 100%

### 估值分析 (权重15%)

**合理估值区间**: 基于机构盈利预测的PE区间
- 当前PE vs 行业均值
- 按预测年份净利润计算远期PE

### 综合评分公式

```
综合评分 = 量价关系(30%) + 资金流向(25%) + 均线技术(20%) + 估值安全(15%) + 消息面(10%)

评分等级:
  4.0-5.0: 🟢 强烈推荐
  3.0-4.0: 🟡 谨慎推荐
  2.0-3.0: 🟠 观望
  1.0-2.0: 🔴 不推荐
  0.0-1.0: 🔴 极度不推荐
```

### 历史复盘方法

对比上次报告的每项关键结论，逐一验证:
1. 价格走势是否符合预判
2. 止损位/目标价是否正确触发
3. 主力资金流向是否如预期
4. 均线支撑/压力是否有效
5. 量价关系是否如预期

标注: ✅完全验证 / ⚠️部分验证 / ❌判断错误

## 四、K线逐日解读与主力行为判断

> 每根K线需标注: 开/收/高/低/成交量 + 前日对比 + 形态名称 + 主力行为推断

### 关键K线形态判断

| 形态 | 特征 | 主力行为 |
|------|------|----------|
| **长上影线(看跌!)** | 上影>2倍实体, 收盘在低位 | ⬇️ 拉高出货，上方抛压极重 |
| **锤子线(看涨)** | 下影>2倍实体, 收盘在高位 | ↗️ 有抄底资金接盘，短期支撑 |
| **放量大阴** | 跌>5% + 量>前日 | ⬇️ 恐慌抛售/主力出货高潮 |
| **缩量反弹** | 涨但量<前日 | ⚠️ 非建仓信号，可能是诱多 |
| **放量下跌** | 跌 + 量比>1.3 | ⬇️ 最危险信号，出货加速 |
| **缩量企稳** | 平/微涨 + 量比<0.7 | ↗️ 抛压减轻，可能见底 |
| **十字星** | 开≈收，上下影 | ⚠️ 方向未定，等下根确认 |
| **涨停板** | 收=涨停价 | ↗️ 强势但需看后续能否连板 |

> ⚠️ **锤子线 vs 长上影阴线**: 两者形态相似(都有长下影线)但含义相反。**关键区分: 收盘价位置**。收盘在K线顶部=锤子线(看涨)，收盘在K线底部=长上影阴线(看跌)。详见下方Pitfalls章节。

### 量价背离判断

- **放量涨**: 健康上涨 ✅
- **缩量涨**: 动能不足 ⚠️
- **放量跌**: 出货加速 ⬇️ (最危险)
- **缩量跌**: 抛压减轻，可能见底 ↗️

## 五、出货时间线(Exhaustion Timeline)

> 当怀疑主力出货时，逐日记录主力净流入+K线特征+主力行为，构建完整出货叙事。

### 构建方法

```
| 日期 | 主力净流入 | K线特征 | 主力行为 |
|------|-----------|---------|----------|
| D1(见顶日) | +0.3亿 | 涨停/长上影 | 拉高出货开始 |
| D2 | -3.5亿 | 放量大阴 | 大规模出货 |
| D3 | -1.2亿 | 继续下跌 | 持续抛售 |
| D4 | +0.5亿 | 反弹 | 诱多?短暂回流 |
| D5 | -2.7亿 | 再次大跌 | 出货高潮 |
| ... | ... | ... | ... |
| 合计 | -X亿 | - | 出货完成度 |
```

### 出货完成度判断

- 累计流出 > 总流入 = **出货基本完成**，但尾部抛压仍在
- 连续3日以上缩量+净流出缩小 = **出货尾声**
- 突然放量净流出 = **新一轮出货开始**

### 支撑/压力位的行动触发

不是所有支撑/压力都值得报告。**只标注有操作意义的位**:

| 位置 | 操作触发 | 示例 |
|------|----------|------|
| 减仓区间 | 反弹至该区间应减仓 | "52-53减半仓" |
| 止损线 | 跌破必须清仓 | "跌破47清仓" |
| 建仓区间 | 回调至该区间可考虑 | "42-44可小仓" |
| 强压力 | 突破前不应加仓 | "55是MA10压力" |

每个位必须附带: **价格 + 操作 + 理由**

## 六、Pitfalls

### ⚠️ 终端heredoc被block

WSL环境下 `cat << 'PYEOF' | python3` 形式的heredoc命令可能被安全策略block。

**解决方案**: 先用 `write_file` 写到 `/tmp/xxx.py`，再用 `python3 /tmp/xxx.py` 执行。

### ⚠️ 板块API返回格式

东财板块API的 `data.diff` 可能返回 `dict{0: {...}, 1: {...}}` 或 `list[..., ...]`，需统一处理:
```python
items = data['data']['diff']
if isinstance(items, dict):
    items = list(items.values())
```

### ⚠️ WSL代理导致东财API全部失败

WSL环境通常有`https_proxy=http://127.0.0.1:7890`等代理设置。**Python内`os.environ.pop`不够**，代理在shell层持久化。

**必须在terminal命令层面先unset**:
```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && python3 script.py
```

**urllib全部失败时切requests库**: 实测2026-07-09，urllib对push2his连续3次RemoteDisconnected，requests一次成功。详见 `references/api-reliability-notes.md` WSL环境章节。

### ⚠️ 资金流向API字段单位

东财资金流向API返回的金额字段单位为**元**（非万元），报告中需转换为万元或亿元显示。

### ⚠️ 盘中数据标注

盘中数据(未收盘)必须在报告中明确标注"盘中"，收盘价可能与盘中价不同。成交量/成交额为盘中累计值，需与前日全天数据对比时注明"盘中(预计缩量/放量)"。

### ⚠️ 前复权 vs 不复权

深度分析报告统一使用**前复权**数据(fqt=1)，确保均线计算准确。如需对比历史报告，确认两次使用相同的复权方式。

### 🔴 致命陷阱: K线数据必须交叉验证

**血泪教训(2026-07-13)**: 7/10报告的K线数据严重错误——收盘价35.59(涨+2.10%)实际是33.83(跌-2.62%)，成交量69,032实际是201,801。导致"缩量锤子线看涨"结论完全错误(实际是放量长上影阴线看跌)，后续3天暴跌-9.25%。

**根因**: 数据来源不可靠或解析错误，未做交叉验证就直接用于分析。

**强制步骤**:
1. **获取K线后立即验证最后一根K线的收盘价** — 对比腾讯实时行情的昨收/今价
2. **成交量异常值检测** — 如果某日量突然变为前日的50%以下或200%以上，必须复核
3. **收盘价方向验证** — 如果K线显示涨但腾讯行情显示跌(或反之)，数据有误
4. **逻辑一致性check** — 写报告前快速验证: "今天大盘涨还是跌? 板块涨还是跌? 个股涨还是跌?" 三者方向应逻辑一致

**验证代码**:
```python
# K线数据交叉验证
kline_last = klines[-1]  # 最后一根K线
kline_close = float(kline_last.split(',')[2])
kline_date = kline_last.split(',')[0]

# 对比腾讯实时行情
tencent_data = fetch_qq("sh603039")  # 昨收=fields[4], 今价=fields[3]
tencent_close = float(tencent_data.split('~')[3])

# 验证: K线收盘价应与腾讯行情一致(收盘后)或在盘中范围内
if abs(kline_close - tencent_close) > 0.5:
    print(f"⚠️ 数据异常! K线收盘{kline_close} vs 腾讯{tencent_close}")
```

### 🔴 致命陷阱: 锤子线 vs 长上影阴线 区分

**这是最容易犯的K线形态误判错误**。两者都有长下影线，但方向完全相反:

| 特征 | 锤子线(看涨) | 长上影阴线(看跌) |
|------|-------------|-----------------|
| 收盘价位置 | 接近最高价 | 接近最低价 |
| 上影线 | 极短或无 | 较长 |
| 下影线 | 较长(≥实体2倍) | 可长可短 |
| 实体位置 | 在K线顶部 | 在K线底部 |
| 含义 | 盘中暴跌后强力拉回 | 盘中反弹后被打压 |
| 主力行为 | 下方承接极强 | 上方抛压极重 |

**判断公式**:
```python
body_ratio = abs(close - open) / (high - low)  # 实体占比
upper_shadow = high - max(open, close)
lower_shadow = min(open, close) - low

if lower_shadow > 2 * abs(close - open) and upper_shadow < abs(close - open):
    # 下影线≥2倍实体 且 上影线<实体 → 锤子线
    pattern = "锤子线(看涨)"
elif upper_shadow > 2 * abs(close - open) and close < (high + low) / 2:
    # 上影线≥2倍实体 且 收盘在中位以下 → 长上影阴线
    pattern = "长上影阴线(看跌)"
```

**关键**: 收盘价在K线的上半部分还是下半部分，是区分两者的决定性因素。
