#!/usr/bin/env python3
"""
板块分析脚本 — 个股所属板块实时分析
用法: python3 sector_analysis.py <股票代码> [股票名称]

输出: 该股所属概念板块今日涨跌 + 相对强弱 + 板块趋势 + 同板块对比
供session/cron agent做市场环境分析
"""
import sys, os, json, time, urllib.request

def get_prefix(code):
    if code.startswith(('6', '9')):
        return 'sh'
    elif code.startswith('8'):
        return 'bj'
    else:
        return 'sz'

def tencent_quote(code):
    """腾讯实时行情"""
    prefix = get_prefix(code)
    url = f'https://qt.gtimg.cn/q={prefix}{code}'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode('gbk')
    vals = data.split('"')[1].split('~')
    return {
        'name': vals[1],
        'price': float(vals[3]) if vals[3] else 0,
        'change_pct': float(vals[32]) if vals[32] else 0,
    }

def get_concepts(code):
    """获取个股所属概念板块(东财)"""
    # secid格式: 0.300179(深市) 或 1.601179(沪市)
    market = '1' if code.startswith(('6', '9')) else '0'
    secid = f'{market}.{code}'
    url = f"https://push2.eastmoney.com/api/qt/slist/get?spt=3&secid={secid}&fields=f12,f13,f14,f3,f2&pn=1&pz=50&np=1&fltt=2&invt=2&ut=b2884a393a59ad64002292a3e90d46a5"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            results = []
            for item in data['data']['diff']:
                name = item.get('f14', '')
                bcode = item.get('f12', '')
                pct = item.get('f3', 0)
                pct_val = float(pct) / 100 if pct and pct != '-' else 0
                results.append({'name': name, 'code': bcode, 'change_pct': pct_val})
            return results
    except Exception:
        pass
    return []

def get_industry_stocks(concept_code, limit=5):
    """获取同板块其他标的今日表现(东财)"""
    url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit+1}&po=1&np=1&fields=f2,f3,f4,f12,f14&fid=f3&fs=b:{concept_code}&ut=b2884a393a59ad64002292a3e90d46a5"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            results = []
            for item in data['data']['diff'][:limit]:
                name = item.get('f14', '')
                code = item.get('f12', '')
                pct = item.get('f3', 0)
                pct_val = float(pct) / 100 if pct and pct != '-' else 0
                results.append({'name': name, 'code': code, 'change_pct': pct_val})
            return results
    except Exception:
        pass
    return []

def get_sector_trend(concept_code):
    """获取板块近5日走势(东财K线)"""
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=90.{concept_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20261231&lmt=5"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.eastmoney.com/'}
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        klines = data.get('data', {}).get('klines', [])
        if klines:
            closes = []
            for k in klines:
                parts = k.split(',')
                closes.append(float(parts[2]))
            if len(closes) >= 2:
                trend_pct = (closes[-1] / closes[0] - 1) * 100
                return trend_pct
    except Exception:
        pass
    return None

def analyze(code, name=None):
    """主分析函数"""
    # 1. 个股行情
    quote = tencent_quote(code)
    stock_name = name or quote['name']
    stock_chg = quote['change_pct']

    # 2. 所属概念
    concepts = get_concepts(code)
    time.sleep(0.3)

    if not concepts:
        return {
            'code': code, 'name': stock_name,
            'stock_chg': stock_chg,
            'error': '无法获取概念板块数据'
        }

    # 3. 分析每个概念板块
    sector_data = []
    for c in concepts[:5]:  # 取前5个概念
        bcode = c['code']
        bname = c['name']
        bpct = c['change_pct']

        # 个股vs板块强弱
        diff = stock_chg - bpct
        if diff > 1:
            strength = '强于板块'
        elif diff < -1:
            strength = '弱于板块'
        else:
            strength = '同步'

        # 板块近5日趋势
        time.sleep(0.3)
        trend = get_sector_trend(bcode)

        sector_data.append({
            'name': bname,
            'code': bcode,
            'change_pct': bpct,
            'strength': strength,
            'diff': round(diff, 2),
            'trend_5d': round(trend, 2) if trend is not None else None,
        })

    # 4. 同板块对比(取第一个概念板块的代表性标的)
    peers = []
    if sector_data:
        time.sleep(0.3)
        peers = get_industry_stocks(sector_data[0]['code'], limit=4)
        # 排除自身
        peers = [p for p in peers if p['code'] != code][:3]

    return {
        'code': code,
        'name': stock_name,
        'stock_chg': stock_chg,
        'concepts': sector_data,
        'peers': peers,
    }

def format_output(data):
    """格式化输出"""
    if 'error' in data:
        print(f"  ⚠️ {data['error']}")
        return

    lines = []
    lines.append(f"  所属板块:")

    # 概念板块
    for c in data['concepts']:
        trend_str = f" 近5日{c['trend_5d']:+.1f}%" if c['trend_5d'] is not None else ""
        strength_icon = {'强于板块': '🟢', '弱于板块': '🔴', '同步': '🟡'}[c['strength']]
        lines.append(f"    {c['name']}: {c['change_pct']:+.2f}% {strength_icon} {c['strength']}{trend_str}")

    # 相对强弱总结
    strong = sum(1 for c in data['concepts'] if c['strength'] == '强于板块')
    weak = sum(1 for c in data['concepts'] if c['strength'] == '弱于板块')
    sync = sum(1 for c in data['concepts'] if c['strength'] == '同步')

    if weak > strong and weak > 0:
        overall = '🔴 个股弱于多数板块(个股层面问题)'
    elif strong > weak and strong > 0:
        overall = '🟢 个股强于多数板块(有独立催化)'
    else:
        overall = '🟡 个股与板块同步(跟随板块)'
    lines.append(f"  相对强弱: {overall}")

    # 同板块对比
    if data['peers']:
        lines.append(f"  同板块对比:")
        for p in data['peers']:
            lines.append(f"    {p['name']}({p['code']}): {p['change_pct']:+.2f}%")

    return '\n'.join(lines)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 sector_analysis.py <股票代码> [股票名称]")
        sys.exit(1)

    code = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None

    data = analyze(code, name)

    # JSON输出(供agent解析)
    if '--json' in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 可读输出
        print(f"\n=== 板块分析: {data.get('name', code)}({code}) ===")
        print(f"  个股今日: {data.get('stock_chg', 0):+.2f}%")
        output = format_output(data)
        if output:
            print(output)

if __name__ == '__main__':
    main()
