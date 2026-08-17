#!/usr/bin/env python3
"""
深度分析数据采集器 — 15步模板(V5)
用法: python3 deep_analysis.py <股票代码> [股票名称]

输出: /tmp/deep_analysis_<code>.json
所有数据通过API获取,禁止编造。脚本只采集数据,不写分析结论。

15步模板(V5):
  Step 0:  前复权检查(除权记录)
  Step 1:  核心数据速览 (腾讯实时行情)
  Step 2:  历史复盘 (如有上次报告则对比)
  Step 3:  市场环境分析 (大盘指数 + 板块)
  Step 1E: 板块分析 (调用sector_analysis.py)
  Step 3B: 北向资金
  Step 4:  量价关系深度分析 (30日K线 + 形态标注)
  Step 5:  资金流向分析 (20日逐日资金流)
  Step 6:  均线与技术面分析 (MA5/10/20/30 + 支撑压力)
  Step 7:  估值与基本面分析 (PE/PB + 板块 + 机构预测)
  Step 8:  综合评分与操作建议 (5维度加权)
  Step 9:  风险提示
  Step 10: 情绪周期分析(换手率5档)
  Step 11: 概念板块完整映射
  Step 12: 消息面分析(调用news_analysis.py)
  Step 13: (reserved)
  Step 14: 风险筛查(7项清单)
  Step 15: 附录: 完整K线数据
"""
import sys, os, json, time, urllib.request, urllib.parse, subprocess, re as _re
from datetime import datetime, timedelta

# 添加路径(仅scripts目录自身)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════
# 腾讯行情工具(内联自quote_utils.py, 消除外部依赖)
# ═══════════════════════════════════════════════════════

def get_prefix(code):
    """返回腾讯行情前缀: 6开头=sh, 8/4/9开头=bj, 0/3开头=sz"""
    if code.startswith('92'):
        return 'bj'
    elif code.startswith(('6', '9')):
        return 'sh'
    elif code.startswith(('8', '4')):
        return 'bj'
    else:
        return 'sz'

def tencent_quote(code):
    """单只股票实时行情, 返回统一quote dict"""
    try:
        prefix = get_prefix(code)
        full_code = f"{prefix}{code}"
        url = f"https://qt.gtimg.cn/q={full_code}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('gbk', errors='replace')
        if '"' not in raw:
            return None
        vals = raw.split('"')[1].split('~')
        if len(vals) < 3:
            return None
        def _f(idx):
            try: return float(vals[idx]) if len(vals) > idx and vals[idx] else 0
            except: return 0
        def _i(idx):
            try: return int(vals[idx]) if len(vals) > idx and vals[idx] else 0
            except: return 0
        return {
            'code': vals[2] if len(vals) > 2 else '',
            'name': vals[1] if len(vals) > 1 else '',
            'price': _f(3), 'last_close': _f(4), 'open': _f(5),
            'volume': _i(6), 'change_pct': _f(32),
            'high': _f(33), 'low': _f(34), 'amount_wan': _f(37),
            'turnover': _f(38), 'pe_ttm': _f(39), 'mcap': _f(44),
            'pb': _f(46), 'vol_ratio': _f(49),
        }
    except Exception:
        return None

# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════

