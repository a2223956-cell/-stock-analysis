# 东方财富API参考

## K线数据API

### 接口
```
https://push2his.eastmoney.com/api/qt/stock/kline/get
```

### 参数
- `secid`: 证券代码，格式 `市场.代码`
  - 深市: `0.001203` (0.开头)
  - 沪市: `1.600552` (1.开头)
- `fields1=f1,f2,f3,f4,f5,f6`: 固定
- `fields2=f51,f52,f53,f54,f55,f56,f57`: K线字段
- `klt=101`: 日K线
- `fqt=1`: 前复权
- `end=20260618`: 截止日期
- `lmt=20`: 返回条数

### 完整请求示例
```
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.001203&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20260618&lmt=20
```

### 响应解析
```python
data = json.loads(resp.read())
klines = data.get('data', {}).get('klines', [])
for k in klines:
    parts = k.split(',')
    # parts[0]=日期, parts[1]=开盘, parts[2]=收盘, parts[3]=最高
    # parts[4]=最低, parts[5]=成交量, parts[6]=成交额
    date, o, c, h, l, vol, amt = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
```

### ⚠️ JSONP包装
有时响应包含JSONP回调包装，需要先去掉:
```python
text = resp.read().decode('utf-8')
if text.startswith('('):
    text = text[1:-2]  # 去掉 ( 和 );
data = json.loads(text)
```

## 资金流向API

### 接口
```
https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get
```

### 参数
- `secid`: 同K线API
- `fields1=f1,f2,f3`: 固定
- `fields2=f51,f52,f53,f54,f55,f56`: 资金流字段
- `lmt=20`: 返回天数

### 字段解析
```python
for k in klines:
    parts = k.split(',')
    # parts[0]=日期
    # parts[1]=主力净流入(元) ← 注意单位是元！
    # parts[2]=小单净流入
    # parts[3]=中单净流入
    # parts[4]=大单净流入
    # parts[5]=超大单净流入
    date = parts[0]
    main_flow_yi = float(parts[1]) / 100000000  # 元→亿元
```

### ⚠️ 单位陷阱
field[1]原始值单位是**元(元)**，不是万元也不是亿元！
- /10000 = 万元
- /100000000 = 亿元

用占比字段(field[6])交叉验算防搞错。

## 概念板块API

### 接口(push2 slist)
```
https://push2.eastmoney.com/api/qt/slist/get
```
或用腾讯API的F10数据。

### 接口(东财datacenter — 更稳定的备用方案)
```
https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_CORETHEME_BOARDTYPE&columns=SECURITY_CODE,BOARD_NAME,BOARD_RANK,BOARD_CODE,IS_PRECISE,BOARD_TYPE&quoteColumns=&filter=(SECURITY_CODE=%22{代码}%22)&pageNumber=1&pageSize=50&sortTypes=-1&sortColumns=BOARD_RANK&source=HSF10&client=PC
```
返回字段:
- BOARD_NAME: 概念名称
- BOARD_CODE: 板块代码
- BOARD_TYPE: 类型(板块/行业)
- BOARD_RANK: 排名

⚠️ 2026-07-16实测: push2 slist API返回空时，此datacenter API仍成功返回22个概念标签。
需要Referer: `https://emweb.securities.eastmoney.com/`

### 接口(东财reportapi — 研报/评级)
```
https://reportapi.eastmoney.com/report/list?industryCode=*&pageNo=1&pageSize=5&beginTime=2025-01-01&endTime=2026-12-31&code={代码}
```
⚠️ 2026-07-16实测: WSL环境下持续返回HTTP 500。降级方案: web_search搜索研报信息。

## ⚠️ 频率限制

东财API有隐性频率限制:
- 连续约15次快速请求后开始返回"Remote end closed connection without response"
- 建议每次请求间隔sleep(1~2秒)
- 被限流后等30秒再重试
- 同域名不要并发请求

## ⚠️ 需要unset代理

所有东财API请求前需unset代理。**推荐方式: 使用em_api.py脚本(subprocess+curl):**

```bash
# ✅ 推荐: em_api.py脚本自动处理代理和限频
python3 ~/.hermes/scripts/em_api.py fund_flow <secid> [limit]
python3 ~/.hermes/scripts/em_api.py kline <secid> [limit]
python3 ~/.hermes/scripts/em_api.py concept_top [limit]
```

**备选: terminal + shell-level unset:**
```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && python3 -c "..."
```

**❌ 不可用: execute_code + Python-level unset:**
```python
# execute_code中Python-level unset不生效:
import os
for k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY']:
    os.environ.pop(k, None)
# push2his仍会RemoteDisconnected
```

**实测(2026-07-21):** em_api.py(subprocess+curl直连)是WSL环境下最可靠的方案。
curl直连(不走代理)100%成功,但有限频(间隔>=5秒)。
requests库的代理处理在WSL+Clash环境下有bug,即使unset也会失败。
