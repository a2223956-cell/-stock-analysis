#!/usr/bin/env python3
"""
深度分析数据采集器 — 10步模板
用法: python3 deep_analysis.py <股票代码> [股票名称]

输出: /tmp/deep_analysis_<code>.json
所有数据通过API获取,禁止编造。脚本只采集数据,不写分析结论。

10步模板:
  1. 核心数据速览 (腾讯实时行情)
  2. 历史复盘 (如有上次报告则对比)
  3. 市场环境分析 (大盘指数 + 板块)
  4. 量价关系深度分析 (30日K线 + 形态标注)
  5. 资金流向分析 (20日逐日资金流)
  6. 均线与技术面分析 (MA5/10/20/30 + 支撑压力)
  7. 估值与基本面分析 (PE/PB + 板块 + 机构预测)
  8. 综合评分与操作建议 (5维度加权)
  9. 风险提示
  10. 附录: 完整K线数据
"""
import sys, os, json, time, urllib.request
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/mx-moni/scripts"))

from quote_utils import tencent_quote, get_prefix

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
            if len(item) >= 6:
                result.append({
                    "date": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5])
                })
        return result
    except:
        return None

def fetch_eastmoney_fund_flow(code):
    """东财资金流向(20日), 带镜像重试"""
    if code.startswith("6"):
        prefix = "1"  # 沪市
    elif code.startswith(("0", "3")):
        prefix = "0"  # 深市
    elif code.startswith(("8", "4")):
        prefix = "0"  # 北交所(用深市前缀)
    else:
        prefix = "0"
    path = f"/api/qt/stock/fflow/kline/get?secid={prefix}.{code}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&lmt=20"
    # 镜像域名列表(主域名可能被WAF)
    mirrors = [
        "https://push2his.eastmoney.com",
        "https://1.push2his.eastmoney.com",
        "https://2.push2his.eastmoney.com",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/"
    }
    for mirror in mirrors:
        try:
            data = fetch_json(mirror + path, headers=headers)
            klines = data.get("data", {}).get("klines", [])
            if klines:  # 有数据才返回
                result = []
                for k in klines:
                    parts = k.split(",")
                    if len(parts) >= 7:
                        result.append({
                            "date": parts[0],
                            "main_net": float(parts[1]),
                            "small_net": float(parts[2]),
                            "mid_net": float(parts[3]),
                            "big_net": float(parts[4]),
                            "super_net": float(parts[5]),
                            "unit": "yuan"
                        })
                return result
        except:
            continue
    return []  # 所有镜像都失败

def fetch_board_info(code):
    """东财板块信息"""
    if code.startswith(('0', '3')):
        suffix = 'SZ'
    elif code.startswith(('8', '4', '9')):
        suffix = 'BJ'
    else:
        suffix = 'SH'
    url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_F10_CORETHEME_BOARDTYPE&columns=SECUCODE,SECURITY_NAME_ABBR,BOARD_CODE,BOARD_NAME,IS_PRECISE,BOARD_RANK,BOARD_TYPE&filter=(SECUCODE=%22{code}.{suffix}%22)&pageSize=50"
    try:
        data = fetch_json(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/"
        })
        items = data.get("result", {}).get("data", [])
        return [i.get("BOARD_NAME", "") for i in items if i.get("BOARD_NAME")]
    except:
        return []

def fetch_market_indices():
    """腾讯大盘指数"""
    codes = "sh000001,sz399001,sz399006"
    url = f"https://qt.gtimg.cn/q={codes}"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("gbk")
        indices = {}
        for seg in raw.split(";"):
            if "=" not in seg or "~" not in seg:
                continue
            body = seg.split("=", 1)[1].strip().strip('"')
            vals = body.split("~")
            if len(vals) < 35:
                continue
            name = vals[1]
            price = float(vals[3]) if vals[3] else 0
            change_pct = float(vals[32]) if vals[32] else 0
            indices[name] = {"price": price, "change_pct": change_pct}
        return indices
    except:
        return {}

# ═══════════════════════════════════════════════════════
# 技术指标计算
# ═══════════════════════════════════════════════════════

