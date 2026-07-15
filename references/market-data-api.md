# 市场环境数据API端点速查

> Step 0.5 市场环境扫描所需的数据源，按可靠性排序。

## 大盘指数（腾讯API，最稳定）

```python
# 批量获取上证/深证/创业板/科创50
codes = 'sh000001,sz399001,sz399006,sh000688'
url = f'https://qt.gtimg.cn/q={codes}'
# 解析: fields[1]=名称, fields[3]=现价, fields[32]=涨跌幅%, fields[37]=成交额(万)
```

⚠️ 腾讯API字段索引(实测校准):
| 索引 | 含义 |
|------|------|
| 1 | 名称 |
| 3 | 现价 |
| 32 | 涨跌幅% |
| 37 | 成交额(万) |
| 43 | 振幅% (不是PB!) |
| 44 | 总市值(亿) |
| 46 | PB |

## 北向资金（同花顺hsgtApi）

```python
url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
headers = {
    "User-Agent": "Mozilla/5.0 ...",
    "Host": "data.hexin.cn",
    "Referer": "https://data.hexin.cn/",
}
# 返回: hgt(沪股通累计净买入), sgt(深股通累计净买入)，单位亿元
# 注意: 是从开盘累计到当前的净买入额，不是单笔
```

⚠️ 返回的是累计值，不是分钟级增量。

## 概念板块涨幅（东财API）

```python
# 涨幅TOP15
url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fields=f2,f3,f4,f12,f14,f104,f105&fid=f3&fs=m:90+t:3"
# 跌幅TOP5
url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=0&np=1&fields=f2,f3,f4,f12,f14,f104,f105&fid=f3&fs=m:90+t:3"
# 解析: item['f14']=板块名, item['f3']/100=涨跌幅%, item['f104']=涨家数, item['f105']=跌家数
```

## 行业板块涨幅（东财API）

```python
url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fields=f2,f3,f4,f12,f14,f104,f105&fid=f3&fs=m:90+t:2"
```

## 个股所属板块涨跌（东财API）

```python
# 先获取个股概念列表(东财datacenter)
# 再查询每个概念板块今日涨跌
url = f"https://push2.eastmoney.com/api/qt/stock/get?secid=90.{concept_code}&fields=f43,f170"
# f170/100 = 涨跌幅%
```

⚠️ 概念代码(code)需要先从东财F10或datacenter获取，不是直接搜索得到的。

## 涨跌家数统计

东财API的f3筛选语法不稳定，不建议用于精确统计。可用mootdx quotes批量获取后Python计算（但耗时30-60秒）。

## 已知问题

1. **东财push2his在有代理环境下RemoteDisconnected** → 必须unset代理
2. **同花顺hsgtApi返回累计值** → 不是分钟级增量
3. **概念板块代码不能直接搜索** → 需要从F10或datacenter获取
4. **涨跌家数精确统计无现成API** → 需要批量quotes+Python计算
