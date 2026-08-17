#!/usr/bin/env python3
"""
A股消息面分析模块
数据源: 东财个股新闻 + 东财全球资讯 + 东财搜索API + 同花顺快讯 + 巨潮公告
V3.0: 彻底移除 akshare 依赖，全部直连 HTTP API
"""

import json
import re
import time
import random
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

import requests

# ── 东财防封：全局节流 + 会话复用 ────────────────────────────────────
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
EM_SESSION = requests.Session()
EM_SESSION.headers.update({"User-Agent": UA})
try:
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    _em_adapter = HTTPAdapter(max_retries=Retry(
        total=3, connect=3, backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"]))
    EM_SESSION.mount("https://", _em_adapter)
    EM_SESSION.mount("http://", _em_adapter)
except Exception:
    pass
EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]


def em_get(url, params=None, headers=None, timeout=15, **kwargs):
    """东财统一请求入口：自动节流 + 复用 session + 默认 UA。"""
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return EM_SESSION.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
    finally:
        _em_last_call[0] = time.time()


# ── 巨潮公告辅助函数 ──────────────────────────────────────────────────
_CNINFO_ORGID_MAP = {}


def _cninfo_ts_to_date(ts):
    """巨潮 announcementTime 返回 Unix 毫秒整数，需转换为日期字符串。"""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    return str(ts)[:10] if ts else ""


def _cninfo_orgid(code):
    """查股票真实 orgId。优先动态查官方映射表，查不到再回退硬编码。"""
    global _CNINFO_ORGID_MAP
    if not _CNINFO_ORGID_MAP:
        try:
            r = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json",
                             headers={"User-Agent": UA}, timeout=15)
            _CNINFO_ORGID_MAP = {s["code"]: s["orgId"]
                                 for s in r.json().get("stockList", [])}
        except Exception as e:
            print(f"[WARN] 巨潮 orgId 映射表拉取失败，回退硬编码规则: {e}")
    org = _CNINFO_ORGID_MAP.get(code)
    if org:
        return org
    if code.startswith("6"):
        return f"gssh0{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"gsbj0{code}"
    return f"gssz0{code}"


# ── 数据源函数 ─────────────────────────────────────────────────────────