def fetch_json(url, headers=None, timeout=10):
    """通用JSON请求"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def fetch_tencent_kline(code, offset=60):
    """腾讯K线数据(前复权)"""
    prefix = get_prefix(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{offset},qfq"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            return None
        kline_data = data.get("data", {}).get(f"{prefix}{code}", {})
        qfqday = kline_data.get("qfqday", kline_data.get("day", []))
        if not qfqday:
            return None
        result = []
        for item in qfqday:
            if isinstance(item, list) and len(item) >= 6 and isinstance(item[0], str) and item[0].startswith("2"):
                result.append({
                    "date": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5])
                })
        return result
    except Exception:
        return None

def fetch_fund_flow_mxdata(code, name=""):
    """资金流向(mx-data API) — 替代不可靠的push2his

    mx-data返回3个table:
    - Table 0: 当日实时快照(主力净流入/DDX/DDY等)
    - Table 1: 当日累计(主力流入/流出)
    - Table 2: 近3日历史(主力净流入逐日)
    """
    try:
        import requests as _req
        api_key = os.environ.get("MX_APIKEY", "")
        if not api_key:
            return {"error": "MX_APIKEY未设置", "source": "mx-data"}

        stock_name = name or code
        query = f"{stock_name}主力资金流向"
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
        headers = {"Content-Type": "application/json", "apikey": api_key}
        resp = _req.post(url, headers=headers, json={"toolQuery": query}, timeout=30)
        data = resp.json()

        # 解析嵌套结构: data.data.searchDataResultDTO.dataTableDTOList
        dto = data.get("data", {}).get("data", {}).get("searchDataResultDTO", {})
        tables = dto.get("dataTableDTOList", [])
        if not tables:
            return {"error": "mx-data返回空数据", "source": "mx-data"}

        result = []

        # Table 2: 近3日历史数据(最有价值)
        if len(tables) >= 3:
            t2 = tables[2]
            table_data = t2.get("table", {})
            dates = table_data.get("headName", [])  # ["2026-08-14(日)", ...]
            # 主力净流入字段: 328083
            main_flow = table_data.get("328083", [])
            for i, date_str in enumerate(dates):
                if i < len(main_flow):
                    raw = str(main_flow[i])
                    amount = _parse_amount(raw)
                    result.append({
                        "date": date_str.split("(")[0] if "(" in date_str else date_str[:10],
                        "main_net": amount,
                        "source": "mx-data"
                    })

        # Table 0: 当日实时快照(补充今日数据)
        if tables:
            t0 = tables[0]
            table_data = t0.get("table", {})
            head = table_data.get("headName", [""])[0] if table_data.get("headName") else ""
            main_net_today = table_data.get("ZLJE_f62_3", ["0"])[0] if table_data.get("ZLJE_f62_3") else "0"
            today_amount = _parse_amount(str(main_net_today))
            today_date = head[:10] if head else ""
            # 如果今日数据不在历史列表中,添加
            if today_date and not any(r["date"] == today_date for r in result):
                result.insert(0, {"date": today_date, "main_net": today_amount, "source": "mx-data"})

        # 提取DDX/DDY信息
        ddx_info = {}
        if tables:
            t0 = tables[0].get("table", {})
            ddx_info = {
                "ddx": t0.get("DRDDX_f88_3", ["0"])[0] if t0.get("DRDDX_f88_3") else "0",
                "ddy": t0.get("DRDDY_f89_3", ["0"])[0] if t0.get("DRDDY_f89_3") else "0",
                "ddz": t0.get("DRDDZ_f90_3", ["0"])[0] if t0.get("DRDDZ_f90_3") else "0",
                "5d_ddx": t0.get("5RDDX_f91_3", ["0"])[0] if t0.get("5RDDX_f91_3") else "0",
                "10d_ddx": t0.get("10RDDX_f94_3", ["0"])[0] if t0.get("10RDDX_f94_3") else "0",
            }

        if result:
            result.sort(key=lambda x: x["date"], reverse=True)
            return result[:20], ddx_info
        return {"error": "无法解析资金流数据", "source": "mx-data"}, {}

    except Exception as e:
        return {"error": str(e), "source": "mx-data"}, {}


def _parse_amount(raw):
    """解析金额字符串(如'-2349万元', '1.13亿元', '511.4万')"""
    raw = str(raw).strip()
    # 匹配 "X.XX亿元"
    m = _re.search(r'([-+]?\d+\.?\d*)\s*亿', raw)
    if m:
        return float(m.group(1)) * 1e8
    # 匹配 "X.XX万元" 或 "X.XX万"
    m = _re.search(r'([-+]?\d+\.?\d*)\s*万', raw)
    if m:
        return float(m.group(1)) * 1e4
    # 纯数字
    try:
        return float(raw)
    except:
        return 0

def fetch_board_info(code):
    """获取个股所属板块"""
    try:
        prefix = "1" if code.startswith("6") else "0"
        url = f"https://push2.eastmoney.com/api/qt/slist/get?fltt=2&invt=2&secid={prefix}.{code}&spt=3&pi=0&pz=50&po=1&fields=f12,f14,f3"
        data = fetch_json(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/"
        })
        diff = (data.get("data") or {}).get("diff") or {}
        items = diff.values() if isinstance(diff, dict) else diff
        return [item.get("f14", "") for item in items if item.get("f14")]
    except Exception:
        return []

def fetch_market_indices():
    """获取大盘指数"""
    codes = "sh000001,sz399001,sz399006,sh000688"
    url = f"https://qt.gtimg.cn/q={codes}"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("gbk", errors="replace")
        result = {}
        for seg in text.split("v_"):
            if "~" not in seg:
                continue
            fields = seg.split("~")
            if len(fields) > 32:
                name = fields[1]
                price = float(fields[3]) if fields[3] else 0
                change_pct = float(fields[32]) if fields[32] else 0
                result[name] = {"price": price, "change_pct": change_pct}
        return result
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════
# V5 新增函数
# ═══════════════════════════════════════════════════════

def fetch_ex_right(code, klines=None):
    """检查近期是否有除权 — 通过K线跳空检测

    除权特征: 相邻两日收盘价出现>5%的向下跳空(非跌停),
    且次日开盘价也低于前日收盘价。
    """
    result = {"ex_right": False, "checked": True, "method": "kline_gap"}

    if not klines or len(klines) < 5:
        result["note"] = "K线数据不足,无法检测"
        result["checked"] = False
        return result

    # 检查近30日是否有异常跳空(除权通常表现为向下跳空5-30%)
    recent = klines[-30:] if len(klines) >= 30 else klines
    gaps = []
    for i in range(1, len(recent)):
        prev_close = recent[i-1]["close"]
        curr_open = recent[i]["open"]
        if prev_close > 0:
            gap_pct = (curr_open - prev_close) / prev_close * 100
            # 除权跳空: 向下5-30%(排除跌停-10%和正常波动)
            if -30 < gap_pct < -4:
                gaps.append({
                    "date": recent[i]["date"],
                    "prev_close": prev_close,
                    "open": curr_open,
                    "gap_pct": round(gap_pct, 2)
                })

    if gaps:
        # 找到最近的跳空
        latest_gap = gaps[-1]
        result["ex_right"] = True
        result["ex_date"] = latest_gap["date"]
        result["gap_pct"] = latest_gap["gap_pct"]
        result["note"] = f"检测到{latest_gap['date']}向下跳空{latest_gap['gap_pct']}%,疑似除权"
    else:
        result["note"] = "近30日未检测到除权跳空"

    return result

def fetch_northbound():
    """获取北向资金(沪股通/深股通净流入)"""
    try:
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        raw = fetch_json(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.hexin.cn/"})
        if "error" in raw:
            return {"error": raw["error"], "available": False}

        # 同花顺API返回格式可能变化, 做防御性解析
        data_str = str(raw)

        # 尝试提取数值(单位: 亿元)
        hgt = 0  # 沪股通
        sgt = 0  # 深股通
        parsed = False

        # 方式1: 如果返回的是dict且有标准字段
        if isinstance(raw, dict):
            hgt_val = raw.get("hgt", raw.get("sh_hgt", 0))
            sgt_val = raw.get("sgt", raw.get("sz_sgt", 0))
            # hgt/sgt可能是列表(每分钟一个值), 取最后一个
            if isinstance(hgt_val, list) and hgt_val:
                hgt = float(hgt_val[-1]) if hgt_val[-1] else 0
            elif isinstance(hgt_val, (int, float)):
                hgt = float(hgt_val)
            if isinstance(sgt_val, list) and sgt_val:
                sgt = float(sgt_val[-1]) if sgt_val[-1] else 0
            elif isinstance(sgt_val, (int, float)):
                sgt = float(sgt_val)
            if hgt or sgt:
                parsed = True

        # 方式2: 从字符串中提取数字
        if not parsed:
            nums = _re.findall(r'[-+]?\d+\.?\d*', data_str[:2000])
            if len(nums) >= 2:
                try:
                    hgt = float(nums[0])
                    sgt = float(nums[1])
                    parsed = True
                except Exception:
                    pass

        if parsed:
            total = hgt + sgt
            return {
                "hgt": round(hgt, 2),
                "sgt": round(sgt, 2),
                "total": round(total, 2),
                "unit": "亿元",
                "available": True,
                "note": "数据来源:同花顺hsgtApi"
            }
        else:
            return {"error": "无法解析北向资金数据", "available": False, "raw": data_str[:300]}

    except Exception as e:
        return {"error": str(e), "available": False}

def fetch_concept_blocks(code):
    """获取个股全部概念板块(东财datacenter)"""
    try:
        filter_val = urllib.parse.quote(f'(SECURITY_CODE="{code}")')
        url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_CORETHEME_BOARDTYPE&columns=SECURITY_CODE,BOARD_NAME,BOARD_RANK,BOARD_CODE&filter={filter_val}&pageSize=50&sortTypes=-1&sortColumns=BOARD_RANK&source=HSF10&client=PC'
        data = fetch_json(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/"
        })
        if "error" in data:
            return {"blocks": [], "error": data["error"]}
        result_data = data.get("result", {})
        if not result_data:
            return {"blocks": [], "note": "无数据"}
        items = result_data.get("data", []) or []
        blocks = []
        for item in items:
            blocks.append({
                "name": item.get("BOARD_NAME", ""),
                "code": item.get("BOARD_CODE", ""),
                "type": item.get("BOARD_TYPE", ""),
                "rank": item.get("BOARD_RANK", 0)
            })
        return {"blocks": blocks, "count": len(blocks)}
    except Exception as e:
        return {"blocks": [], "error": str(e)}

def call_sector_analysis(code, name=""):
    """调用sector_analysis.py获取板块分析"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sector_analysis.py")
    if not os.path.exists(script_path):
        return {"error": "sector_analysis.py not found"}
    try:
        cmd = [sys.executable, script_path, code]
        if name:
            cmd.append(name)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = r.stdout
        sectors = []
        for line in output.split("\n"):
            if "→" in line or "板块" in line or "+" in line or "-" in line:
                sectors.append(line.strip())
        return {"raw_output": output[:2000], "sectors": sectors, "returncode": r.returncode}
    except Exception as e:
        return {"error": str(e)}

