#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สคริปต์สำหรับสแกนและนับจำนวนหน้าในแต่ละเล่มของ Tipitaka
สร้างไฟล์ page-counts.json เพื่อใช้ในการโหลดหน้าเว็บอย่างรวดเร็ว
"""

import os
import json
import glob
from pathlib import Path


def scan_tipitaka_pages(base_path: str) -> dict:
    """
    สแกนโฟลเดอร์ tipitaka และนับจำนวนหน้าในแต่ละเล่มแต่ละฉบับ
    
    Args:
        base_path: path ไปยังโฟลเดอร์ public/tipitaka
        
    Returns:
        dict: ข้อมูลจำนวนหน้าแบบ {"edition": {"volume": page_count}}
    """
    result = {}
    
    # รายการฉบับที่รองรับ
    editions = ['tr']
    
    for edition in editions:
        print(f"\n📖 สแกนฉบับ {edition.upper()}...")
        result[edition] = {}
        
        edition_path = Path(base_path) / edition
        if not edition_path.exists():
            print(f"   ⚠️  ไม่พบโฟลเดอร์ {edition_path}")
            continue
            
        # หาเล่มทั้งหมด (โฟลเดอร์ที่เป็นตัวเลข)
        volumes = []
        for item in edition_path.iterdir():
            if item.is_dir() and item.name.isdigit():
                volumes.append(int(item.name))
        
        volumes.sort()
        print(f"   พบ {len(volumes)} เล่ม: {volumes}")
        
        # นับหน้าในแต่ละเล่ม
        for volume_num in volumes:
            volume_path = edition_path / str(volume_num)
            
            # หาไฟล์รูป (.png, .jpg, .jpeg)
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg']:
                image_files.extend(glob.glob(str(volume_path / ext)))
            
            # กรองเฉพาะไฟล์ที่ชื่อเป็นตัวเลข
            page_numbers = []
            for file_path in image_files:
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                try:
                    page_num = int(name_without_ext)
                    page_numbers.append(page_num)
                except ValueError:
                    continue  # ข้ามไฟล์ที่ชื่อไม่ใช่ตัวเลข
            
            if page_numbers:
                max_page = max(page_numbers)
                result[edition][str(volume_num)] = max_page
                print(f"   เล่ม {volume_num:2d}: {max_page:3d} หน้า")
            else:
                print(f"   เล่ม {volume_num:2d}: ไม่พบหน้า")
                
    return result


def generate_page_counts_file():
    """สร้างไฟล์ page-counts.json"""
    
    # หา path ไปยังโฟลเดอร์ tipitaka
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # ย้อนกลับไปที่ root ของโปรเจกต์
    tipitaka_path = project_root / "public" / "tipitaka"
    
    print(f"🔍 ค้นหาไฟล์ใน: {tipitaka_path}")
    
    if not tipitaka_path.exists():
        print(f"❌ ไม่พบโฟลเดอร์ {tipitaka_path}")
        return
    
    # สแกนและนับหน้า
    page_counts = scan_tipitaka_pages(str(tipitaka_path))
    
    # สร้างไฟล์ JSON
    output_file = tipitaka_path / "page-counts.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(page_counts, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ สร้างไฟล์ {output_file} เรียบร้อยแล้ว")
    
    # แสดงสรุปข้อมูล
    print("\n📊 สรุปข้อมูล:")
    for edition, volumes in page_counts.items():
        total_pages = sum(volumes.values())
        print(f"   {edition.upper()}: {len(volumes)} เล่ม, รวม {total_pages:,} หน้า")
    
    return output_file


def main():
    """ฟังก์ชันหลัก"""
    print("🚀 เริ่มสแกนและสร้างไฟล์ page-counts.json")
    print("=" * 50)
    
    try:
        output_file = generate_page_counts_file()
        
        if output_file and output_file.exists():
            print(f"\n🎉 สำเร็จ! ไฟล์ถูกสร้างที่: {output_file}")
            print("\n💡 ไฟล์นี้จะถูกใช้โดยหน้าเว็บเพื่อโหลดข้อมูลอย่างรวดเร็ว")
        else:
            print("\n❌ เกิดข้อผิดพลาดในการสร้างไฟล์")
            
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")


if __name__ == "__main__":
    main()