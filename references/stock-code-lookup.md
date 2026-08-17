# 股票代码查询参考

## 东财suggest API（最可靠）

```python
import urllib.request, json

def lookup_stock(name: str) -> list[dict]:
    """通过股票名称查询代码"""
    url = f"https://searchapi.eastmoney.com/api/suggest/get?input={name}&type=14&count=5"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode("utf-8"))
    results = data.get("QuotationCodeTable", {}).get("Data", [])
    return [{"code": r.get("Code"), "name": r.get("Name"), "market": r.get("MktNum")} for r in results]

# 用法
codes = lookup_stock("雷赛智能")
# 返回: [{"code": "002979", "name": "雷赛智能", "market": "0"}]
```

## 已知易混淆代码

| 用户说的 | 实际代码 | 实际公司 |
|---------|---------|---------|
| 凯盛科技 | 600552 | 凯盛科技(正确) |
| 凯盛科技 | 600876 | 凯盛新能(原名凯盛科技，已更名) |
| 柯力传感 | 603662 | 柯力传感(正确) |
| 柯力传感 | 603210 | 泰鸿万立(搜索误导) |
| 南方精工 | 002553 | 南方精工(做滚针轴承，非六维力传感器) |
| 雷赛智能 | 002979 | 雷赛智能(正确) |
| 雷赛智能 | 002529 | 海源复材(代码相邻易混淆) |
| 大众矿业 | - | A股无此公司，应为"大中矿业"(001203) |

## 验证流程（每次必做）

```python
import urllib.request

def verify_stock(code: str, expected_name: str) -> bool:
    """通过腾讯行情API验证代码对应公司名"""
    prefix = "sh" if code.startswith(("6","9")) else ("bj" if code.startswith("8") else "sz")
    url = f"https://qt.gtimg.cn/q={prefix}{code}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode("gbk")
    actual_name = data.split('"')[1].split("~")[1]
    match = expected_name in actual_name or actual_name in expected_name
    if not match:
        print(f"⚠️ 代码验证失败: {code} 实际是'{actual_name}', 预期'{expected_name}'")
    return match
```