def call_news_analysis(code, name=""):
    """调用news_analysis.py获取消息面"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_analysis.py")
    if not os.path.exists(script_path):
        return {"error": "news_analysis.py not found"}
    try:
        cmd = [sys.executable, script_path, code]
        if name:
            cmd.append(name)
        env = os.environ.copy()
        for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
            env.pop(k, None)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        output = r.stdout
        sentiment = "unknown"
        score = 0
        bullish = 0
        bearish = 0
        for line in output.split("\n"):
            if "情绪判定" in line or "情绪:" in line:
                if "偏多" in line: sentiment = "偏多"
                elif "偏空" in line: sentiment = "偏空"
                elif "中性" in line: sentiment = "中性"
            if "得分" in line:
                m = _re.search(r'得分[：:]\s*([0-9.]+)', line)
                if m: score = float(m.group(1))
            if "利多" in line or "利好" in line:
                m = _re.search(r'(\d+)条', line)
                if m: bullish = int(m.group(1))
            if "利空" in line:
                m = _re.search(r'(\d+)条', line)
                if m: bearish = int(m.group(1))
        return {
            "sentiment": sentiment,
            "score": score,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "raw_output": output[:3000],
            "returncode": r.returncode
        }
    except Exception as e:
        return {"error": str(e)}

def compute_sentiment(klines, quote):
    """情绪周期分析(基于换手率和量能)"""
    if not klines or len(klines) < 10:
        return {"error": "K线数据不足"}

    volumes = [k.get("volume", 0) for k in klines]
    avg_20 = sum(volumes[-20:]) / min(20, len(volumes[-20:])) if volumes else 0
    avg_5 = sum(volumes[-5:]) / min(5, len(volumes[-5:])) if volumes else 0

    turnover = quote.get("turnover", 0) if quote else 0
    if turnover < 0.5:
        turnover_level = "冷淡底部"
    elif turnover < 2:
        turnover_level = "正常平稳"
    elif turnover < 5:
        turnover_level = "活跃升温"
    elif turnover < 10:
        turnover_level = "过热警惕"
    else:
        turnover_level = "极度过热"

    if avg_5 > avg_20 * 1.2:
        volume_trend = "放量"
    elif avg_5 < avg_20 * 0.8:
        volume_trend = "缩量"
    else:
        volume_trend = "持平"

    recent_5_vol = [k.get("volume", 0) for k in klines[-5:]] if len(klines) >= 5 else []
    if len(recent_5_vol) >= 2:
        if recent_5_vol[-1] > recent_5_vol[0] * 1.2:
            trend = "升温"
        elif recent_5_vol[-1] < recent_5_vol[0] * 0.8:
            trend = "降温"
        else:
            trend = "持平"
    else:
        trend = "unknown"

    return {
        "turnover": turnover,
        "turnover_level": turnover_level,
        "volume_trend": volume_trend,
        "5d_trend": trend,
        "avg_20_vol": round(avg_20),
        "avg_5_vol": round(avg_5)
    }

def check_risks(indicators, quote, klines):
    """7项风险筛查"""
    risks = []
    risks.append({"name": "大股东减持/质押", "checked": False, "note": "需agent搜索确认"})
    risks.append({"name": "业绩预亏/变脸", "checked": False, "note": "需agent搜索确认"})
    risks.append({"name": "监管处罚/立案", "checked": False, "note": "需agent搜索确认"})
    risks.append({"name": "行业政策利空", "checked": False, "note": "需agent搜索确认"})
    risks.append({"name": "限售解禁(30天内)", "checked": False, "note": "需agent搜索确认"})

    pe = quote.get("pe_ttm", 0) if quote else 0
    pb = quote.get("pb", 0) if quote else 0
    pe_abnormal = bool(pe and (pe > 100 or pe < 0))
    pb_abnormal = bool(pb and pb > 10)
    risks.append({
        "name": "估值异常",
        "checked": True,
        "result": pe_abnormal or pb_abnormal,
        "detail": f"PE={pe} PB={pb}" + (" ⚠️异常" if pe_abnormal or pb_abnormal else " ✓正常")
    })

    if indicators and klines and len(klines) > 0:
        current = klines[-1].get("close", 0)
        ma30 = indicators.get("ma30", 0)
        broken = bool(current < ma30 if ma30 > 0 else False)
        risks.append({
            "name": "技术破位(MA30)",
            "checked": True,
            "result": broken,
            "detail": f"当前{current} vs MA30={ma30}" + (" ⚠️跌破!" if broken else " ✓守住")
        })
    else:
        risks.append({"name": "技术破位(MA30)", "checked": False, "note": "数据不足"})

    return risks

# ═══════════════════════════════════════════════════════
# 计算函数
# ═══════════════════════════════════════════════════════

def _ema(data, period):
    """指数移动平均"""
    if not data:
        return []
    multiplier = 2 / (period + 1)
    ema = [data[0]]
    for i in range(1, len(data)):
        ema.append(data[i] * multiplier + ema[-1] * (1 - multiplier))
    return ema

def _atr(highs, lows, closes, period=14):
    """ATR"""
    if len(closes) < 2:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr

def _rsi(closes, period=6):
    """RSI (Wilder's EMA method)"""
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_indicators(klines):
    """计算技术指标"""
    if not klines or len(klines) < 20:
        return {}

    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    volumes = [k["volume"] for k in klines]

    # 均线
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else 0
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
    ma30 = sum(closes[-30:]) / 30 if len(closes) >= 30 else 0

    current = closes[-1]
    ma20_dev = ((current - ma20) / ma20 * 100) if ma20 else 0

    # 均线排列
    if ma5 > ma10 > ma20:
        ma_align = "多头"
    elif ma5 < ma10 < ma20:
        ma_align = "空头"
    else:
        ma_align = "纠缠"

    # MA20斜率(近5日)
    if len(closes) >= 25:
        ma20_5d_ago = sum(closes[-25:-5]) / 20
        ma20_slope = (ma20 - ma20_5d_ago) / ma20_5d_ago * 100 if ma20_5d_ago else 0
    else:
        ma20_slope = 0

    # MACD
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = [ema12[i] - ema26[i] for i in range(len(closes))]
    dea = _ema(dif, 9)
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]

    macd_golden = dif[-1] > dea[-1] and dif[-2] <= dea[-2] if len(dif) >= 2 else False
    macd_above_zero = dif[-1] > 0
    macd_bar_rising = macd_bar[-1] > macd_bar[-2] if len(macd_bar) >= 2 else False

    # RSI & ATR
    rsi6 = _rsi(closes, 6)
    atr14 = _atr(highs, lows, closes, 14)

    # 缩量比
    avg_vol_5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
    shrink = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1
    vol_ratio = volumes[-1] / avg_vol_5 if avg_vol_5 > 0 else 1

    # 支撑压力
    recent_lows = lows[-20:]
    recent_highs = highs[-20:]
    support = min(recent_lows)
    resistance = max(recent_highs)

    # 当前K线形态
    k = klines[-1]
    body = abs(k["close"] - k["open"])
    full_range = k["high"] - k["low"]
    lower_shadow = min(k["close"], k["open"]) - k["low"]
    upper_shadow = k["high"] - max(k["close"], k["open"])
    body_ratio = (body / full_range * 100) if full_range > 0 else 50
    lower_ratio = (lower_shadow / full_range * 100) if full_range > 0 else 0
    is_doji = body_ratio < 10
    has_long_lower = lower_shadow > body * 2 and lower_shadow > upper_shadow

    # 近5日涨跌
    bounce_pct = (closes[-1] - min(closes[-5:])) / min(closes[-5:]) * 100 if min(closes[-5:]) > 0 else 0
    drop_pct = (closes[-1] - max(closes[-5:])) / max(closes[-5:]) * 100 if max(closes[-5:]) > 0 else 0

    return {
        "current": current,
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma30": round(ma30, 2),
        "ma20_dev": round(ma20_dev, 2),
        "ma_align": ma_align,
        "ma20_slope": round(ma20_slope, 4),
        "rsi6": round(rsi6, 2),
        "shrink": round(shrink, 2),
        "vol_ratio": round(vol_ratio, 2),
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "dif": round(dif[-1], 4),
        "dea": round(dea[-1], 4),
        "macd_golden": macd_golden,
        "macd_above_zero": macd_above_zero,
        "macd_bar_rising": macd_bar_rising,
        "atr14": round(atr14, 2),
        "bounce_pct": round(bounce_pct, 2),
        "drop_pct": round(drop_pct, 2),
        "above_ma20": current > ma20,
        "kline": {
            "open": k["open"],
            "close": k["close"],
            "high": k["high"],
            "low": k["low"],
            "volume": k["volume"],
            "body_ratio": round(body_ratio, 1),
            "lower_ratio": round(lower_ratio, 1),
            "upper_shadow": round(upper_shadow, 2),
            "lower_shadow": round(lower_shadow, 2),
            "is_doji": is_doji,
            "has_long_lower": has_long_lower,
        },
        "patterns_3d": _detect_3day_patterns(klines),
    }

