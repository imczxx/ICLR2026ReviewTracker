#!/usr/bin/env python3
"""
ICLR 2026 Submissions Merger

合并 data/raw/ 目录下的所有JSON文件，保留所有review版本
同时提供合并前后的验证信息
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict


def load_json_file(filepath: str) -> List[Dict]:
    """Load JSON file and return the data."""
    print(f"Loading {Path(filepath).name}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filepath: str, data: List[Dict]):
    """Save data to JSON file with proper formatting."""
    print(f"Saving to {filepath}...")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved successfully!")


def analyze_data(data: List[Dict], title: str) -> Dict:
    """分析数据并返回统计信息"""
    stats = {
        'total_submissions': len(data),
        'submissions_with_reviews': 0,
        'total_review_entries': 0,
        'unique_reviews': 0,
        'multi_version_count': 0,
        'version_distribution': defaultdict(int)
    }
    
    all_review_ids = set()
    
    for submission in data:
        reviews = submission.get('details', {}).get('directReplies', [])
        
        if reviews:
            stats['submissions_with_reviews'] += 1
            stats['total_review_entries'] += len(reviews)
            
            # 按review_id分组
            review_groups = defaultdict(list)
            for review in reviews:
                review_id = review.get('id')
                if review_id:
                    review_groups[review_id].append(review)
                    all_review_ids.add(review_id)
            
            # 统计版本数
            unique_reviews = len(review_groups)
            total_versions = len(reviews)
            
            if total_versions > unique_reviews:
                stats['multi_version_count'] += 1
                extra_versions = total_versions - unique_reviews
                stats['version_distribution'][extra_versions] += 1
    
    stats['unique_reviews'] = len(all_review_ids)
    
    return stats


def print_stats(stats: Dict, title: str):
    """打印统计信息"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(f"Total submissions: {stats['total_submissions']}")
    print(f"Submissions with reviews: {stats['submissions_with_reviews']}")
    print(f"Total review entries: {stats['total_review_entries']}")
    print(f"Unique reviews: {stats['unique_reviews']}")
    
    if stats['multi_version_count'] > 0:
        print(f"\nSubmissions with multi-version reviews: {stats['multi_version_count']}")
        if stats['version_distribution']:
            print("Version distribution:")
            for extra_versions in sorted(stats['version_distribution'].keys()):
                count = stats['version_distribution'][extra_versions]
                print(f"  +{extra_versions} extra version(s): {count} submissions")


def merge_reviews(all_files_data: List[tuple]) -> List[Dict]:
    """
    Merge submissions from multiple files.
    
    Args:
        all_files_data: List of tuples (date_str, submissions_list)
    
    Returns:
        Merged list of submissions with all review versions preserved
    """
    # Sort by date to ensure we process in chronological order
    # 'merged' should be treated as earliest to collect reviews, but not used as base
    all_files_data.sort(key=lambda x: (x[0] != 'merged', x[0]))
    
    # Find the latest dated file (not 'merged') as base for submission metadata
    latest_date = None
    latest_submissions = None
    for date_str, submissions in reversed(all_files_data):
        if date_str != 'merged':
            latest_date = date_str
            latest_submissions = submissions
            break
    
    if not latest_submissions:
        # Fallback to last file if no dated files found
        latest_date, latest_submissions = all_files_data[-1]
    
    print(f"\nUsing {latest_date} as base for submission metadata")
    
    # Create a mapping of submission_id -> submission for the latest file
    merged_submissions = {}
    for submission in latest_submissions:
        sub_id = submission.get('id')
        if sub_id:
            merged_submissions[sub_id] = submission.copy()
    
    print(f"Found {len(merged_submissions)} submissions in latest file")
    
    # Now collect all reviews from all files - keep ALL versions
    review_collections = {}  # submission_id -> {review_id -> [list of all versions]}
    
    for date_str, submissions in all_files_data:
        print(f"\nProcessing reviews from {date_str}...")
        reviews_found = 0
        
        for submission in submissions:
            sub_id = submission.get('id')
            if not sub_id:
                continue
            
            # Initialize review collection for this submission if needed
            if sub_id not in review_collections:
                review_collections[sub_id] = {}
            
            # Extract reviews from details.directReplies
            details = submission.get('details', {})
            direct_replies = details.get('directReplies', [])
            
            for review in direct_replies:
                review_id = review.get('id')
                if not review_id:
                    continue
                
                # Initialize list for this review if needed
                if review_id not in review_collections[sub_id]:
                    review_collections[sub_id][review_id] = []
                
                # Check if this exact version already exists
                review_version = review.get('version', 0)
                review_mdate = review.get('mdate', 0)
                
                # Check for duplicate (same version and mdate)
                is_duplicate = False
                for existing_review in review_collections[sub_id][review_id]:
                    if (existing_review.get('version', 0) == review_version and 
                        existing_review.get('mdate', 0) == review_mdate):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    review_collections[sub_id][review_id].append(review)
                    reviews_found += 1
        
        print(f"  Processed {reviews_found} review versions")
    
    # Now merge the reviews back into the submissions
    print("\nMerging reviews into submissions...")
    total_reviews = 0
    total_review_versions = 0
    
    for sub_id, submission in merged_submissions.items():
        if sub_id in review_collections:
            # Flatten all review versions into a single list
            all_review_versions = []
            for review_id, versions in review_collections[sub_id].items():
                all_review_versions.extend(versions)
            
            # Sort reviews by: 1) number (if available), 2) version, 3) mdate
            all_review_versions.sort(key=lambda r: (
                r.get('number', 0),
                r.get('version', 0),
                r.get('mdate', 0)
            ))
            
            # Update the submission's details.directReplies
            if 'details' not in submission:
                submission['details'] = {}
            
            submission['details']['directReplies'] = all_review_versions
            
            unique_review_ids = len(review_collections[sub_id])
            total_versions = len(all_review_versions)
            total_reviews += unique_review_ids
            total_review_versions += total_versions
    
    print(f"\nTotal unique reviews: {total_reviews}")
    print(f"Total review versions: {total_review_versions}")
    
    # Convert back to list and sort by submission number
    result = list(merged_submissions.values())
    result.sort(key=lambda s: s.get('number', 0))
    
    return result


