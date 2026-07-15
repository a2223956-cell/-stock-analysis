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

### 接口
```
https://push2.eastmoney.com/api/qt/slist/get
```
或用腾讯API的F10数据。

## ⚠️ 频率限制

东财API有隐性频率限制:
- 连续约15次快速请求后开始返回"Remote end closed connection without response"
- 建议每次请求间隔sleep(1~2秒)
- 被限流后等30秒再重试
- 同域名不要并发请求

## ⚠️ 需要unset代理

所有东财API请求前需unset代理。**关键区别：Python-level unset不可靠，必须用shell-level unset：**

```python
# ❌ execute_code中Python-level unset不生效:
import os
for k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY']:
    os.environ.pop(k, None)
# execute_code的Python进程仍可能走代理, push2his会RemoteDisconnected

# ✅ 必须用terminal + shell-level unset:
# unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && python3 -c "..."
# 或在terminal()中执行unset + Python脚本
```

**实测(2026-07-01):** execute_code中即使用`os.environ.pop()`清除了所有代理环境变量,
东财push2his K线API和资金流API仍报RemoteDisconnected。
改用terminal + shell-level `unset`后正常。
腾讯API(`qt.gtimg.cn`)不受代理影响(走了不同路由)。

**结论:** 东财push2his相关API(K线/资金流)必须通过`terminal()`执行并先`unset`,
不要放在`execute_code()`中。mootdx(TCP协议)不受HTTP代理影响。