def _detect_3day_patterns(klines):
    """检测近3日组合形态"""
    if len(klines) < 3:
        return []
    patterns = []
    d1, d2, d3 = klines[-3], klines[-2], klines[-1]

    def lower_shadow(k):
        return min(k["close"], k["open"]) - k["low"]
    def body(k):
        return abs(k["close"] - k["open"])
    def full_range(k):
        return k["high"] - k["low"]

    # 双针探底
    if (lower_shadow(d2) > body(d2) * 1.5 and lower_shadow(d3) > body(d3) * 1.5
        and abs(d2["low"] - d3["low"]) / ((d2["low"] + d3["low"]) / 2) < 0.02):
        patterns.append("双针探底")

    # 十字星确认
    if body(d2) / full_range(d2) < 0.1 if full_range(d2) > 0 else False:
        if d3["close"] > d2["close"] and d3["close"] > d3["open"]:
            patterns.append("十字星确认")

    # 看涨吞没
    if d2["close"] < d2["open"] and d3["close"] > d3["open"]:
        if d3["close"] > d2["open"] and d3["open"] < d2["close"]:
            patterns.append("看涨吞没")

    return patterns

def compute_scores(indicators, fund_flow, quote):
    """综合评分"""
    if not indicators or not quote:
        return {"total_raw": 0, "score_100": 0, "score_5": 0, "dimensions": {}, "max_raw": 100}

    # 量价关系 (30分)
    vol_score = 0
    if indicators.get("shrink", 1) < 0.8:
        vol_score += 8
    if indicators.get("vol_ratio", 0) > 1.5:
        vol_score += 5
    if indicators.get("kline", {}).get("is_doji"):
        vol_score += 4
    if indicators.get("kline", {}).get("has_long_lower"):
        vol_score += 4
    if indicators.get("bounce_pct", 0) > 3:
        vol_score += 5
    if indicators.get("drop_pct", 0) < -5:
        vol_score -= 3
    vol_score = max(0, min(30, vol_score + 10))

    # 均线技术 (25分)
    tech_score = 0
    if indicators.get("ma_align") == "多头":
        tech_score += 10
    elif indicators.get("ma_align") == "纠缠":
        tech_score += 5
    if indicators.get("above_ma20"):
        tech_score += 5
    if indicators.get("macd_golden"):
        tech_score += 5
    if indicators.get("macd_above_zero"):
        tech_score += 3
    if indicators.get("macd_bar_rising"):
        tech_score += 2
    tech_score = max(0, min(25, tech_score))

    # 资金流向 (20分)
    fund_score = 10  # 默认中性
    if fund_flow:
        recent_net = fund_flow[-1].get("main_net", 0) if fund_flow else 0
        total_5d = sum(f.get("main_net", 0) for f in fund_flow[-5:]) if len(fund_flow) >= 5 else 0
        if total_5d > 0:
            fund_score = min(20, 10 + int(total_5d / 1e7))
        elif total_5d < 0:
            fund_score = max(0, 10 - int(abs(total_5d) / 1e7))

    # 估值安全 (10分)
    val_score = 5
    pe = quote.get("pe_ttm", 0)
    if pe and 0 < pe < 30:
        val_score = 8
    elif pe and 30 <= pe < 60:
        val_score = 5
    elif pe and pe >= 60:
        val_score = 2
    elif pe and pe < 0:
        val_score = 1

    # 消息面 (15分) - 默认中性
    msg_score = 7.5

    total = vol_score + tech_score + fund_score + val_score + msg_score
    max_raw = 100

    return {
        "dimensions": {
            "量价关系": {"score": vol_score, "max": 30, "weight": 0.3},
            "资金流向": {"score": fund_score, "max": 20, "weight": 0.2},
            "均线技术": {"score": tech_score, "max": 25, "weight": 0.25},
            "估值安全": {"score": val_score, "max": 10, "weight": 0.1},
            "消息面": {"score": msg_score, "max": 15, "weight": 0.15},
        },
        "total_raw": total,
        "score_100": total,
        "score_5": round(total / 20, 2),
        "total_weighted": total,
        "max_raw": max_raw,
    }

