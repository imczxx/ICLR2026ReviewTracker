#!/usr/bin/env python3
"""
ICLR 2026 Submissions Crawler

从OpenReview API抓取ICLR 2026的所有submissions和reviews
保存到 data/raw/ 目录，文件名包含精确到秒的时间戳
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

BASE = "https://api2.openreview.net"
INVITATION = "ICLR.cc/2026/Conference/-/Submission"

def crawl_submissions():
    """抓取所有submissions"""
    print("=" * 70)
    print("ICLR 2026 Submissions Crawler")
    print("=" * 70)
    
    all_notes = []
    limit = 1000
    offset = 0
    
    print(f"\nStarting to fetch submissions from OpenReview API...")
    print(f"Base URL: {BASE}")
    print(f"Invitation: {INVITATION}\n")
    
    while True:
        url = f"{BASE}/notes?invitation={INVITATION}&details=directReplies&limit={limit}&offset={offset}"
        print(f"Fetching offset {offset}...")
        
        try:
            resp = requests.get(url).json()
            notes = resp.get("notes", [])
            
            if not notes:
                print(f"\nDone! Total submissions fetched: {len(all_notes)}")
                break
            
            all_notes.extend(notes)
            offset += limit
            time.sleep(0.2)  # 避免请求过快
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
            continue
    
    return all_notes


def save_to_file(data):
    """保存数据到文件，使用精确到秒的时间戳"""
    # 确保目录存在
    data_dir = Path(__file__).parent / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成时间戳（精确到秒）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"iclr2026_submissions_{timestamp}.json"
    filepath = data_dir / filename
    
    print(f"\nSaving to {filepath}...")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved successfully!")
    print(f"   File: {filepath}")
    print(f"   Size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")
    
    return filepath


def main():
    """主函数"""
    start_time = time.time()
    
    # 抓取数据
    submissions = crawl_submissions()
    
    # 保存数据
    filepath = save_to_file(submissions)
    
    # 统计信息
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("Crawl Summary")
    print("=" * 70)
    print(f"Total submissions: {len(submissions)}")
    print(f"Output file: {filepath}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print("=" * 70)


if __name__ == "__main__":
    main()
