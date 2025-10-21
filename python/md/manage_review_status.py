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
    python python/utils/manage_review_status.py --state draft --basket vi --book para --locale romn --locale thai
"""

import os
import re
import yaml
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


def parse_locale_args(locale_args: Optional[List[str]]) -> Optional[List[str]]:
    """แปลงค่า locale จาก arguments ให้เป็นรายการ locale"""
    if not locale_args:
        return ["romn"]  # ค่าดั้งเดิมเพื่อความเข้ากันได้ย้อนหลัง

    locales: List[str] = []
    for value in locale_args:
        parts = [part.strip() for part in value.split(',') if part.strip()]
        for part in parts:
            lowered = part.lower()
            if lowered in {"all", "*"}:
                return None  # None แทนการเลือกทั้ง src/content/docs
            locales.append(part)

    return locales if locales else None

class ReviewStatusManager:
    """จัดการสถานะการตรวจทานเอกสาร"""
    
    def __init__(self, content_dir: str = "src/content/docs"):
        self.project_root = Path(__file__).resolve().parents[2]
        self.content_dir = self._resolve_content_dir(Path(content_dir))
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

    def _resolve_content_dir(self, content_path: Path) -> Path:
        """แปลง content_dir ให้เป็น path ที่ถูกต้องเสมอ"""
        candidates = []

        if content_path.is_absolute():
            candidates.append(content_path)
        else:
            candidates.append((Path.cwd() / content_path).resolve())
            candidates.append((self.project_root / content_path).resolve())

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # ถ้ายังไม่พบ ให้ใช้ path ภายใต้ project_root เป็นค่า default
        fallback = (self.project_root / content_path).resolve()
        if not fallback.exists():
            print(f"⚠️ ไม่พบ content_dir {fallback}, ใช้ path นี้เป็นค่า default")
        return fallback
    
    def find_files(self,
                   locales: Optional[List[str]] = None,
                   basket: Optional[str] = None,
                   book: Optional[str] = None,
                   file_pattern: str = "*.mdx") -> List[Path]:
        """หาไฟล์เอกสารตามเงื่อนไข ภายใต้ src/content/docs"""
        try:
            files: List[Path] = []
            base_paths: List[Path] = []
            content_root = self.content_dir.resolve()

            if locales is None:
                base_paths = [self.content_dir]
            else:
                for locale in locales:
                    locale_stripped = locale.strip()
                    if not locale_stripped or locale_stripped.lower() == "root":
                        base_paths.append(self.content_dir)
                        continue
                    relative_path = Path(locale_stripped)
                    target_path = (self.content_dir / relative_path).resolve()
                    try:
                        common_root = os.path.commonpath([str(content_root), str(target_path)])
                    except ValueError:
                        print(f"⚠️ เส้นทาง {locale} อยู่นอก {self.content_dir}, ข้าม")
                        continue
                    if Path(common_root) != content_root:
                        print(f"⚠️ เส้นทาง {locale} อยู่นอก {self.content_dir}, ข้าม")
                        continue
                    if not target_path.exists():
                        print(f"⚠️ ไม่พบ locale/เส้นทาง: {locale}")
                        continue
                    base_paths.append(target_path)

            if not base_paths:
                default_path = self.content_dir / "romn"
                base_paths.append(default_path if default_path.exists() else self.content_dir)

            for base_path in base_paths:
                if not base_path.exists():
                    continue
                for candidate in base_path.rglob(file_pattern):
                    if not candidate.is_file():
                        continue
                    try:
                        relative_parts = candidate.relative_to(self.content_dir).parts
                    except ValueError:
                        # อยู่นอก content_dir ไม่ต้องใช้งาน
                        continue

                    # ป้องกันการเลือกนอกขอบเขต locale ที่ระบุ (เมื่อเจาะจง locale)
                    if locales is not None and base_path != self.content_dir:
                        base_parts = base_path.relative_to(self.content_dir).parts
                        if base_parts:
                            if tuple(relative_parts[:len(base_parts)]) != base_parts:
                                continue

                    parts_lower = [part.lower() for part in relative_parts]

                    if basket and basket.lower() not in parts_lower:
                        continue
                    if book and book.lower() not in parts_lower:
                        continue

                    files.append(candidate)

            # ลบรายการซ้ำโดยคงลำดับเดิม
            unique_files: List[Path] = []
            seen = set()
            for path in files:
                if path not in seen:
                    unique_files.append(path)
                    seen.add(path)

            return unique_files
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
                import_pattern = r'^(import\s+[^;]+;)$'
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
                else:
                    # ไม่มี imports เลย เพิ่มที่ด้านบนของ body
                    import_lines = "\n".join(imports_to_add) + "\n"
                    body = import_lines + body

            if components_to_add:
                lines = body.split('\n')

                # หา index สำหรับแทรกหลังจากบล็อก import/คอมเมนต์ส่วนต้น
                insert_index = None
                for idx, line in enumerate(lines):
                    stripped = line.strip()

                    # ข้ามบรรทัดว่างช่วงต้น
                    if stripped == "":
                        continue

                    # ข้ามคำสั่ง import และคอมเมนต์นำหน้า
                    if stripped.startswith('import ') or stripped.startswith('//'):
                        continue

                    insert_index = idx
                    break

                if insert_index is None:
                    insert_index = len(lines)

                insertion_block: List[str] = []

                # เว้นบรรทัดว่างก่อนบล็อกใหม่ หากยังไม่มีบรรทัดว่างคั่น
                if insert_index > 0 and lines[insert_index - 1].strip() != "":
                    insertion_block.append("")

                for component_line in components_to_add:
                    insertion_block.append(component_line)
                    insertion_block.append("")

                lines[insert_index:insert_index] = insertion_block
                body = '\n'.join(lines)
            
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

    # อัปเดตหลาย locale (romn, thai, mymr)
    python python/utils/manage_review_status.py --state draft --basket vi --book para --locale romn --locale thai --locale mymr

    # อัปเดตทุก locale ภายใต้ src/content/docs
    python python/utils/manage_review_status.py --state review --basket vi --book para --locale all
  
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
                       help="ปิฎก (vi=วินัย, su=สูตร, ab=อภิธรรม)")
    parser.add_argument("--book", 
                       help="คัมภีร์ (para, paci, maha, culla, pari, etc.)")
    parser.add_argument("--file", 
                       help="ไฟล์เฉพาะ (path จาก root)")
    parser.add_argument("--locale",
                       action="append",
                       help="เลือก locale/path ภายใต้ src/content/docs (ระบุหลายครั้งหรือคั่นด้วย comma, ใช้ all/* เพื่อเลือกทั้งหมด)")
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
    parser.add_argument("--yes",
                       action="store_true",
                       help="ยืนยันการอัปเดตโดยอัตโนมัติเพื่อข้ามคำถามยืนยัน")
    parser.add_argument("--content-dir",
                       default="src/content/docs",
                       help="โฟลเดอร์เนื้อหา (default: src/content/docs)")
    
    args = parser.parse_args()
    selected_locales = parse_locale_args(args.locale)
    
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
        files = manager.find_files(
            locales=selected_locales,
            basket=args.basket,
            book=args.book
        )
    
    if not files:
        print("❌ ไม่พบไฟล์ที่ตรงกับเงื่อนไข")
        return 1
    
    if not args.file:
        if selected_locales is None:
            print("🌐 ขอบเขต: ทุก locale ภายใต้ src/content/docs")
        elif selected_locales:
            print("🌐 Locale/เส้นทาง: " + ", ".join(selected_locales))

    print(f"📁 พบไฟล์ {len(files)} ไฟล์")
    
    # แสดงข้อมูลตาม filters
    if args.basket:
        basket_names = {"vi": "พระวินัย", "su": "พระสูตร", "ab": "อภิธรรม"}
        print(f"🗂️  ปิฎก: {basket_names.get(args.basket, args.basket)}")
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
    if len(files) > 1 and not args.yes:
        print(f"\n❓ ยืนยันการอัปเดต {len(files)} ไฟล์?")
        confirm = input("   พิมพ์ 'yes' หรือ 'y' เพื่อดำเนินการ: ").lower()
        if confirm not in ['yes', 'y']:
            print("❌ ยกเลิกการทำงาน")
            return 0
    elif args.yes:
        print("\n✅ ข้ามขั้นตอนยืนยันตามคำสั่ง --yes")
    
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