def compute_indicators(klines):
    """计算MA/MACD/RSI/ATR等技术指标"""
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

    # MA20斜率(5日)
    if len(closes) >= 25:
        ma20_today = sum(closes[-20:]) / 20
        ma20_5d_ago = sum(closes[-25:-5]) / 20
        ma20_slope = (ma20_today - ma20_5d_ago) / ma20_5d_ago * 100 if ma20_5d_ago > 0 else 0
    else:
        ma20_slope = 0

    # MA排列(含MA30)
    if ma5 > ma10 > ma20 > ma30:
        ma_align = "多头"
    elif ma5 < ma10 < ma20 < ma30:
        ma_align = "空头"
    else:
        ma_align = "纠缠"

    # MACD
    if len(closes) >= 26:
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        # 对齐长度: ema12比ema26长(period差)
        offset = len(ema12) - len(ema26)
        dif = [ema12[offset + i] - ema26[i] for i in range(len(ema26))]
        dea = _ema(dif, 9)
        # 对齐: dif比dea长(EMA period差)
        dea_offset = len(dif) - len(dea)
        macd_bar = [(dif[dea_offset + i] - dea[i]) * 2 for i in range(len(dea))]
        macd_golden = dif[-1] > dea[-1] and dif[-2] <= dea[-2] if len(dif) >= 2 else False
        macd_above_zero = dif[-1] > 0
        macd_bar_rising = macd_bar[-1] > macd_bar[-2] if len(macd_bar) >= 2 else False
    else:
        dif = dea = macd_bar = []
        macd_golden = macd_above_zero = macd_bar_rising = False

    # ATR(14)
    atr14 = _atr(highs, lows, closes, 14)

    # RSI(6)
    rsi6 = _rsi(closes, 6)

    # 量能分析
    vol_5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
    vol_prev5 = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else 0
    shrink = vol_5 / vol_prev5 if vol_prev5 > 0 else 99
    vol_ratio = volumes[-1] / vol_5 if vol_5 > 0 else 1.0  # 当日量/5日均量(量比)

    # MA20偏离
    ma20_dev = (current / ma20 - 1) * 100 if ma20 > 0 else 0

    # 支撑压力
    recent_20_highs = highs[-20:]
    recent_20_lows = lows[-20:]
    resistance = max(recent_20_highs) if recent_20_highs else current
    support = min(recent_20_lows) if recent_20_lows else current

    # K线形态
    last_k = klines[-1]
    body = abs(last_k["close"] - last_k["open"])
    full_range = last_k["high"] - last_k["low"]
    body_ratio = (body / full_range * 100) if full_range > 0 else 100
    upper_shadow = last_k["high"] - max(last_k["close"], last_k["open"])
    lower_shadow = min(last_k["close"], last_k["open"]) - last_k["low"]
    lower_ratio = (lower_shadow / full_range * 100) if full_range > 0 else 0

    is_doji = body_ratio < 15
    has_long_lower = lower_ratio > 50

    # 近5日阶段判断
    if len(closes) >= 5:
        low_5d = min(closes[-5:])
        high_5d = max(closes[-5:])
        bounce_pct = (current - low_5d) / low_5d * 100 if low_5d > 0 else 0
        drop_pct = (current - high_5d) / high_5d * 100 if high_5d > 0 else 0
    else:
        bounce_pct = drop_pct = 0

    return {
        "current": current,
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma30": round(ma30, 2),
        "ma20_slope": round(ma20_slope, 4),
        "ma20_dev": round(ma20_dev, 2),
        "ma_align": ma_align,
        "above_ma20": current > ma20,
        "macd_golden": macd_golden,
        "macd_above_zero": macd_above_zero,
        "macd_bar_rising": macd_bar_rising,
        "dif": round(dif[-1], 4) if dif else 0,
        "dea": round(dea[-1], 4) if dea else 0,
        "atr14": round(atr14, 2),
        "rsi6": round(rsi6, 2),
        "shrink": round(shrink, 2),
        "vol_ratio": round(vol_ratio, 2),
        "resistance": round(resistance, 2),
        "support": round(support, 2),
        "kline": {
            "open": last_k["open"],
            "close": last_k["close"],
            "high": last_k["high"],
            "low": last_k["low"],
            "volume": last_k["volume"],
            "body_ratio": round(body_ratio, 1),
            "lower_ratio": round(lower_ratio, 1),
            "upper_shadow": round(upper_shadow, 2),
            "lower_shadow": round(lower_shadow, 2),
            "is_doji": is_doji,
            "has_long_lower": has_long_lower,
        },
        "patterns_3d": _detect_3day_patterns(klines),
        "bounce_pct": round(bounce_pct, 2),
        "drop_pct": round(drop_pct, 2),
    }