# ═══════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════

def main():
    try:
        if len(sys.argv) < 2:
            print("用法: python3 deep_analysis.py <股票代码> [股票名称]")
            sys.exit(1)

        code = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else ""

        print(f"{'='*60}")
        print(f"  深度分析数据采集 | {code} {name}")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        result = {"code": code, "name": name, "timestamp": datetime.now().isoformat(), "version": "5.0", "steps_completed": []}
        errors = []

        # Step 0: 前复权检查(需先获取K线用于跳空检测)
        print("\n[Step 0/15] 前复权检查...")
        klines = fetch_tencent_kline(code, 60)  # 提前获取,Step 4复用
        ex_right = fetch_ex_right(code, klines)
        result["ex_right_check"] = ex_right
        result["steps_completed"].append("step0")
        if ex_right.get("ex_right"):
            print(f"  ⚠️ 近期有除权: {ex_right.get('note','')}")
        else:
            print(f"  ✓ {ex_right.get('note','无除权记录')}")

        time.sleep(1)

        # Step 1: 核心数据速览
        print("\n[Step 1/15] 核心数据速览...")
        quote = tencent_quote(code)
        if quote:
            result["quote"] = quote
            if not name:
                result["name"] = quote.get("name", "")
            print(f"  ✓ {quote.get('name','')} 现价{quote.get('price',0)} 涨跌{quote.get('change_pct',0)}%")
            result["steps_completed"].append("step1")
        else:
            errors.append("Step1: 行情获取失败")
            print(f"  ✗ 行情获取失败")

        # Step 2: 历史复盘
        print("\n[Step 2/15] 历史复盘...")
        report_dir = os.path.expanduser("~/stock-reports")
        prev_report = None
        if os.path.exists(report_dir):
            stock_name = result.get("name", "")
            for d in os.listdir(report_dir):
                if code in d or stock_name in d:
                    sub_dir = os.path.join(report_dir, d)
                    if os.path.isdir(sub_dir):
                        reports = sorted([f for f in os.listdir(sub_dir) if f.endswith(".md") and "深度分析" in f], reverse=True)
                        if reports:
                            prev_report = os.path.join(sub_dir, reports[0])
                            break
        result["prev_report"] = prev_report
        result["steps_completed"].append("step2")
        if prev_report:
            print(f"  ✓ 找到上次报告: {os.path.basename(prev_report)}")
        else:
            print(f"  ⓘ 首次分析,无历史报告")

        # Step 3: 市场环境
        print("\n[Step 3/15] 市场环境分析...")
        indices = fetch_market_indices()
        result["indices"] = indices
        for idx_name, idx_data in indices.items():
            print(f"  {idx_name}: {idx_data['price']} ({idx_data['change_pct']:+.2f}%)")

        boards = fetch_board_info(code)
        result["boards"] = boards
        print(f"  板块({len(boards)}个): {', '.join(boards[:5])}{'...' if len(boards)>5 else ''}")

        # Step 1E: 板块分析
        print("\n[Step 1E/15] 板块分析...")
        sector_result = call_sector_analysis(code, result.get("name", ""))
        result["sector_analysis"] = sector_result
        result["steps_completed"].append("step1e")
        if sector_result.get("error"):
            print(f"  ✗ 板块分析失败: {sector_result['error']}")
        else:
            print(f"  ✓ 板块分析完成({len(sector_result.get('sectors',[]))}个板块)")

        # 北向资金
        print("\n[Step 3B/15] 北向资金...")
        northbound = fetch_northbound()
        result["northbound"] = northbound
        if northbound.get("error") or not northbound.get("available"):
            print(f"  ✗ 北向资金获取失败: {northbound.get('error','未知')}")
        else:
            print(f"  沪股通: {northbound.get('hgt',0)}亿 | 深股通: {northbound.get('sgt',0)}亿 | 合计: {northbound.get('total',0)}亿")
        result["steps_completed"].append("step3")

        time.sleep(1)

        # Step 4: 量价关系(klines已在Step 0获取)
        print("\n[Step 4/15] 量价关系分析...")
        result["klines_30d"] = klines[-30:] if klines else []
        if klines and len(klines) >= 20:
            indicators = compute_indicators(klines)
            result["indicators"] = indicators
            print(f"  ✓ K线{len(klines)}根, 形态: {'十字星' if indicators.get('kline',{}).get('is_doji') else '正常'}")
            print(f"  缩量比: {indicators.get('shrink','?')} | 量比: {indicators.get('vol_ratio','?')}")
            if indicators.get("patterns_3d"):
                print(f"  3日形态: {', '.join(indicators['patterns_3d'])}")
            result["steps_completed"].append("step4")
        else:
            errors.append("Step4: K线数据不足")
            indicators = {}
            result["indicators"] = {}
            print(f"  ✗ K线数据不足")

        time.sleep(1)

        # Step 5: 资金流向(mx-data API)
        print("\n[Step 5/15] 资金流向分析...")
        fund_flow, ddx_info = fetch_fund_flow_mxdata(code, result.get("name", ""))
        result["fund_flow"] = fund_flow
        result["ddx_info"] = ddx_info
        if isinstance(fund_flow, list) and fund_flow:
            recent_net = fund_flow[0].get("main_net", 0) if fund_flow else 0
            total_5d = sum(f.get("main_net", 0) for f in fund_flow[:5]) if len(fund_flow) >= 5 else 0
            print(f"  ✓ 获取{len(fund_flow)}日数据(source:mx-data)")
            print(f"  最近1日主力净流: {recent_net/1e4:.0f}万 | 近5日: {total_5d/1e4:.0f}万")
            if ddx_info:
                print(f"  DDX={ddx_info.get('ddx','?')} DDY={ddx_info.get('ddy','?')} 5日DDX={ddx_info.get('5d_ddx','?')}")
            result["steps_completed"].append("step5")
        else:
            err_msg = fund_flow.get("error", "未知") if isinstance(fund_flow, dict) else "空数据"
            errors.append(f"Step5: {err_msg}")
            print(f"  ✗ 资金流获取失败: {err_msg}")

        # Step 6: 均线与技术面
        print("\n[Step 6/15] 均线与技术面...")
        if indicators:
            print(f"  MA5={indicators.get('ma5')} MA10={indicators.get('ma10')} MA20={indicators.get('ma20')} MA30={indicators.get('ma30')}")
            print(f"  MA20偏离: {indicators.get('ma20_dev','?')}% | 排列: {indicators.get('ma_align','?')}")
            print(f"  MA20斜率: {indicators.get('ma20_slope','?')}%")
            print(f"  ATR14: {indicators.get('atr14','?')} | RSI6: {indicators.get('rsi6','?')}")
            print(f"  支撑: {indicators.get('support','?')} | 压力: {indicators.get('resistance','?')}")
            print(f"  MACD: 金叉{'✓' if indicators.get('macd_golden') else '✗'} 零轴{'↑' if indicators.get('macd_above_zero') else '↓'} 柱状{'↑' if indicators.get('macd_bar_rising') else '↓'}")
            result["steps_completed"].append("step6")
        else:
            print(f"  ✗ 无技术指标数据")

        # Step 10: 情绪周期分析
        print("\n[Step 10/15] 情绪周期分析...")
        sentiment = compute_sentiment(klines, quote)
        result["sentiment"] = sentiment
        result["steps_completed"].append("step10")
        print(f"  换手率: {sentiment.get('turnover','?')}% ({sentiment.get('turnover_level','?')})")
        print(f"  量能趋势: {sentiment.get('volume_trend','?')}")
        print(f"  5日走势: {sentiment.get('5d_trend','?')}")

        # Step 7: 估值与基本面
        print("\n[Step 7/15] 估值与基本面...")
        if quote:
            print(f"  PE(TTM): {quote.get('pe_ttm','?')}")
            print(f"  PB: {quote.get('pb','?')}")
            print(f"  流通市值: {quote.get('mcap','?')}亿")
            print(f"  换手率: {quote.get('turnover','?')}%")
            result["steps_completed"].append("step7")

        # Step 11: 概念板块完整映射
        print("\n[Step 11/15] 概念板块映射...")
        concept_blocks = fetch_concept_blocks(code)
        result["concept_blocks"] = concept_blocks
        result["steps_completed"].append("step11")
        if concept_blocks.get("error"):
            print(f"  ✗ 概念获取失败: {concept_blocks['error']}")
        else:
            print(f"  ✓ 获取{concept_blocks.get('count',0)}个概念: {', '.join(b['name'] for b in concept_blocks.get('blocks',[])[:5])}")

        time.sleep(1)

        # Step 12: 消息面
        print("\n[Step 12/15] 消息面分析...")
        news = call_news_analysis(code, result.get("name", ""))
        result["news_analysis"] = news
        result["steps_completed"].append("step12")
        if news.get("error"):
            print(f"  ✗ 消息面获取失败: {news['error']}")
        else:
            print(f"  情绪: {news.get('sentiment','?')} (得分:{news.get('score',0)})")
            print(f"  利好{news.get('bullish_count',0)}条/利空{news.get('bearish_count',0)}条")

        time.sleep(1)

        # Step 8: 综合评分
        print("\n[Step 8/15] 综合评分...")
        if indicators and quote:
            scores = compute_scores(indicators, fund_flow, quote)
            result["scores"] = scores
            print(f"  量价关系: {scores['dimensions']['量价关系']['score']:.1f}/{scores['dimensions']['量价关系']['max']}")
            print(f"  资金流向: {scores['dimensions']['资金流向']['score']:.1f}/{scores['dimensions']['资金流向']['max']}")
            print(f"  均线技术: {scores['dimensions']['均线技术']['score']:.1f}/{scores['dimensions']['均线技术']['max']}")
            print(f"  估值安全: {scores['dimensions']['估值安全']['score']:.1f}/{scores['dimensions']['估值安全']['max']}")
            print(f"  消息面: {scores['dimensions']['消息面']['score']:.1f}/{scores['dimensions']['消息面']['max']}")
            print(f"  ─────────────────")
            print(f"  原始总分: {scores['total_raw']:.1f}/{scores['max_raw']}")
            print(f"  100分制: {scores['score_100']:.1f}/100 | 5分制: {scores['score_5']:.2f}/5.0")
            result["steps_completed"].append("step8")
        else:
            print(f"  ✗ 无法评分(数据不足)")

        # Step 14: 风险筛查(7项清单)
        print("\n[Step 14/15] 风险筛查(7项)...")
        risks = check_risks(indicators, quote, klines)
        if indicators:
            if indicators.get("shrink", 99) > 1.2:
                risks.append({"name": "量能放大", "checked": True, "result": True, "detail": "量比>1.2"})
            if indicators.get("ma20_slope", 0) < -0.3:
                risks.append({"name": "MA20下降趋势", "checked": True, "result": True, "detail": f"斜率{indicators['ma20_slope']}%"})
        result["risks"] = risks
        result["steps_completed"].append("step14")
        risk_count = sum(1 for r in risks if r.get("result"))
        print(f"  已检查{len(risks)}项, 发现{risk_count}项风险")
        for r in risks:
            if r.get("result"):
                print(f"  ⚠️ {r['name']}: {r.get('detail','')}")
            elif r.get("checked"):
                print(f"  ✓ {r['name']}: {r.get('detail','正常')}")
            else:
                print(f"  ⓘ {r['name']}: {r.get('note','待查')}")

        # Step 15: 附录
        print("\n[Step 15/15] 附录数据...")
        print(f"  K线数据: {len(result.get('klines_30d', []))}根")
        print(f"  资金流: {len(fund_flow)}日")
        result["steps_completed"].append("step15")

        # 保存结果
        result["errors"] = errors
        output_path = f"/tmp/deep_analysis_{code}.json"
        with open(output_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"  数据采集完成(V5) | 保存至: {output_path}")
        print(f"  完成步骤: {len(result.get('steps_completed',[]))}/15")
        print(f"  错误: {len(errors)}个 {'('+', '.join(errors)+')' if errors else ''}")
        print(f"{'='*60}")

    except Exception as e:
        code = sys.argv[1] if len(sys.argv) > 1 else "unknown"
        output_path = f"/tmp/deep_analysis_{code}.json"
        error_result = {
            "code": code,
            "timestamp": datetime.now().isoformat(),
            "version": "5.0",
            "errors": [f"致命错误: {str(e)}"],
            "exception": str(e)
        }
        try:
            with open(output_path, "w") as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
            print(f"\n✗ 致命错误: {e}")
            print(f"  错误JSON已保存至: {output_path}")
        except Exception:
            print(f"\n✗ 致命错误且无法保存JSON: {e}")

if __name__ == "__main__":
    main()
