#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Review Status Management Script for TPTK Project
จัดการสถานะการตรวจทานเอกสารพระไตรปิฎก

Requirements:
- Python 3.7+
- PyYAML (pip install PyYAML)
- Run in virtual environment: .venv\Scripts\activate

Usage:
    python python/utils/manage_review_status.py --state draft --updated-by "admin"
    python python/utils/manage_review_status.py --state review --basket vi --updated-by "reviewer1"
"""

import os
import re
import yaml
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

class ReviewStatusManager:
    """จัดการสถานะการตรวจทานเอกสาร"""
    
    def __init__(self, content_dir: str = "src/content/docs"):
        self.content_dir = Path(content_dir)
        self.valid_states = ["draft", "review", "revision", "approved", "published"]
        
        # ตรวจสอบว่าอยู่ใน virtual environment หรือไม่
        if not self._check_venv():
            print("⚠️ แนะนำให้รันใน virtual environment")
            print("   รัน: .venv\\Scripts\\activate (Windows) หรือ source .venv/bin/activate (Linux/Mac)")
            
    def _check_venv(self) -> bool:
        """ตรวจสอบว่าอยู่ใน virtual environment หรือไม่"""
        return (hasattr(sys, 'real_prefix') or 
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
                'VIRTUAL_ENV' in os.environ)
    
    def find_files(self, 
                   basket: Optional[str] = None, 
                   book: Optional[str] = None,
                   file_pattern: str = "*.mdx") -> List[Path]:
        """หาไฟล์เอกสารตามเงื่อนไข"""
        try:
            if basket and book:
                # เฉพาะคัมภีร์ เช่น vi/para
                search_path = self.content_dir / "romn" / "tipitaka" / basket / book
            elif basket:
                # เฉพาะพิธีก เช่น vi (vinaya)  
                search_path = self.content_dir / "romn" / "tipitaka" / basket
            else:
                # ทั้งหมด
                search_path = self.content_dir / "romn" / "tipitaka"
            
            if search_path.exists():
                return list(search_path.rglob(file_pattern))
            return []
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการค้นหาไฟล์: {e}")
            return []
    
    def parse_frontmatter(self, content: str) -> tuple:
        """แยก frontmatter จากเนื้อหา"""
        try:
            pattern = r'^---\n(.*?)\n---\n(.*)$'
            match = re.match(pattern, content, re.DOTALL)
            
            if match:
                frontmatter_str = match.group(1)
                body = match.group(2)
                
                # Parse YAML
                frontmatter_data = yaml.safe_load(frontmatter_str)
                if frontmatter_data is None:
                    frontmatter_data = {}
                
                return frontmatter_data, body
            
            return {}, content
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในการ parse frontmatter: {e}")
            return {}, content
    
    def get_current_state(self, file_path: Path) -> str:
        """ดึงสถานะปัจจุบันจากไฟล์"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter, _ = self.parse_frontmatter(content)
            
            if 'review' in frontmatter and 'current' in frontmatter['review']:
                return frontmatter['review']['current']
            
            return "draft"  # default state
        except Exception as e:
            print(f"❌ ไม่สามารถอ่านสถานะจาก {file_path}: {e}")
            return "draft"
    
    def create_review_data(self, 
                          new_state: str,
                          previous_state: str,
                          updated_by: str = "",
                          notes: str = "",
                          existing_history: List[Dict] = None) -> Dict[str, Any]:
        """สร้างข้อมูล review object - ไม่จำกัดจำนวน history"""
        timestamp = datetime.now().isoformat()
        
        # เตรียม history entry ใหม่
        new_history_entry = {
            "state": new_state,
            "date": timestamp,
            "updated_by": updated_by,
            "notes": notes,
            "previous_state": previous_state if previous_state != new_state else None
        }
        
        # รวม history เดิมกับรายการใหม่ (ไม่จำกัดจำนวน)
        history = existing_history or []
        history.insert(0, new_history_entry)  # ใส่รายการใหม่ที่ด้านบน
        
        return {
            "current": new_state,
            "updated": timestamp,
            "updated_by": updated_by,
            "notes": notes,
            "history": history
        }
    
    def update_review_status(self, 
                           file_path: Path,
                           new_state: str,
                           updated_by: str = "",
                           notes: str = "") -> bool:
        """อัปเดตสถานะในไฟล์ - รองรับการข้ามขั้นตอน"""
        if new_state not in self.valid_states:
            print(f"❌ สถานะไม่ถูกต้อง: {new_state}")
            print(f"   ใช้ได้เฉพาะ: {', '.join(self.valid_states)}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter_data, body = self.parse_frontmatter(content)
            
            # ดึงสถานะเดิม
            previous_state = "draft"
            existing_history = []
            
            if 'review' in frontmatter_data:
                previous_state = frontmatter_data['review'].get('current', 'draft')
                existing_history = frontmatter_data['review'].get('history', [])
            
            # ถ้าสถานะเดิมกับใหม่เหมือนกัน ให้แจ้งเตือน
            if previous_state == new_state and not notes:
                print(f"⚠️  สถานะเดิมกับใหม่เหมือนกัน ({new_state}) ใน {file_path.name}")
                return True  # ถือว่าสำเร็จแต่ไม่ต้องทำอะไร
            
            # สร้างข้อมูล review ใหม่
            frontmatter_data['review'] = self.create_review_data(
                new_state, previous_state, updated_by, notes, existing_history
            )
            
            # เพิ่ม imports ที่จำเป็นหากยังไม่มี
            imports_to_add = []
            components_to_add = []
            
            # ตรวจสอบ ReviewStatus import และ component  
            if "import ReviewStatus" not in body and "<ReviewStatus" not in body:
                imports_to_add.append("import ReviewStatus from '@components/ReviewStatus.astro';")
                components_to_add.append("<ReviewStatus review={frontmatter.review} showDetails={true} />")
            
            # ตรวจสอบ HypothesisAnnotation import และ component
            if "import HypothesisAnnotation" not in body and "<HypothesisAnnotation" not in body:
                imports_to_add.append("import HypothesisAnnotation from '@components/HypothesisAnnotation.astro';")
                components_to_add.append("<HypothesisAnnotation frontmatter={frontmatter} />")
            
            # เพิ่ม imports หากมี
            if imports_to_add:
                # หาตำแหน่ง imports
                import_pattern = r'^(import.*?;)$'
                existing_imports = re.findall(import_pattern, body, re.MULTILINE)
                
                if existing_imports:
                    # เพิ่มหลังจาก import อื่นๆ
                    last_import = existing_imports[-1]
                    new_imports = "\n" + "\n".join(imports_to_add)
                    body = body.replace(
                        last_import,
                        last_import + new_imports,
                        1
                    )
                    
                    # เพิ่ม components หลังจาก imports และ components อื่นๆ
                    if components_to_add:
                        lines = body.split('\n')
                        insert_pos = 0
                        
                        # หาตำแหน่งหลังจาก DynamicBreadcrumb หรือหลัง imports
                        for i, line in enumerate(lines):
                            if '<DynamicBreadcrumb' in line:
                                insert_pos = i + 2  # หลังจาก DynamicBreadcrumb และบรรทัดว่าง
                                break
                            elif line.strip() == '' and i > 0 and not lines[i-1].strip().startswith('import'):
                                insert_pos = i
                                break
                        
                        if insert_pos > 0:
                            # เพิ่ม components ทีละตัว
                            for j, component_line in enumerate(components_to_add):
                                lines.insert(insert_pos + j * 2, "")
                                lines.insert(insert_pos + j * 2 + 1, component_line)
                            
                            lines.insert(insert_pos + len(components_to_add) * 2, "")
                            body = '\n'.join(lines)
                else:
                    # ไม่มี imports เลย เพิ่มที่ด้านบน
                    import_lines = "\n".join(imports_to_add) + "\n" if imports_to_add else ""
                    component_lines = "\n" + "\n".join(components_to_add) + "\n\n" if components_to_add else ""
                    body = import_lines + component_lines + body
            
            # สร้าง frontmatter ใหม่
            frontmatter_yaml = yaml.dump(
                frontmatter_data, 
                default_flow_style=False, 
                allow_unicode=True,
                sort_keys=False,
                width=float('inf')  # ป้องกัน line wrapping
            )
            
            # รวมเนื้อหาใหม่
            new_content = f"---\n{frontmatter_yaml}---\n{body}"
            
            # เขียนกลับไฟล์
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            print(f"❌ ข้อผิดพลาดในไฟล์ {file_path}: {e}")
            return False
    
    def batch_update(self, 
                     files: List[Path],
                     new_state: str,
                     updated_by: str = "",
                     notes: str = "") -> Dict[str, Any]:
        """อัปเดตสถานะหลายไฟล์"""
        results = {
            "success": 0, 
            "failed": 0, 
            "skipped": 0,
            "files": [],
            "errors": []
        }
        
        for file_path in files:
            try:
                relative_path = file_path.relative_to(Path.cwd())
                print(f"🔄 กำลังอัปเดต: {relative_path}")
            except ValueError:
                # ถ้า relative path ไม่ได้ ให้ใช้ชื่อไฟล์แทน
                print(f"🔄 กำลังอัปเดต: {file_path}")
            
            try:
                if self.update_review_status(file_path, new_state, updated_by, notes):
                    results["success"] += 1
                    results["files"].append(str(file_path))
                    print(f"✅ สำเร็จ: {file_path.name}")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"ล้มเหลว: {file_path}")
                    print(f"❌ ล้มเหลว: {file_path.name}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"ข้อผิดพลาด {file_path}: {e}")
                print(f"❌ ข้อผิดพลาด {file_path.name}: {e}")
        
        return results
    
    def show_status_summary(self, files: List[Path]) -> None:
        """แสดงสรุปสถานะของไฟล์ต่างๆ"""
        status_count = {}
        
        print("\n📊 สรุปสถานะปัจจุบัน:")
        
        for file_path in files:
            current_state = self.get_current_state(file_path)
            status_count[current_state] = status_count.get(current_state, 0) + 1
        
        # แสดงตามลำดับ workflow
        state_order = ["draft", "review", "revision", "approved", "published"]
        for state in state_order:
            if state in status_count:
                count = status_count[state]
                icon = {
                    "draft": "📝", "review": "👁️", "revision": "✏️", 
                    "approved": "✅", "published": "🌐"
                }
                print(f"   {icon.get(state, '📄')} {state}: {count} ไฟล์")
        
        # แสดงสถานะอื่นๆ ถ้ามี
        for state, count in status_count.items():
            if state not in state_order:
                print(f"   📄 {state}: {count} ไฟล์")
        
        print(f"   📋 รวม: {len(files)} ไฟล์")
        
        # แสดงเปอร์เซ็นต์
        if len(files) > 0:
            for state in state_order:
                if state in status_count:
                    percentage = (status_count[state] / len(files)) * 100
                    print(f"        {state}: {percentage:.1f}%")

def main():
    parser = argparse.ArgumentParser(
        description="จัดการสถานะการตรวจทานเอกสารพระไตรปิฎก",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:
  # อัปเดตทุกไฟล์เป็น draft
  python python/utils/manage_review_status.py --state draft --updated-by "admin"
  
  # อัปเดตเฉพาะพระวินัย
  python python/utils/manage_review_status.py --state review --basket vi --updated-by "reviewer1"
  
  # อัปเดตเฉพาะปาราชิก
  python python/utils/manage_review_status.py --state approved --basket vi --book para --updated-by "validator"
  
  # อัปเดตไฟล์เดียว
  python python/utils/manage_review_status.py --state published --file "src/content/docs/romn/tipitaka/vi/para/1.mdx"
  
  # ดูสถานะปัจจุบัน
  python python/utils/manage_review_status.py --show-status --basket vi
  
  # ทดสอบก่อนอัปเดต
  python python/utils/manage_review_status.py --state review --basket vi --dry-run
  
  # ข้ามขั้นตอน - เปลี่ยนจาก draft ไป approved ได้
  python python/utils/manage_review_status.py --state approved --file "path/to/file.mdx" --updated-by "validator"
        """
    )
    
    parser.add_argument("--state", 
                       choices=["draft", "review", "revision", "approved", "published"],
                       help="สถานะใหม่ที่ต้องการอัปเดต")
    parser.add_argument("--basket", 
                       help="พิธีก (vi=วินัย, su=สูตร, ab=อภิธรรม)")
    parser.add_argument("--book", 
                       help="คัมภีร์ (para, paci, maha, culla, pari, etc.)")
    parser.add_argument("--file", 
                       help="ไฟล์เฉพาะ (path จาก root)")
    parser.add_argument("--updated-by", 
                       default="", 
                       help="ชื่อผู้อัปเดต")
    parser.add_argument("--notes", 
                       default="", 
                       help="หมายเหตุเพิ่มเติม")
    parser.add_argument("--dry-run", 
                       action="store_true", 
                       help="แสดงผลโดยไม่เปลี่ยนแปลงไฟล์")
    parser.add_argument("--show-status", 
                       action="store_true", 
                       help="แสดงสถานะปัจจุบันเท่านั้น")
    parser.add_argument("--content-dir",
                       default="src/content/docs",
                       help="โฟลเดอร์เนื้อหา (default: src/content/docs)")
    
    args = parser.parse_args()
    
    # ตรวจสอบ arguments
    if not args.show_status and not args.state:
        parser.error("ต้องระบุ --state หรือ --show-status")
    
    print("🚀 Review Status Manager for TPTK Project")
    print("   สคริปต์จัดการสถานะการตรวจทานเอกสารพระไตรปิฎก")
    print()
    
    manager = ReviewStatusManager(args.content_dir)
    
    # หาไฟล์ที่ต้องทำงาน
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        files = [file_path]
        if not files[0].exists():
            print(f"❌ ไม่พบไฟล์: {args.file}")
            return 1
    else:
        files = manager.find_files(args.basket, args.book)
    
    if not files:
        print("❌ ไม่พบไฟล์ที่ตรงกับเงื่อนไข")
        return 1
    
    print(f"📁 พบไฟล์ {len(files)} ไฟล์")
    
    # แสดงข้อมูลตาม filters
    if args.basket:
        basket_names = {"vi": "พระวินัย", "su": "พระสูตร", "ab": "อภิธรรม"}
        print(f"🗂️  พิธีก: {basket_names.get(args.basket, args.basket)}")
    if args.book:
        print(f"📖 คัมภีร์: {args.book}")
    
    # แสดงสถานะปัจจุบัน
    if args.show_status:
        manager.show_status_summary(files)
        return 0
    
    print(f"🎯 สถานะใหม่: {args.state}")
    if args.updated_by:
        print(f"👤 ผู้อัปเดต: {args.updated_by}")
    if args.notes:
        print(f"📝 หมายเหตุ: {args.notes}")
    
    # โหมดทดสอบ
    if args.dry_run:
        print("\n🔍 โหมดทดสอบ - ไม่มีการเปลี่ยนแปลงไฟล์")
        for file_path in files[:10]:  # แสดงแค่ 10 ไฟล์แรก
            current_state = manager.get_current_state(file_path)
            print(f"  📄 {file_path.name}: {current_state} → {args.state}")
        
        if len(files) > 10:
            print(f"  ... และอีก {len(files) - 10} ไฟล์")
        return 0
    
    # ยืนยันการทำงาน
    if len(files) > 1:
        print(f"\n❓ ยืนยันการอัปเดต {len(files)} ไฟล์?")
        confirm = input("   พิมพ์ 'yes' หรือ 'y' เพื่อดำเนินการ: ").lower()
        if confirm not in ['yes', 'y']:
            print("❌ ยกเลิกการทำงาน")
            return 0
    
    # อัปเดตไฟล์
    print("\n🚀 เริ่มการอัปเดต...")
    results = manager.batch_update(
        files, 
        args.state, 
        args.updated_by, 
        args.notes
    )
    
    # แสดงผลสรุป
    print(f"\n📊 สรุปผลการทำงาน:")
    print(f"✅ สำเร็จ: {results['success']} ไฟล์")
    if results['failed'] > 0:
        print(f"❌ ล้มเหลว: {results['failed']} ไฟล์")
    if results['skipped'] > 0:
        print(f"⏭️  ข้าม: {results['skipped']} ไฟล์")
    
    # แสดงข้อผิดพลาด
    if results['errors']:
        print(f"\n❌ ข้อผิดพลาด:")
        for error in results['errors'][:5]:  # แสดงแค่ 5 รายการแรก
            print(f"   {error}")
        
        if len(results['errors']) > 5:
            print(f"   ... และอีก {len(results['errors']) - 5} รายการ")
    
    print("\n🎉 การทำงานเสร็จสิ้น!")
    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    exit(main())