def main():
    """Main function to merge ICLR 2026 submission files."""
    print("=" * 70)
    print("ICLR 2026 Submissions Merger")
    print("=" * 70)
    
    # Define directories
    base_dir = Path(__file__).parent
    raw_dir = base_dir / 'data' / 'raw'
    data_dir = base_dir / 'data'
    output_file = data_dir / 'iclr2026_submissions_merged.json'
    
    # Ensure directories exist
    raw_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files in data/raw directory
    print(f"\nScanning {raw_dir} for JSON files...")
    json_files = sorted(raw_dir.glob('iclr2026_submissions_*.json'))
    
    if not json_files:
        print(f"❌ Error: No JSON files found in {raw_dir}")
        print("Please run crawl.py first to fetch data.")
        return
    
    print(f"Found {len(json_files)} JSON files:")
    for f in json_files:
        print(f"  - {f.name}")
    
    # Check if merged file already exists and analyze it
    existing_data = None
    if output_file.exists():
        print(f"\n⚠️  Found existing merged file: {output_file.name}")
        print("Analyzing existing data...")
        existing_data = load_json_file(str(output_file))
        existing_stats = analyze_data(existing_data, "📊 Before Merge")
        print_stats(existing_stats, "📊 Before Merge")
    else:
        print("\n✨ No existing merged file found. Creating new merge...")
    
    # Load all files
    all_files_data = []
    
    # Add existing merged data first if it exists
    if existing_data:
        all_files_data.append(('merged', existing_data))
    
    # Load all JSON files from raw directory
    for filepath in json_files:
        # Extract timestamp from filename
        filename = filepath.stem  # e.g., iclr2026_submissions_20251117_085900
        timestamp = filename.replace('iclr2026_submissions_', '')
        
        data = load_json_file(str(filepath))
        all_files_data.append((timestamp, data))
    
    if not all_files_data:
        print("❌ Error: No data loaded!")
        return
    
    # Merge the data
    print("\n" + "=" * 70)
    print("🔄 Starting Merge Process")
    print("=" * 70)
    merged_data = merge_reviews(all_files_data)
    
    # Analyze merged data
    merged_stats = analyze_data(merged_data, "📊 After Merge")
    
    # Save the merged data
    print("\n" + "=" * 70)
    print("💾 Saving Merged Data")
    print("=" * 70)
    save_json_file(str(output_file), merged_data)
    
    # Print final statistics
    print_stats(merged_stats, "📊 After Merge")
    
    # Print comparison if we had existing data
    if existing_data:
        print("\n" + "=" * 70)
        print("📈 Comparison")
        print("=" * 70)
        print(f"Review entries: {existing_stats['total_review_entries']} → {merged_stats['total_review_entries']} "
              f"(+{merged_stats['total_review_entries'] - existing_stats['total_review_entries']})")
        print(f"Unique reviews: {existing_stats['unique_reviews']} → {merged_stats['unique_reviews']} "
              f"(+{merged_stats['unique_reviews'] - existing_stats['unique_reviews']})")
        print(f"Multi-version submissions: {existing_stats['multi_version_count']} → {merged_stats['multi_version_count']} "
              f"(+{merged_stats['multi_version_count'] - existing_stats['multi_version_count']})")
    
    print("\n" + "=" * 70)
    print("✅ Merge Completed Successfully!")
    print("=" * 70)
    print(f"Output file: {output_file}")
    print(f"Total submissions: {len(merged_data)}")
    print(f"Merged from {len(json_files)} raw files")
    print("=" * 70)


if __name__ == '__main__':
    main()