def _ema(data, period):
    """指数移动平均"""
    if len(data) < period:
        return data[:]
    ema = [sum(data[:period]) / period]
    k = 2 / (period + 1)
    for i in range(period, len(data)):
        ema.append(data[i] * k + ema[-1] * (1 - k))
    return ema

def _atr(highs, lows, closes, period=14):
    """平均真实波幅 (Wilder's EMA平滑)"""
    if len(highs) < period + 1:
        return 0
    trs = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    # Wilder's EMA: 先用前period个简单平均，后续用EMA平滑
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return round(atr, 2)

def _rsi(closes, period=6):
    """相对强弱指标 (Wilder's EMA平滑)"""
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    # Wilder's EMA: 先用前period个简单平均，后续用EMA平滑
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
    return round(100 - (100 / (1 + rs)), 2)

def _detect_3day_patterns(klines):
    """检测3日组合K线形态"""
    if not klines or len(klines) < 3:
        return []
    patterns = []
    d0 = klines[-1]  # 今日
    d1 = klines[-2]  # 昨日
    d2 = klines[-3]  # 前日

    # 双针探底: 连续2日长下影(下影>实体2倍), 且价格处于低位(低于MA20)
    def _lower_shadow(k):
        return min(k["close"], k["open"]) - k["low"]
    def _body(k):
        return abs(k["close"] - k["open"])
    def _full_range(k):
        return k["high"] - k["low"]

    body0, body1 = _body(d0), _body(d1)
    ls0, ls1 = _lower_shadow(d0), _lower_shadow(d1)
    fr0, fr1 = _full_range(d0), _full_range(d1)
    if body0 > 0 and body1 > 0 and ls0 > body0 * 2 and ls1 > body1 * 2:
        # 低位校验: 当前价格需低于MA20
        if len(klines) >= 20:
            closes = [k["close"] for k in klines[-20:]]
            ma20 = sum(closes) / 20
            if d0["close"] < ma20:
                patterns.append("双针探底")
        else:
            # 数据不足20日时,仍添加形态但标注
            patterns.append("双针探底")

    # 看涨吞没: 前日阴线+今日阳线完全包裹前日实体
    d1_bearish = d1["close"] < d1["open"]
    d0_bullish = d0["close"] > d0["open"]
    if d1_bearish and d0_bullish:
        d1_body_top = max(d1["close"], d1["open"])
        d1_body_bot = min(d1["close"], d1["open"])
        d0_body_top = max(d0["close"], d0["open"])
        d0_body_bot = min(d0["close"], d0["open"])
        if d0_body_top > d1_body_top and d0_body_bot < d1_body_bot:
            patterns.append("看涨吞没")

    # 放量滞涨: 今日量>昨日量×1.5 但涨幅<0.5%
    if d1["volume"] > 0 and d0["volume"] > d1["volume"] * 1.5:
        if d1["close"] > 0:
            change_pct = (d0["close"] - d1["close"]) / d1["close"] * 100
            if abs(change_pct) < 0.5:
                patterns.append("放量滞涨")

    return patterns

# ═══════════════════════════════════════════════════════
# 5维度评分
# ═══════════════════════════════════════════════════════

