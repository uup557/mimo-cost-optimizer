#!/usr/bin/env python3
"""
MiMo 真实用量监控 - 从Hermes数据库读取真实token数据
"""
import os
import sys
import sqlite3
from datetime import datetime, date, timedelta

DB_PATH = os.path.expanduser("~/.hermes/state.db")

def get_report(days=7):
    """获取真实用量报告"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    today_start = datetime.combine(date.today(), datetime.min.time()).timestamp()
    
    # 全局汇总
    cursor.execute('''
        SELECT 
            SUM(input_tokens) as new_input,
            SUM(cache_read_tokens) as cached,
            SUM(output_tokens) as output,
            SUM(api_call_count) as calls,
            COUNT(*) as sessions
        FROM sessions
        WHERE started_at >= ?
    ''', (datetime.strptime(since, '%Y-%m-%d').timestamp(),))
    t = cursor.fetchone()
    
    new_input = t[0] or 0
    cached = t[1] or 0
    output = t[2] or 0
    calls = t[3] or 0
    sessions = t[4] or 0
    total_prompt = new_input + cached
    actual_billing = new_input + output
    cache_rate = (cached / total_prompt * 100) if total_prompt > 0 else 0
    
    # 今日
    cursor.execute('''
        SELECT 
            SUM(input_tokens), SUM(cache_read_tokens), SUM(output_tokens),
            SUM(api_call_count), COUNT(*)
        FROM sessions WHERE started_at >= ?
    ''', (today_start,))
    td = cursor.fetchone()
    td_new = td[0] or 0
    td_cached = td[1] or 0
    td_output = td[2] or 0
    td_calls = td[3] or 0
    td_sessions = td[4] or 0
    td_total = td_new + td_cached
    td_actual = td_new + td_output
    td_cache_rate = (td_cached / td_total * 100) if td_total > 0 else 0
    
    # 每日明细
    daily = []
    for i in range(days-1, -1, -1):
        d = date.today() - timedelta(days=i)
        day_start = datetime.combine(d, datetime.min.time()).timestamp()
        day_end = datetime.combine(d + timedelta(days=1), datetime.min.time()).timestamp()
        cursor.execute('''
            SELECT SUM(input_tokens), SUM(cache_read_tokens), SUM(output_tokens), SUM(api_call_count)
            FROM sessions WHERE started_at >= ? AND started_at < ?
        ''', (day_start, day_end))
        row = cursor.fetchone()
        if row and row[0] is not None:
            di = row[0] or 0
            dc = row[1] or 0
            do = row[2] or 0
            dt = di + dc
            actual = di + do
            cr = (dc/dt*100) if dt > 0 else 0
            daily.append((d, row[3] or 0, di, dc, do, actual, cr))
        else:
            daily.append((d, 0, 0, 0, 0, 0, 0))
    
    # 按来源
    cursor.execute('''
        SELECT source, SUM(input_tokens), SUM(cache_read_tokens), 
               SUM(output_tokens), COUNT(*)
        FROM sessions WHERE started_at >= ? AND input_tokens > 0
        GROUP BY source ORDER BY SUM(input_tokens) + SUM(cache_read_tokens) DESC
    ''', (datetime.strptime(since, '%Y-%m-%d').timestamp(),))
    by_source = cursor.fetchall()
    
    conn.close()
    
    return {
        'period_days': days,
        'since': since,
        'total': {'new_input': new_input, 'cached': cached, 'output': output, 
                  'calls': calls, 'sessions': sessions, 'total_prompt': total_prompt,
                  'actual': actual_billing, 'cache_rate': cache_rate},
        'today': {'new_input': td_new, 'cached': td_cached, 'output': td_output,
                  'calls': td_calls, 'sessions': td_sessions, 'total': td_total,
                  'actual': td_actual, 'cache_rate': td_cache_rate},
        'daily': daily,
        'by_source': by_source
    }

def print_report(r):
    """打印报告"""
    t = r['total']
    td = r['today']
    
    print(f"\n{'='*55}")
    print(f"🔥 MiMo 真实用量报告")
    print(f"{'='*55}")
    print(f"📅 统计周期: {r['since']} ~ 今天 ({r['period_days']}天)")
    
    print(f"\n📊 期间汇总")
    print(f"  Sessions:     {t['sessions']}")
    print(f"  API调用:      {t['calls']:,}")
    print(f"  总Prompt:     {t['total_prompt']:,} tokens")
    print(f"  ├ 新Input:    {t['new_input']:,}")
    print(f"  └ 缓存命中:   {t['cached']:,} ({t['cache_rate']:.1f}%)")
    print(f"  Output:       {t['output']:,}")
    print(f"  ─────────────────────────────")
    print(f"  💰 实际计费:  {t['actual']:,} tokens")
    print(f"  🎉 缓存节省:  {t['cached']:,} tokens")
    
    print(f"\n📅 今日({date.today()})")
    print(f"  Sessions: {td['sessions']}, 调用: {td['calls']}")
    print(f"  新Input: {td['new_input']:,}  缓存: {td['cached']:,} ({td['cache_rate']:.1f}%)  Output: {td['output']:,}")
    print(f"  💰 实际计费: {td['actual']:,} tokens")
    
    if r['daily']:
        print(f"\n📈 每日明细:")
        for d, calls, new_in, cached, output, actual, cr in r['daily']:
            if calls > 0:
                print(f"  {d}: {calls:>3}次 | 计费={actual:>9,}  缓存={cached:>10,} ({cr:.0f}%)  新in={new_in:>8,}")
            else:
                print(f"  {d}: 无数据")
    
    if r['by_source']:
        print(f"\n🏷️ 按来源:")
        for src, ni, ca, out, cnt in r['by_source']:
            billing = ni + out
            print(f"  {str(src or '?'):12}: {cnt:>3} sessions | 计费={billing:>10,}  总prompt={ni+ca:>10,}")
    
    print(f"\n{'='*55}")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    r = get_report(days)
    print_report(r)