def fetch_stock_news_em(symbol, limit=10):
    """
    东财个股新闻（直连 search-api-web JSONP，替代 akshare stock_news_em）
    返回: [{title, content, time, source, url}, ...]
    """
    try:
        cb = "jQuery_news"
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        inner_params = json.dumps({
            "uid": "",
            "keyword": symbol,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                      "pageIndex": 1, "pageSize": limit, "preTag": "", "postTag": ""}},
        }, separators=(',', ':'))
        params = {"cb": cb, "param": inner_params}
        headers = {"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}
        r = em_get(url, params=params, headers=headers, timeout=15)

        text = r.text
        json_str = text[text.index("(") + 1:text.rindex(")")]
        d = json.loads(json_str)

        articles = d.get("result", {}).get("cmsArticleWebOld", []) or []
        results = []
        for a in articles[:limit]:
            results.append({
                "title": re.sub(r'<[^>]+>', '', a.get("title", "")),
                "content": re.sub(r'<[^>]+>', '', a.get("content", ""))[:200],
                "time": a.get("date", ""),
                "source": a.get("mediaName", ""),
                "url": a.get("url", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_global_news_em(limit=50):
    """
    东财全球资讯 7x24（直连 np-weblist，替代 akshare stock_info_global_em）
    返回: [{title, summary, time, url}, ...]
    """
    try:
        import uuid
        url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
        params = {
            "client": "web", "biz": "web_724",
            "fastColumn": "102", "sortEnd": "",
            "pageSize": str(limit),
            "req_trace": str(uuid.uuid4()),
        }
        headers = {"User-Agent": UA, "Referer": "https://kuaixun.eastmoney.com/"}
        r = em_get(url, params=params, headers=headers, timeout=10)
        d = r.json()

        results = []
        for item in d.get("data", {}).get("fastNewsList", []):
            results.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", "")[:200],
                "time": item.get("showTime", ""),
                "url": "",
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_ths_flash(limit=20):
    """
    同花顺快讯
    返回: [{title, time}, ...]
    """
    try:
        url = "https://news.10jqka.com.cn/tapp/news/push/stock/"
        params = {
            "page": "1",
            "tag": "",
            "track": "website",
            "pagesize": str(limit)
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0",
            "Referer": "https://news.10jqka.com.cn/"
        }
        r = requests.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        items = data.get("data", {}).get("list", [])
        results = []
        for item in items[:limit]:
            results.append({
                "title": item.get("title", ""),
                "time": item.get("pub_time", ""),
                "source": "同花顺",
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_cninfo_announcements(symbol, days=30):
    """
    巨潮公告（直连 cninfo.com.cn，替代 akshare stock_zh_a_disclosure_report_cninfo）
    返回: [{title, time, url}, ...]
    """
    try:
        url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        org_id = _cninfo_orgid(symbol)

        payload = {
            "stock": f"{symbol},{org_id}",
            "tabName": "fulltext",
            "pageSize": "30",
            "pageNum": "1",
            "column": "",
            "category": "",
            "plate": "",
            "seDate": "",
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.cninfo.com.cn/new/disclosure",
            "Origin": "https://www.cninfo.com.cn",
        }
        r = requests.post(url, data=payload, headers=headers, timeout=15)
        d = r.json()

        results = []
        for item in (d.get("announcements") or [])[:10]:
            results.append({
                "title": item.get("announcementTitle", ""),
                "time": _cninfo_ts_to_date(item.get("announcementTime")),
                "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={item.get('announcementId', '')}",
                "source": "巨潮资讯",
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_eastmoney_search(keyword, limit=10):
    """
    东财搜索API (JSONP)
    返回: [{title, date, source, url}, ...]
    """
    try:
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        params = {
            "cb": "jQuery",
            "param": json.dumps({
                "uid": "",
                "keyword": keyword,
                "type": ["cmsArticleWebOld"],
                "client": "web",
                "clientType": "web",
                "clientVersion": "curr",
                "param": {
                    "cmsArticleWebOld": {
                        "searchScope": "default",
                        "sort": "default",
                        "pageIndex": 1,
                        "pageSize": limit,
                        "preTag": "<em>",
                        "postTag": "</em>"
                    }
                }
            })
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0",
            "Referer": "https://so.eastmoney.com/"
        }
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")

        json_str = text[text.index("(") + 1:text.rindex(")")]
        data = json.loads(json_str)
        articles = data.get("result", {}).get("cmsArticleWebOld", [])

        results = []
        for a in articles[:limit]:
            title = re.sub(r"<[^>]+>", "", a.get("title", ""))
            results.append({
                "title": title,
                "date": a.get("date", "")[:10],
                "source": a.get("mediaName", ""),
                "url": a.get("url", ""),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


def filter_relevant_news(news_list, keywords):
    """按关键词过滤相关新闻"""
    relevant = []
    for news in news_list:
        if "error" in news:
            continue
        text = (news.get("title", "") + news.get("content", "") + news.get("summary", "")).lower()
        if any(kw.lower() in text for kw in keywords):
            relevant.append(news)
    return relevant


def analyze_news_sentiment(news_list):
    """简单情绪分析: 基于关键词判断利多/利空"""
    bullish_keywords = [
        "利好", "上涨", "突破", "增长", "盈利", "订单", "合作", "扩张",
        "涨停", "主力流入", "机构买入", "评级买入", "超预期", "创新高",
        "比亚迪", "机器人", "特斯拉", "华为", "政策支持"
    ]
    bearish_keywords = [
        "利空", "下跌", "亏损", "下滑", "减持", "质押", "违规", "处罚",
        "跌停", "主力出逃", "机构卖出", "评级卖出", "不及预期", "创新低",
        "退市", "ST", "风险", "警告"
    ]

    bullish_count = 0
    bearish_count = 0

    for news in news_list:
        if "error" in news:
            continue
        text = (news.get("title", "") + news.get("content", "") + news.get("summary", "")).lower()
        for kw in bullish_keywords:
            if kw.lower() in text:
                bullish_count += 1
                break
        for kw in bearish_keywords:
            if kw.lower() in text:
                bearish_count += 1
                break

    total = bullish_count + bearish_count
    if total == 0:
        sentiment = "中性"
        score = 0
    elif bullish_count > bearish_count * 1.5:
        sentiment = "偏多"
        score = bullish_count / total
    elif bearish_count > bullish_count * 1.5:
        sentiment = "偏空"
        score = -bearish_count / total
    else:
        sentiment = "中性"
        score = (bullish_count - bearish_count) / total

    return {
        "sentiment": sentiment,
        "score": round(score, 2),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "total_news": len([n for n in news_list if "error" not in n])
    }


def full_news_analysis(symbol, stock_name="", keywords=None):
    """完整消息面分析"""
    if not keywords:
        keywords = [stock_name, symbol] if stock_name else [symbol]

    # 1. 个股新闻
    stock_news = fetch_stock_news_em(symbol, limit=10)

    # 2. 东财搜索
    search_news = fetch_eastmoney_search(symbol, limit=10)

    # 3. 同花顺快讯
    ths_flash = fetch_ths_flash(limit=20)

    # 4. 巨潮公告
    cninfo_announcements = fetch_cninfo_announcements(symbol, days=30)

    # 5. 全球资讯（过滤相关）
    global_news = fetch_global_news_em(limit=100)
    relevant_global = filter_relevant_news(global_news, keywords)

    # 6. 情绪分析
    all_news = stock_news + search_news + ths_flash + cninfo_announcements + relevant_global
    sentiment = analyze_news_sentiment(all_news)

    # 7. 时间排序（最近的在前）
    dated_news = [n for n in all_news if "date" in n or "time" in n]
    dated_news.sort(key=lambda x: x.get("date", x.get("time", "")), reverse=True)

    return {
        "symbol": symbol,
        "stock_name": stock_name,
        "stock_news": stock_news,
        "search_news": search_news,
        "ths_flash": ths_flash,
        "cninfo_announcements": cninfo_announcements,
        "global_news": relevant_global,
        "sentiment": sentiment,
        "all_news_count": len(all_news),
    }


def format_news_report(analysis):
    """格式化消息面报告（终端友好）"""
    symbol = analysis["symbol"]
    name = analysis["stock_name"]
    sentiment = analysis["sentiment"]

    lines = []
    lines.append(f"== 消息面分析: {name}({symbol}) ==")
    lines.append(f"  情绪判定: {sentiment['sentiment']} (得分: {sentiment['score']})")
    lines.append(f"  利多信号: {sentiment['bullish_count']}条 | 利空信号: {sentiment['bearish_count']}条")
    lines.append(f"  总新闻数: {sentiment['total_news']}条")
    lines.append("")

    # 个股新闻
    if analysis["stock_news"] and "error" not in analysis["stock_news"][0]:
        lines.append("--- 个股新闻 ---")
        for i, news in enumerate(analysis["stock_news"][:5], 1):
            time_str = news.get("time", "")[:10]
            title = news.get("title", "")[:60]
            source = news.get("source", "")
            lines.append(f"  {i}. [{time_str}] {title}")
            lines.append(f"     来源: {source}")
        lines.append("")

    # 巨潮公告
    if analysis.get("cninfo_announcements") and "error" not in analysis["cninfo_announcements"][0]:
        lines.append("--- 公司公告 (巨潮) ---")
        for i, news in enumerate(analysis["cninfo_announcements"][:5], 1):
            time_str = news.get("time", "")[:10]
            title = news.get("title", "")[:60]
            lines.append(f"  {i}. [{time_str}] {title}")
        lines.append("")

    # 搜索新闻
    if analysis["search_news"] and "error" not in analysis["search_news"][0]:
        lines.append("--- 东财搜索 ---")
        for i, news in enumerate(analysis["search_news"][:5], 1):
            date = news.get("date", "")
            title = news.get("title", "")[:60]
            source = news.get("source", "")
            lines.append(f"  {i}. [{date}] {title}")
            lines.append(f"     来源: {source}")
        lines.append("")

    # 同花顺快讯
    if analysis.get("ths_flash") and "error" not in analysis["ths_flash"][0]:
        lines.append("--- 财经快讯 (同花顺) ---")
        for i, news in enumerate(analysis["ths_flash"][:5], 1):
            time_str = news.get("time", "")[:16]
            title = news.get("title", "")[:60]
            lines.append(f"  {i}. [{time_str}] {title}")
        lines.append("")

    # 相关全球资讯
    if analysis["global_news"]:
        lines.append("--- 相关行业/板块资讯 ---")
        for i, news in enumerate(analysis["global_news"][:5], 1):
            time_str = news.get("time", "")[:16]
            title = news.get("title", "")[:60]
            lines.append(f"  {i}. [{time_str}] {title}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 news_analysis.py <股票代码> [股票名称]")
        sys.exit(1)

    symbol = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else ""

    analysis = full_news_analysis(symbol, name)
    print(format_news_report(analysis))