def compute_scores(indicators, fund_flow, quote):
    """5维度加权评分(100分制)"""
    scores = {}

    # 维度1: 量价关系 (30分满分)
    vol_score = 0
    if indicators.get("shrink", 99) < 0.8:
        vol_score += 15
    kline = indicators.get("kline", {})
    if kline.get("is_doji") or kline.get("has_long_lower"):
        vol_score += 10
    if indicators.get("bounce_pct", 0) > 3:
        vol_score += 5
    vol_score = min(vol_score, 30)
    scores["量价关系"] = {"score": vol_score, "max": 30, "weight": 0.30}

    # 维度2: 资金流向 (20分满分)
    fund_score = 0
    if fund_flow:
        recent_3 = fund_flow[-3:] if len(fund_flow) >= 3 else fund_flow
        net_3d = sum(f["main_net"] for f in recent_3)
        if net_3d > 0:
            fund_score += 12
        if fund_flow and fund_flow[-1].get("main_net", 0) > 0:
            fund_score += 8
    else:
        fund_score = 10  # 数据缺失时给中性分(满分20的50%)
    fund_score = min(fund_score, 20)
    scores["资金流向"] = {"score": fund_score, "max": 20, "weight": 0.20}

    # 维度3: 均线技术 (25分满分)
    tech_score = 0
    if indicators.get("ma_align") == "多头":
        tech_score += 10
    elif indicators.get("ma_align") == "纠缠":
        tech_score += 5
    if indicators.get("above_ma20"):
        tech_score += 5
    if indicators.get("ma20_slope", 0) > 0:
        tech_score += 5
    if indicators.get("rsi6", 50) < 30:
        tech_score += 3
    elif indicators.get("rsi6", 50) > 70:
        tech_score -= 2
    tech_score = max(0, min(tech_score, 25))
    scores["均线技术"] = {"score": tech_score, "max": 25, "weight": 0.25}

    # 维度4: 估值安全 (10分满分)
    pe = quote.get("pe_ttm", 0)
    val_score = 0
    if 0 < pe < 30:
        val_score += 8
    elif 30 <= pe < 50:
        val_score += 5
    elif pe >= 50:
        val_score += 2
    pb = quote.get("pb", 0)
    if 0 < pb < 3:
        val_score += 2
    val_score = min(val_score, 10)
    scores["估值安全"] = {"score": val_score, "max": 10, "weight": 0.10}

    # 维度5: 消息面 (15分满分)
    news_score = 7.5  # 默认中性
    scores["消息面"] = {"score": news_score, "max": 15, "weight": 0.15}

    # 加权总分(直接100分制)
    total_weighted = sum(s["score"] * s["weight"] / s["max"] * 100 for s in scores.values() if s["max"] > 0)
    total_raw = sum(s["score"] for s in scores.values())

    score_100 = round(total_weighted, 2)
    score_5 = round(score_100 / 20, 2)  # 5分制兼容

    return {
        "dimensions": scores,
        "total_raw": round(total_raw, 2),
        "score_100": score_100,
        "score_5": score_5,
        "total_weighted": score_100,  # 兼容旧字段
        "max_raw": sum(s["max"] for s in scores.values()),
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

        result = {"code": code, "name": name, "timestamp": datetime.now().isoformat()}
        errors = []

        # Step 1: 核心数据速览
        print("\n[Step 1/10] 核心数据速览...")
        quote = tencent_quote(code)
        if quote:
            result["quote"] = quote
            if not name:
                result["name"] = quote.get("name", "")
            print(f"  ✓ {quote.get('name','')} 现价{quote.get('price',0)} 涨跌{quote.get('change_pct',0)}%")
        else:
            errors.append("Step1: 行情获取失败")
            print(f"  ✗ 行情获取失败")

        # Step 2: 历史复盘(检查是否有上次报告)
        print("\n[Step 2/10] 历史复盘...")
        report_dir = os.path.expanduser("~/stock-reports")
        prev_report = None
        if os.path.exists(report_dir):
            # 搜索子目录(如 许继电气_000400/)
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
        if prev_report:
            print(f"  ✓ 找到上次报告: {os.path.basename(prev_report)}")
        else:
            print(f"  ⓘ 首次分析,无历史报告")

        # Step 3: 市场环境
        print("\n[Step 3/10] 市场环境分析...")
        indices = fetch_market_indices()
        result["indices"] = indices
        for idx_name, idx_data in indices.items():
            print(f"  {idx_name}: {idx_data['price']} ({idx_data['change_pct']:+.2f}%)")

        boards = fetch_board_info(code)
        result["boards"] = boards
        print(f"  板块({len(boards)}个): {', '.join(boards[:5])}{'...' if len(boards)>5 else ''}")

        # Step 4: 量价关系
        print("\n[Step 4/10] 量价关系分析...")
        klines = fetch_tencent_kline(code, 60)
        result["klines_30d"] = klines[-30:] if klines else []
        if klines and len(klines) >= 20:
            indicators = compute_indicators(klines)
            result["indicators"] = indicators
            print(f"  ✓ K线{len(klines)}根, 形态: {'十字星' if indicators.get('kline',{}).get('is_doji') else '正常'}")
            print(f"  缩量比: {indicators.get('shrink','?')} | 量比: {indicators.get('vol_ratio','?')}")
            if indicators.get("patterns_3d"):
                print(f"  3日形态: {', '.join(indicators['patterns_3d'])}")
        else:
            errors.append("Step4: K线数据不足")
            indicators = {}
            result["indicators"] = {}
            print(f"  ✗ K线数据不足")

        # Step 5: 资金流向
        print("\n[Step 5/10] 资金流向分析...")
        fund_flow = fetch_eastmoney_fund_flow(code)
        result["fund_flow"] = fund_flow
        if fund_flow:
            recent_net = fund_flow[-1].get("main_net", 0) if fund_flow else 0
            total_5d = sum(f.get("main_net", 0) for f in fund_flow[-5:]) if len(fund_flow) >= 5 else 0
            print(f"  ✓ 获取{len(fund_flow)}日数据")
            print(f"  最近1日主力净流: {recent_net/1e4:.0f}万 | 近5日: {total_5d/1e4:.0f}万")
        else:
            errors.append("Step5: 资金流数据为空")
            print(f"  ✗ 资金流数据为空")

        # Step 6: 均线与技术面(已在Step4计算)
        print("\n[Step 6/10] 均线与技术面...")
        if indicators:
            print(f"  MA5={indicators.get('ma5')} MA10={indicators.get('ma10')} MA20={indicators.get('ma20')} MA30={indicators.get('ma30')}")
            print(f"  MA20偏离: {indicators.get('ma20_dev','?')}% | 排列: {indicators.get('ma_align','?')}")
            print(f"  MA20斜率: {indicators.get('ma20_slope','?')}%")
            print(f"  ATR14: {indicators.get('atr14','?')} | RSI6: {indicators.get('rsi6','?')}")
            print(f"  支撑: {indicators.get('support','?')} | 压力: {indicators.get('resistance','?')}")
            print(f"  MACD: 金叉{'✓' if indicators.get('macd_golden') else '✗'} 零轴{'↑' if indicators.get('macd_above_zero') else '↓'} 柱状{'↑' if indicators.get('macd_bar_rising') else '↓'}")
        else:
            print(f"  ✗ 无技术指标数据")

        # Step 7: 估值与基本面
        print("\n[Step 7/10] 估值与基本面...")
        if quote:
            print(f"  PE(TTM): {quote.get('pe_ttm','?')}")
            print(f"  PB: {quote.get('pb','?')}")
            print(f"  流通市值: {quote.get('mcap','?')}亿")
            print(f"  换手率: {quote.get('turnover','?')}%")

        # Step 8: 综合评分
        print("\n[Step 8/10] 综合评分...")
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
        else:
            print(f"  ✗ 无法评分(数据不足)")

        # Step 9: 风险提示(基础风险)
        print("\n[Step 9/10] 风险提示...")
        risks = []
        if indicators:
            if indicators.get("shrink", 99) > 1.2:
                risks.append("量能放大,可能有分歧")
            if indicators.get("ma20_slope", 0) < -0.3:
                risks.append("MA20下降趋势")
            if not indicators.get("above_ma20"):
                risks.append("价格低于MA20")
            if indicators.get("drop_pct", 0) < -10:
                risks.append("近5日大幅回调")
        if quote:
            pe = quote.get("pe_ttm", 0)
            if pe and pe > 50:
                risks.append(f"PE偏高({pe})")
            if pe and pe < 0:
                risks.append("亏损企业")
            turnover = quote.get("turnover", 0)
            if turnover and turnover > 10:
                risks.append(f"换手率过高({turnover}%)")
        result["risks"] = risks
        for r in risks:
            print(f"  ⚠️ {r}")
        if not risks:
            print(f"  ✓ 无明显风险")

        # Step 10: 附录(K线数据已在Step4采集)
        print("\n[Step 10/10] 附录数据...")
        print(f"  K线数据: {len(result.get('klines_30d', []))}根")
        print(f"  资金流: {len(fund_flow)}日")

        # 保存结果
        result["errors"] = errors
        output_path = f"/tmp/deep_analysis_{code}.json"
        with open(output_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"  数据采集完成 | 保存至: {output_path}")
        print(f"  错误: {len(errors)}个 {'('+', '.join(errors)+')' if errors else ''}")
        print(f"{'='*60}")

    except Exception as e:
        # 异常时也输出JSON(含errors字段)
        code = sys.argv[1] if len(sys.argv) > 1 else "unknown"
        output_path = f"/tmp/deep_analysis_{code}.json"
        error_result = {
            "code": code,
            "timestamp": datetime.now().isoformat(),
            "errors": [f"致命错误: {str(e)}"],
            "exception": str(e)
        }
        try:
            with open(output_path, "w") as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
            print(f"\n✗ 致命错误: {e}")
            print(f"  错误JSON已保存至: {output_path}")
        except:
            print(f"\n✗ 致命错误且无法保存JSON: {e}")

if __name__ == "__main__":
    main()
