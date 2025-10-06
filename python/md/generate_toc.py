#!/usr/bin/env python3
"""
สคริปต์สำหรับสร้างสารบัญ (Table of Contents) สำหรับไฟล์ Tipitaka
อ่านไฟล์ markdown จาก python/md/tipitaka และสร้างสารบัญแบบลำดับชั้น
ผลลัพธ์จะเป็น bullet points พร้อมชื่อหัวข้อเท่านั้น

การใช้งาน:
    python generate_toc.py [book_code] [--all]
    
ตัวอย่าง:
    python generate_toc.py 1V          # สร้าง TOC สำหรับเล่ม 1V เท่านั้น
    python generate_toc.py --all       # สร้าง TOC สำหรับทุกเล่ม
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

try:
    from aksharamukha import transliterate
    TRANSLITERATION_AVAILABLE = True
except ImportError:
    TRANSLITERATION_AVAILABLE = False
    print("Warning: aksharamukha not available. Transliteration features disabled.")
    print("To enable transliteration, install: pip install aksharamukha")


def activate_venv():
    """Activate virtual environment if available"""
    # Get current working directory
    current_dir = Path.cwd()
    
    # Check if we're in the right directory structure
    if not (current_dir / "python" / "md" / "tipitaka").exists():
        # Try to navigate to the project root
        project_root = current_dir
        while project_root.parent != project_root:  # Not at filesystem root
            if (project_root / "python" / "md" / "tipitaka").exists():
                os.chdir(project_root)
                break
            project_root = project_root.parent
        else:
            print("Warning: Could not find project root with python/md/tipitaka structure")
    
    # Look for virtual environment activation script
    venv_scripts = [
        Path(".venv/Scripts/activate"),  # Windows
        Path(".venv/bin/activate"),      # Unix/Linux/macOS
        Path("venv/Scripts/activate"),   # Windows alternative
        Path("venv/bin/activate"),       # Unix alternative
    ]
    
    for venv_script in venv_scripts:
        if venv_script.exists():
            print(f"Found virtual environment: {venv_script}")
            # Note: We can't actually activate venv from within Python
            # But we can check if we're already in one
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                print("Virtual environment is already active")
            else:
                print(f"Please activate virtual environment first: source {venv_script}")
            break
    else:
        print("No virtual environment found - continuing without activation")


class TipitakaTOCGenerator:
    def __init__(self, tipitaka_dir: str = "tipitaka", output_dir: str = "toc", locale: str = "romn"):
        self.tipitaka_dir = Path(tipitaka_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.locale = locale
        
        # Transliteration configuration
        self.transliteration_config = {
            'romn': {'from': 'IASTPali', 'to': 'IASTPali'},  # No conversion needed
            'mymr': {'from': 'IASTPali', 'to': 'Burmese'},   
            'thai': {'from': 'IASTPali', 'to': 'Thai'},
            'sinh': {'from': 'IASTPali', 'to': 'Sinhala'},
            'deva': {'from': 'IASTPali', 'to': 'Devanagari'},
            'khmr': {'from': 'IASTPali', 'to': 'Khmer'},
            'laoo': {'from': 'IASTPali', 'to': 'LaoPali'},
            'lana': {'from': 'IASTPali', 'to': 'TaiTham'}
        }
        
        # Cache for transliteration results
        self._transliteration_cache = {}
        
        # Pattern สำหรับตรวจสอบรายการ TOC ในไฟล์
        self.toc_pattern = re.compile(r'^\s*\*\s+\[([^\]]+)\]\(([^)]+)\)\s*$')
        
        # Pattern สำหรับ breadcrumb navigation
        self.breadcrumb_pattern = re.compile(r'^\[.*?\]\(.*?\)')
        
        # Book mappings จาก migrate_tipitaka.py (ตัดแต่งเฉพาะที่จำเป็น)
        self.book_mappings = {
            # Vinayapiṭaka (vi)
            '1V': {'abbrev': 'para', 'name': 'Pārājikapāḷi'},
            '2V': {'abbrev': 'paci', 'name': 'Pācittiyapāḷi'},
            '3V': {'abbrev': 'vi-maha', 'name': 'Mahāvaggapāḷi'},
            '4V': {'abbrev': 'cula', 'name': 'Cūḷavaggapāḷi'},
            '5V': {'abbrev': 'pari', 'name': 'Parivārapāḷi'},
            
            # Dīghanikāya (dn)
            '6D': {'abbrev': 'sila', 'name': 'Sīlakkhandhavaggapāḷi'},
            '7D': {'abbrev': 'dn-maha', 'name': 'Mahāvaggapāḷi'},
            '8D': {'abbrev': 'pthi', 'name': 'Pāthikavaggapāḷi'},
            
            # Majjhimanikāya (mn)
            '9M': {'abbrev': 'mula', 'name': 'Mūlapaṇṇāsapāḷi'},
            '10M': {'abbrev': 'majj', 'name': 'Majjhimapaṇṇāsapāḷi'},
            '11M': {'abbrev': 'upar', 'name': 'Uparipaṇṇāsapāḷi'},
            
            # Saṃyuttanikāya (sn)
            '12S1': {'abbrev': 'saga', 'name': 'Sagāthāvaggasaṃyuttapāḷi'},
            '12S2': {'abbrev': 'nida', 'name': 'Nidānavaggasaṃyuttapāḷi'},
            '13S3': {'abbrev': 'khan', 'name': 'Khandhavaggasaṃyuttapāḷi'},
            '13S4': {'abbrev': 'sala', 'name': 'Saḷāyatanavaggasaṃyuttapāḷi'},
            '14S5': {'abbrev': 'sn-maha', 'name': 'Mahāvaggasaṃyuttapāḷi'},
            
            # Aṅguttaranikāya (an)
            '15A1': {'abbrev': 'a1', 'name': 'Ekakanipātapāḷi'},
            '15A2': {'abbrev': 'a2', 'name': 'Dukanipātapāḷi'},
            '15A3': {'abbrev': 'a3', 'name': 'Tikanipātapāḷi'},
            '15A4': {'abbrev': 'a4', 'name': 'Catukkanipātapāḷi'},
            '16A5': {'abbrev': 'a5', 'name': 'Pañcakanipātapāḷi'},
            '16A6': {'abbrev': 'a6', 'name': 'Chakkanipātapāḷi'},
            '16A7': {'abbrev': 'a7', 'name': 'Sattakanipātapāḷi'},
            '17A8': {'abbrev': 'a8', 'name': 'Aṭṭhakanipātapāḷi'},
            '17A9': {'abbrev': 'a9', 'name': 'Navakanipātapāḷi'},
            '17A10': {'abbrev': 'a10', 'name': 'Dasakanipātapāḷi'},
            '17A11': {'abbrev': 'a11', 'name': 'Ekādasakanipātapāḷi'},
            
            # Khuddakanikāya (kn)
            '18Kh': {'abbrev': 'kh', 'name': 'Khuddakapāṭhapāḷi'},
            '18Dh': {'abbrev': 'dh', 'name': 'Dhammapadapāḷi'},
            '18Ud': {'abbrev': 'ud', 'name': 'Udānapāḷi'},
            '18It': {'abbrev': 'it', 'name': 'Itivuttakapāḷi'},
            '18Sn': {'abbrev': 'sn', 'name': 'Suttanipātapāḷi'},
            '19Vv': {'abbrev': 'vv', 'name': 'Vimānavatthupāḷi'},
            '19Pv': {'abbrev': 'pv', 'name': 'Petavatthupāḷi'},
            '19Th1': {'abbrev': 'th1', 'name': 'Theragāthāpāḷi'},
            '19Th2': {'abbrev': 'th2', 'name': 'Therīgāthāpāḷi'},
            '20Ap1': {'abbrev': 'ap1', 'name': 'Therāpadānapāḷi'},
            '20Ap2': {'abbrev': 'ap2', 'name': 'Therīapadānapāḷi'},
            '21Bu': {'abbrev': 'bu', 'name': 'Buddhavaṃsapāḷi'},
            '21Cp': {'abbrev': 'cp', 'name': 'Cariyāpiṭakapāḷi'},
            '22J': {'abbrev': 'ja1', 'name': 'Jātakapāḷi 1'},
            '23J': {'abbrev': 'ja2', 'name': 'Jātakapāḷi 2'},
            '24Mn': {'abbrev': 'mn', 'name': 'Mahāniddesapāḷi'},
            '25Cn': {'abbrev': 'cn', 'name': 'Cūḷaniddesapāḷi'},
            '26Ps': {'abbrev': 'ps', 'name': 'Paṭisambhidāmaggapāḷi'},
            '27Ne': {'abbrev': 'ne', 'name': 'Nettipāḷi'},
            '27Pe': {'abbrev': 'pe', 'name': 'Peṭakopadesapāḷi'},
            '28Mi': {'abbrev': 'mi', 'name': 'Milindapañhapāḷi'},
            
            # Abhidhammapiṭaka (ab)
            '29Dhs': {'abbrev': 'dhs', 'name': 'Dhammasaṅgaṇīpāḷi'},
            '30Vbh': {'abbrev': 'vbh', 'name': 'Vibhaṅgapāḷi'},
            '31Dht': {'abbrev': 'dht', 'name': 'Dhātukathāpāḷi'},
            '31Pu': {'abbrev': 'pu', 'name': 'Puggalapaññattipāḷi'},
            '32Kv': {'abbrev': 'kv', 'name': 'Kathāvatthupāḷi'},
            
            # Yamaka (ab/yk)
            '33Y1': {'abbrev': 'y1', 'name': 'Mūlayamakapāḷi'},
            '33Y2': {'abbrev': 'y2', 'name': 'Khandhayamakapāḷi'},
            '33Y3': {'abbrev': 'y3', 'name': 'Āyatanayamakapāḷi'},
            '33Y4': {'abbrev': 'y4', 'name': 'Dhātuyamakapāḷi'},
            '33Y5': {'abbrev': 'y5', 'name': 'Saccayamakapāḷi'},
            '34Y6': {'abbrev': 'y6', 'name': 'Saṅkhārayamakapāḷi'},
            '34Y7': {'abbrev': 'y7', 'name': 'Anusayayamakapāḷi'},
            '34Y8': {'abbrev': 'y8', 'name': 'Cittayamakapāḷi'},
            '35Y9': {'abbrev': 'y9', 'name': 'Dhammayamakapāḷi'},
            '35Y10': {'abbrev': 'y10', 'name': 'Indriyayamakapāḷi'},
            
            # Paṭṭhāna (ab/pt) - Dhammānuloma
            '36P1': {'abbrev': 'p1-1', 'name': 'Tikapaṭṭhānapāḷi 1'},
            '37P1': {'abbrev': 'p1-2', 'name': 'Tikapaṭṭhānapāḷi 2'},
            '38P2': {'abbrev': 'p2', 'name': 'Dukapaṭṭhānapāḷi'},
            '39P3': {'abbrev': 'p3', 'name': 'Dukatikapaṭṭhānapāḷi'},
            '39P4': {'abbrev': 'p4', 'name': 'Tikadukapaṭṭhānapāḷi'},
            '39P5': {'abbrev': 'p5', 'name': 'Tikatikapaṭṭhānapāḷi'},
            '39P6': {'abbrev': 'p6', 'name': 'Dukadukapaṭṭhānapāḷi'},
            
            # Paṭṭhāna - Dhammapaccanīya
            '40P7': {'abbrev': 'p7', 'name': 'Tikapaṭṭhānapāḷi'},
            '40P8': {'abbrev': 'p8', 'name': 'Dukapaṭṭhānapāḷi'},
            '40P9': {'abbrev': 'p9', 'name': 'Dukatikapaṭṭhānapāḷi'},
            '40P10': {'abbrev': 'p10', 'name': 'Tikadukapaṭṭhānapāḷi'},
            '40P11': {'abbrev': 'p11', 'name': 'Tikatikapaṭṭhānapāḷi'},
            '40P12': {'abbrev': 'p12', 'name': 'Dukadukapaṭṭhānapāḷi'},
            
            # Paṭṭhāna - Dhammānulomapaccanīya
            '40P13': {'abbrev': 'p13', 'name': 'Tikapaṭṭhānapāḷi'},
            '40P14': {'abbrev': 'p14', 'name': 'Dukapaṭṭhānapāḷi'},
            '40P15': {'abbrev': 'p15', 'name': 'Dukatikapaṭṭhānapāḷi'},
            '40P16': {'abbrev': 'p16', 'name': 'Tikadukapaṭṭhānapāḷi'},
            '40P17': {'abbrev': 'p17', 'name': 'Tikatikapaṭṭhānapāḷi'},
            '40P18': {'abbrev': 'p18', 'name': 'Dukadukapaṭṭhānapāḷi'},
            
            # Paṭṭhāna - Dhammapaccanīyānuloma
            '40P19': {'abbrev': 'p19', 'name': 'Tikapaṭṭhānapāḷi'},
            '40P20': {'abbrev': 'p20', 'name': 'Dukapaṭṭhānapāḷi'},
            '40P21': {'abbrev': 'p21', 'name': 'Dukatikapaṭṭhānapāḷi'},
            '40P22': {'abbrev': 'p22', 'name': 'Tikadukapaṭṭhānapāḷi'},
            '40P23': {'abbrev': 'p23', 'name': 'Tikatikapaṭṭhānapāḷi'},
            '40P24': {'abbrev': 'p24', 'name': 'Dukadukapaṭṭhānapāḷi'},
        }
    
    def convert_text_with_transliteration(self, text: str) -> str:
        """Convert text using aksharamukha transliteration with caching"""
        if self.locale == 'romn' or not TRANSLITERATION_AVAILABLE:
            return text  # No conversion needed for roman
        
        # Check cache first
        cache_key = (text, self.locale)
        if cache_key in self._transliteration_cache:
            return self._transliteration_cache[cache_key]
        
        config = self.transliteration_config.get(self.locale)
        if not config:
            return text  # Return unchanged if locale not supported
        
        try:
            # Protect markdown links and numbers from transliteration
            import re
            
            # Split text into segments, preserving numbers and symbols
            segments = re.split(r'(\d+|[^\w\u0100-\u017F\u1E00-\u1EFF]+)', text)
            result_segments = []
            
            for segment in segments:
                if re.match(r'^\d+$|^[^\w\u0100-\u017F\u1E00-\u1EFF]+$', segment):
                    # Keep numbers and non-Pali characters as is
                    result_segments.append(segment)
                elif segment.strip():
                    # Transliterate only non-empty Pali word segments
                    try:
                        converted = transliterate.process(config['from'], config['to'], segment)
                        result_segments.append(converted)
                    except Exception as e:
                        # On error, keep original segment
                        print(f"Warning: Transliteration failed for '{segment}': {e}")
                        result_segments.append(segment)
                else:
                    result_segments.append(segment)
            
            result = ''.join(result_segments)
            
            # Cache the result
            self._transliteration_cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"Warning: Transliteration failed for locale {self.locale}: {e}")
            return text  # Return original on error
    
    def activate_venv(self):
        """เปิดใช้งาน virtual environment"""
        venv_script = Path(".venv/Scripts/Activate.ps1")  # Windows PowerShell
        venv_script_bat = Path(".venv/Scripts/activate.bat")  # Windows batch
        venv_script_unix = Path(".venv/bin/activate")  # Unix/Linux
        
        print("กำลังเปิดใช้งาน virtual environment...")
        
        try:
            if os.name == 'nt':  # Windows
                if venv_script.exists():
                    # PowerShell activation
                    result = subprocess.run(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(venv_script)],
                        capture_output=True, text=True, cwd=Path.cwd()
                    )
                elif venv_script_bat.exists():
                    # Batch activation
                    result = subprocess.run([str(venv_script_bat)], shell=True, capture_output=True, text=True)
                else:
                    print("ไม่พบ virtual environment script")
                    return False
            else:
                # Unix/Linux
                if venv_script_unix.exists():
                    result = subprocess.run([f"source {venv_script_unix}"], shell=True, capture_output=True, text=True)
                else:
                    print("ไม่พบ virtual environment script")
                    return False
            
            print("เปิดใช้งาน virtual environment สำเร็จ")
            return True
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการเปิดใช้งาน venv: {e}")
            return False
    
    def extract_toc_titles_only(self, file_path: Path) -> List[str]:
        """
        สกัดเฉพาะชื่อหัวข้อจากรายการ TOC
        Returns: List of title strings only
        """
        titles = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # ข้าม breadcrumb lines
                if self.breadcrumb_pattern.match(line) and ('/' in line or '[Home]' in line):
                    continue
                
                # หา TOC entries แล้วเก็บเฉพาะชื่อ
                match = self.toc_pattern.match(line)
                if match:
                    title = match.group(1).strip()
                    # Apply transliteration if needed
                    if self.locale != 'romn':
                        title = self.convert_text_with_transliteration(title)
                    titles.append(title)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
        
        return titles
    
    def build_correct_hierarchy(self, book_dir: Path) -> List[Tuple[str, int]]:
        """
        สร้าง hierarchy ที่ถูกต้องตามโครงสร้างที่ต้องการ
        โครงสร้าง: 1 Mahāvibhaṅga (0) -> Verañjakaṇḍa (1) / 1.1-1.4 (1) -> 1.1.1-1.4.3 (2) -> 1.1.1.1-1.4.3.10 (3)
        """
        results = []
        
        # อ่านหัวข้อหลักจาก 0.md (เฉพาะหัวข้อ ไม่เอารายการ TOC)
        main_title_file = book_dir / '0.md'
        if main_title_file.exists():
            try:
                with open(main_title_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # หาหัวข้อหลักเท่านั้น
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if title_match:
                    main_title = title_match.group(1).strip()
                    # Apply transliteration if needed
                    if self.locale != 'romn':
                        main_title = self.convert_text_with_transliteration(main_title)
                    results.append((main_title, 0))  # Level 0
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการอ่านไฟล์หลัก {main_title_file}: {e}")

        # หาไฟล์ sutta ทั้งหมด (1.md, 2.md, 3.md, ...)
        # ข้าม 0.md เพราะเราเอาแค่หัวข้อหลักแล้ว
        main_files = []
        for item in book_dir.iterdir():
            if item.is_file() and item.suffix == '.md' and item.stem.isdigit() and item.stem != '0':
                main_files.append(item)
        
        # เรียงตามตัวเลข
        main_files.sort(key=lambda f: int(f.stem))
        
        if not main_files:
            print(f"ไม่พบไฟล์หลักสำหรับ {book_dir}")
            return results
            
        # ประมวลผลแต่ละไฟล์หลัก
        for main_file in main_files:
            try:
                # หา title หลักจากไฟล์หลัก 
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if title_match:
                    main_title = title_match.group(1).strip()
                    # Apply transliteration if needed
                    if self.locale != 'romn':
                        main_title = self.convert_text_with_transliteration(main_title)
                    results.append((main_title, 0))  # Level 0
                
                # หา TOC links ในไฟล์หลัก
                lines = content.split('\n')
                toc_links = []
                
                for line in lines:
                    line = line.strip()
                    if self.breadcrumb_pattern.match(line) and ('/' in line or '[Home]' in line):
                        continue
                        
                    match = self.toc_pattern.match(line)
                    if match:
                        title = match.group(1).strip()
                        link_path = match.group(2).strip()
                        toc_links.append((title, link_path))
                
                # ประมวลผลแต่ละ TOC link
                for title, link_path in toc_links:
                    # Apply transliteration if needed
                    if self.locale != 'romn':
                        title = self.convert_text_with_transliteration(title)
                    results.append((title, 1))  # Level 1
                    
                    # ตามลิงก์ไปไฟล์ย่อย
                    if link_path and not link_path.startswith('http'):
                        link_full_path = main_file.parent / link_path
                        if link_full_path.exists():
                            sub_hierarchy = self._process_sub_file(link_full_path, 2)
                            results.extend(sub_hierarchy)
                            
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการอ่านไฟล์ {main_file}: {e}")
        return results
    
    def _process_sub_file(self, file_path: Path, level: int) -> List[Tuple[str, int]]:
        """
        ประมวลผลไฟล์ย่อยและ sub-directories
        """
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # หา TOC links ในไฟล์นี้
            for line in lines:
                line = line.strip()
                if self.breadcrumb_pattern.match(line) and ('/' in line or '[Home]' in line):
                    continue
                    
                match = self.toc_pattern.match(line)
                if match:
                    title = match.group(1).strip()
                    link_path = match.group(2).strip()
                    
                    # Apply transliteration if needed
                    if self.locale != 'romn':
                        title = self.convert_text_with_transliteration(title)
                    
                    results.append((title, level))  # ระดับปัจจุบัน
                    
                    # ตามลิงก์ไปไฟล์ลึกขึ้น
                    if link_path and not link_path.startswith('http'):
                        link_full_path = file_path.parent / link_path
                        if link_full_path.exists():
                            deeper_results = self._process_sub_file(link_full_path, level + 1)
                            results.extend(deeper_results)
                            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการอ่านไฟล์ {file_path}: {e}")
            
        return results
    
    def collect_all_titles_recursive(self, current_dir: Path, level: int = 0) -> List[Tuple[str, int]]:
        """
        รวบรวมชื่อหัวข้อทั้งหมดแบบ recursive โดยใช้โครงสร้าง hierarchy ที่ถูกต้อง
        Returns: List of (title, level) tuples
        """
        return self.build_correct_hierarchy(current_dir)
    
    def create_toc_markdown(self, book_code: str, all_titles: List[Tuple[str, int]]) -> str:
        """สร้าง markdown content สำหรับ TOC"""
        
        book_info = self.book_mappings.get(book_code, {})
        book_name = book_info.get('name', book_code)
        
        # Apply transliteration to book name if needed
        if self.locale != 'romn':
            book_name = self.convert_text_with_transliteration(book_name)
        
        # Frontmatter
        markdown_lines = [
            "---",
            f'title = "สารบัญ {book_code}"',
            f'description = "สารบัญ {book_code}"',
            "---",
            "",
            f"## {book_name}",
            ""
        ]
        
        # สร้างรายการ bullet points
        # ข้ามหัวข้อ level 0 แรกเพราะมันคือชื่อหนังสือที่แสดงใน ## {book_name} แล้ว
        first_level_0_skipped = False
        for title, level in all_titles:
            if level == 0:
                if not first_level_0_skipped:
                    # ข้ามหัวข้อ level 0 แรกที่เป็นชื่อหนังสือ
                    first_level_0_skipped = True
                    continue
                # หัวข้อ level 0 อื่นๆ (เช่น sutta) ยังคงเป็น level 0 ใน markdown
            
            indent = "  " * level  # ใช้ level ตรงๆ ไม่ปรับ
            markdown_lines.append(f"{indent}- {title}")
        
        return "\n".join(markdown_lines)
    
    def generate_book_toc(self, book_code: str) -> bool:
        """สร้าง TOC สำหรับเล่มหนึ่งเล่ม"""
        print(f"กำลังสร้าง TOC สำหรับ {book_code}...")
        
        # ตรวจสอบ book mapping
        if book_code not in self.book_mappings:
            print(f"ไม่พบ {book_code} ใน book mappings")
            return False
        
        book_info = self.book_mappings[book_code]
        abbrev = book_info['abbrev']
        
        # ตรวจสอบว่ามีไฟล์และ directory
        main_file = self.tipitaka_dir / f"{book_code}.md"
        book_dir = self.tipitaka_dir / book_code
        
        if not main_file.exists() and not book_dir.exists():
            print(f"ไม่พบไฟล์หรือโฟลเดอร์สำหรับ {book_code}")
            return False
        
        all_titles = []
        
        # ประมวลผลจาก directory (ซึ่งจะใช้ hierarchy ที่ถูกต้อง)
        if book_dir.exists():
            all_titles = self.collect_all_titles_recursive(book_dir, 0)
        elif main_file.exists():
            # fallback หากมีแต่ไฟล์เดียว
            main_titles = self.extract_toc_titles_only(main_file)
            for title in main_titles:
                all_titles.append((title, 0))
        
        if not all_titles:
            print(f"ไม่พบหัวข้อใดสำหรับ {book_code}")
            return False
        
        # สร้างเนื้อหา markdown
        markdown_content = self.create_toc_markdown(book_code, all_titles)
        
        # บันทึกไฟล์ตาม abbrev
        output_file = self.output_dir / f"{abbrev}-toc.md"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"สร้าง TOC สำเร็จ: {output_file}")
            print(f"จำนวนหัวข้อ: {len(all_titles)} รายการ")
            return True
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการบันทึก {output_file}: {e}")
            return False
    
    def get_available_books(self) -> List[str]:
        """รับรายชื่อเล่มทั้งหมดที่มีอยู่"""
        books = []
        
        if not self.tipitaka_dir.exists():
            return books
        
        # หาเล่มที่มีอยู่จริงในระบบ
        for book_code in self.book_mappings.keys():
            main_file = self.tipitaka_dir / f"{book_code}.md"
            book_dir = self.tipitaka_dir / book_code
            
            if main_file.exists() or book_dir.exists():
                books.append(book_code)
        
        # เรียงตามลำดับ
        def sort_key(book_code):
            # แยกตัวเลขออกจากตัวอักษร
            match = re.match(r'(\d+)([A-Z].*)$', book_code)
            if match:
                return (int(match.group(1)), match.group(2))
            return (999, book_code)
        
        books.sort(key=sort_key)
        return books
    
    def generate_all_tocs(self) -> Dict[str, bool]:
        """สร้าง TOC สำหรับทุกเล่ม"""
        books = self.get_available_books()
        results = {}
        
        if not books:
            print("ไม่พบเล่มใดที่สามารถประมวลผลได้")
            return results
        
        print(f"พบ {len(books)} เล่ม: {', '.join(books)}")
        print("=" * 50)
        
        success_count = 0
        for book_code in books:
            success = self.generate_book_toc(book_code)
            results[book_code] = success
            if success:
                success_count += 1
            print()
        
        print("=" * 50)
        print(f"สรุปผลการดำเนินงาน: {success_count}/{len(books)} เล่ม")
        
        # แสดงรายละเอียดผลลัพธ์
        failed_books = [book for book, success in results.items() if not success]
        if failed_books:
            print(f"เล่มที่ไม่สำเร็จ: {', '.join(failed_books)}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='สร้างสารบัญ (TOC) สำหรับไฟล์ Tipitaka')
    parser.add_argument('book_code', nargs='?', help='รหัสเล่มที่ต้องการสร้าง TOC (เช่น 1V, 10M)')
    parser.add_argument('--all', action='store_true', help='สร้าง TOC สำหรับทุกเล่ม')
    parser.add_argument('--tipitaka-dir', default='./tipitaka', 
                       help='ตำแหน่งโฟลเดอร์ tipitaka (default: ./tipitaka)')
    parser.add_argument('--output-dir', default='./toc',
                       help='ตำแหน่งโฟลเดอร์สำหรับบันทึกผลลัพธ์ (default: ./toc)')
    parser.add_argument('--locale', '-l', default='romn', 
                       choices=['romn', 'thai', 'mymr', 'sinh', 'deva', 'khmr', 'laoo', 'lana'],
                       help='ภาษาสำหรับปริวรรตอักษร (default: romn - โรมันดั้งเดิม)')
    
    args = parser.parse_args()
    
    # ตรวจสอบ transliteration support
    if args.locale != 'romn' and not TRANSLITERATION_AVAILABLE:
        print("Error: การปริวรรตอักษรไม่พร้อมใช้งาน")
        print("กรุณาติดตั้ง: pip install aksharamukha")
        sys.exit(1)
    
    # สร้าง generator
    generator = TipitakaTOCGenerator(args.tipitaka_dir, args.output_dir, args.locale)
    
    # เปิดใช้งาน venv ก่อนทำงาน
    if not generator.activate_venv():
        print("เตือน: ไม่สามารถเปิดใช้งาน virtual environment ได้")
        print("กำลังดำเนินการต่อโดยไม่ใช้ venv...")
    
    print()
    
    if args.all:
        # สร้าง TOC ทุกเล่ม
        generator.generate_all_tocs()
    elif args.book_code:
        # สร้าง TOC เล่มเดียว
        generator.generate_book_toc(args.book_code)
    else:
        # แสดงรายการเล่มที่มี
        books = generator.get_available_books()
        if books:
            print("รายการเล่มที่มีอยู่:")
            for i, book in enumerate(books, 1):
                book_info = generator.book_mappings[book]
                print(f"  {i:2d}. {book} ({book_info['abbrev']}) - {book_info['name']}")
            print(f"\nใช้คำสั่ง: python {os.path.basename(__file__)} <book_code> หรือ --all")
        else:
            print(f"ไม่พบเล่มใดในโฟลเดอร์ {args.tipitaka_dir}")


if __name__ == '__main__':
    main()