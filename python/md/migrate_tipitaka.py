#!/usr/bin/env python3
"""
Tipitaka Content Migration Script
Migrates content from md/tipitaka to Starlight content structure
Based on cmd.txt requirements
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from aksharamukha import transliterate

class TipitakaMigrator:
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.locales = ['romn', 'mymr', 'thai', 'sinh', 'deva', 'khmr', 'laoo', 'lana']
        
        # Transliteration configuration mapping - matches build_tree.py
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
        
        # Mapping from cmd.txt - book codes to directory abbreviations
        self.book_mappings = {
            # Vinayapiṭaka
            '1V': {'abbrev': 'paraj', 'name': 'Pārājikapāḷi'},
            '2V': {'abbrev': 'pacit', 'name': 'Pācittiyapāḷi'},
            '3V': {'abbrev': 'maha-vi', 'name': 'Mahāvaggapāḷi'},
            '4V': {'abbrev': 'cula-vi', 'name': 'Cūḷavaggapāḷi'},
            '5V': {'abbrev': 'pariv', 'name': 'Parivārapāḷi'},
            
            # Dīghanikāya
            '6D': {'abbrev': 'sila', 'name': 'Sīlakkhandhavaggapāḷi'},
            '7D': {'abbrev': 'maha-di', 'name': 'Mahāvaggapāḷi'},
            '8D': {'abbrev': 'pathika', 'name': 'Pāthikavaggapāḷi'},
            
            # Majjhimanikāya
            '9M': {'abbrev': 'mula', 'name': 'Mūlapaṇṇāsapāḷi'},
            '10M': {'abbrev': 'majjh', 'name': 'Majjhimapaṇṇāsapāḷi'},
            '11M': {'abbrev': 'upari', 'name': 'Uparipaṇṇāsapāḷi'},
            
            # Saṃyuttanikāya
            '12S1': {'abbrev': 'saga', 'name': 'Sagāthāvaggasaṃyuttapāḷi'},
            '12S2': {'abbrev': 'nidana', 'name': 'Nidānavaggasaṃyuttapāḷi'},
            '13S3': {'abbrev': 'khandha', 'name': 'Khandhavaggasaṃyuttapāḷi'},
            '13S4': {'abbrev': 'salaya', 'name': 'Saḷāyatanavaggasaṃyuttapāḷi'},
            '14S5': {'abbrev': 'maha-sa', 'name': 'Mahāvaggasaṃyuttapāḷi'},
            
            # Aṅguttaranikāya
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
            
            # Khuddakanikāya
            '18Kh': {'abbrev': 'kh', 'name': 'Khuddakapāṭhapāḷi'},
            '18Dh': {'abbrev': 'dh', 'name': 'Dhammapadapāḷi'},
            '18Ud': {'abbrev': 'ud', 'name': 'Udānapāḷi'},
            '18It': {'abbrev': 'it', 'name': 'Itivuttakapāḷi'},
            '18Sn': {'abbrev': 'sn', 'name': 'Suttanipātapāḷi'},
            '19Vv': {'abbrev': 'vv', 'name': 'Vimānavatthupāḷi'},
            '19Pv': {'abbrev': 'pv', 'name': 'Petavatthupāḷi'},
            '19Th1': {'abbrev': 'thera', 'name': 'Theragāthāpāḷi'},
            '19Th2': {'abbrev': 'theri', 'name': 'Therīgāthāpāḷi'},
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
            
            # Abhidhammapiṭaka
            '29Dhs': {'abbrev': 'dhs', 'name': 'Dhammasaṅgaṇīpāḷi'},
            '30Vbh': {'abbrev': 'vbh', 'name': 'Vibhaṅgapāḷi'},
            '31Dht': {'abbrev': 'dht', 'name': 'Dhātukathāpāḷi'},
            '31Pu': {'abbrev': 'pu', 'name': 'Puggalapaññattipāḷi'},
            '32Kv': {'abbrev': 'kv', 'name': 'Kathāvatthupāḷi'},
            
            # Yamaka
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
            
            # Paṭṭhāna - Dhammānuloma
            '36P1': {'abbrev': 'p1', 'name': 'Tikapaṭṭhānapāḷi'},
            '37P1': {'abbrev': 'p1', 'name': 'Tikapaṭṭhānapāḷi'},
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
        
        # Hierarchical structure mapping
        self.structure = {
            'tipitaka': {
                'v': {  # Vinayapiṭaka
                    'books': ['1V', '2V', '3V', '4V', '5V']
                },
                'sutta': {  # Suttantapiṭaka
                    'd': {  # Dīghanikāya
                        'books': ['6D', '7D', '8D']
                    },
                    'm': {  # Majjhimanikāya
                        'books': ['9M', '10M', '11M']
                    },
                    's': {  # Saṃyuttanikāya
                        'books': ['12S1', '12S2', '13S3', '13S4', '14S5']
                    },
                    'a': {  # Aṅguttaranikāya
                        'books': ['15A1', '15A2', '15A3', '15A4', '16A5', '16A6', '16A7', '17A8', '17A9', '17A10', '17A11']
                    },
                    'khu': {  # Khuddakanikāya
                        'books': ['18Kh', '18Dh', '18Ud', '18It', '18Sn', '19Vv', '19Pv', '19Th1', '19Th2', 
                                 '20Ap1', '20Ap2', '21Bu', '21Cp', '22J', '23J', '24Mn', '25Cn', '26Ps', '27Ne', '27Pe', '28Mi']
                    }
                },
                'abhi': {  # Abhidhammapiṭaka
                    'books': ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv'],
                    'y': {  # Yamaka
                        'books': ['33Y1', '33Y2', '33Y3', '33Y4', '33Y5', '34Y6', '34Y7', '34Y8', '35Y9', '35Y10']
                    },
                    'p': {  # Paṭṭhāna
                        'anu': {  # Dhammānuloma
                            'books': ['36P1', '37P1', '38P2', '39P3', '39P4', '39P5', '39P6']
                        },
                        'pac': {  # Dhammapaccanīya
                            'books': ['40P7', '40P8', '40P9', '40P10', '40P11', '40P12']
                        },
                        'anupac': {  # Dhammānulomapaccanīya
                            'books': ['40P13', '40P14', '40P15', '40P16', '40P17', '40P18']
                        },
                        'pacanu': {  # Dhammapaccanīyānuloma
                            'books': ['40P19', '40P20', '40P21', '40P22', '40P23', '40P24']
                        }
                    }
                }
            }
        }
        
        self.sidebar_data = {}
    
    def convert_text_with_aksharamukha(self, text: str, locale: str) -> str:
        """Convert text using aksharamukha transliteration, preserving numbers and symbols"""
        if locale == 'romn':
            return text  # No conversion needed for roman (source text is already in roman)
        
        config = self.transliteration_config.get(locale)
        if not config:
            return text
        
        try:
            # Split text into segments, preserving numbers and symbols
            import re
            
            # For non-roman text, apply transliteration only to Pali text segments
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
                    except:
                        # If transliteration fails for this segment, keep original
                        result_segments.append(segment)
                else:
                    result_segments.append(segment)
            
            return ''.join(result_segments)
        except Exception as e:
            # Silently return original text if transliteration fails completely
            return text
        
    def clean_content(self, content: str, book_code: str = '') -> str:
        """Remove breadcrumb navigation, go to previous/next links, and fix internal links."""
        lines = content.split('\n')
        cleaned_lines = []
        
        # Pattern to find markdown links like [text](link)
        link_pattern = re.compile(r'(\[.*?\]\()(.+?)(\))')

        for line in lines:
            # Skip breadcrumb lines (contains [Home](/) pattern)
            if '[Home](/)' in line:
                continue
            # Skip navigation lines (Go to previous/next page)
            if line.startswith('[Go to '):
                continue

            def fix_link(match):
                pre, link, post = match.groups()
                # Remove book_code prefix
                if book_code:
                    link = link.replace(f'{book_code}/', '')
                # For internal links, remove .md extension, convert to lowercase, and replace dots with dashes
                if not link.startswith('http'):
                    link = link.removesuffix('.md').lower().replace('.', '-')
                return f"{pre}{link}{post}"

            line = link_pattern.sub(fix_link, line)

            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def create_frontmatter(self, title: str, sidebar_order: int) -> str:
        """Create Astro Starlight frontmatter"""
        return f"""---
title: "{title}"
sidebar:
  order: {sidebar_order}
---

"""
    
    def extract_title_from_content(self, content: str) -> str:
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"
    
    def get_target_path(self, book_code: str, relative_path: str, locale: str = 'romn') -> Path:
        """Generate target path based on hierarchical structure"""
        if book_code not in self.book_mappings:
            return None
            
        book_abbrev = self.book_mappings[book_code]['abbrev']
        
        # Determine the hierarchical path
        base_path = self.target_dir / locale
        
        # Find the book in the structure and build path
        if book_code.endswith('V'):  # Vinayapiṭaka
            target_path = base_path / 'tipitaka' / 'v' / book_abbrev
        elif book_code.endswith('D'):  # Dīghanikāya
            target_path = base_path / 'tipitaka' / 'sutta' / 'd' / book_abbrev
        elif book_code.endswith('M'):  # Majjhimanikāya
            target_path = base_path / 'tipitaka' / 'sutta' / 'm' / book_abbrev
        elif book_code.startswith(('12S', '13S', '14S')):  # Saṃyuttanikāya
            target_path = base_path / 'tipitaka' / 'sutta' / 's' / book_abbrev
        elif book_code.startswith(('15A', '16A', '17A')):  # Aṅguttaranikāya
            target_path = base_path / 'tipitaka' / 'sutta' / 'a' / book_abbrev
        elif book_code.startswith(('18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28')):  # Khuddakanikāya
            target_path = base_path / 'tipitaka' / 'sutta' / 'khu' / book_abbrev
        elif book_code in ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv']:  # Abhidhammapiṭaka direct
            target_path = base_path / 'tipitaka' / 'abhi' / book_abbrev
        elif book_code.startswith(('33Y', '34Y', '35Y')):  # Yamaka
            target_path = base_path / 'tipitaka' / 'abhi' / 'y' / book_abbrev
        elif book_code.startswith('36P') or book_code.startswith('37P') or book_code.startswith('38P') or book_code.startswith('39P'):  # Paṭṭhāna - Dhammānuloma
            target_path = base_path / 'tipitaka' / 'abhi' / 'p' / 'anu' / book_abbrev
        elif book_code.startswith('40P') and int(book_code[3:]) <= 12:  # Paṭṭhāna - Dhammapaccanīya
            target_path = base_path / 'tipitaka' / 'abhi' / 'p' / 'pac' / book_abbrev
        elif book_code.startswith('40P') and 13 <= int(book_code[3:]) <= 18:  # Paṭṭhāna - Dhammānulomapaccanīya
            target_path = base_path / 'tipitaka' / 'abhi' / 'p' / 'anupac' / book_abbrev
        elif book_code.startswith('40P') and int(book_code[3:]) >= 19:  # Paṭṭhāna - Dhammapaccanīyānuloma
            target_path = base_path / 'tipitaka' / 'abhi' / 'p' / 'pacanu' / book_abbrev
        else:
            return None
            
        # Add the relative path
        if relative_path and relative_path != '.':
            target_path = target_path / relative_path
            
        return target_path
    
    def migrate_file(self, source_file: Path, book_code: str, relative_path: str = '', locale: str = 'romn', sidebar_order: int = 1):
        """Migrate a single file"""
        if not source_file.exists():
            return
            
        # Read source content
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {source_file}: {e}")
            return
            
        # Clean content
        cleaned_content = self.clean_content(content, book_code)
        if not cleaned_content.strip():
            return
            
        # Extract title
        title = self.extract_title_from_content(cleaned_content)
        if title == "Untitled" and source_file.stem != source_file.name:
            title = source_file.stem
        
        # For main book files (index.md), use the full book name instead of book code
        if not relative_path and source_file.name == f"{book_code}.md" and book_code in self.book_mappings:
            title = self.book_mappings[book_code]['name']
            
        # Apply transliteration for non-roman locales
        if locale != 'romn':
            title = self.convert_text_with_aksharamukha(title, locale)
            cleaned_content = self.convert_text_with_aksharamukha(cleaned_content, locale)
            
        # Remove H1 from content if it matches the title, as Starlight adds it automatically
        if title != "Untitled":
            lines = cleaned_content.split('\n')
            if lines and lines[0].strip() == f"# {title}":
                cleaned_content = '\n'.join(lines[1:]).lstrip()
            
        # Create target path
        target_path = self.get_target_path(book_code, relative_path, locale)
        if not target_path:
            print(f"Could not determine target path for {book_code}")
            return
            
        # Create target file
        # If it's a main book file (e.g. 1V.md), name it index.mdx
        if not relative_path and source_file.name == f"{book_code}.md":
            target_file = target_path / "index.mdx"
        else:
            # Replace dots with dashes in filenames
            safe_stem = source_file.stem.lower().replace('.', '-')
            target_file = target_path / f"{safe_stem}.mdx"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create content with frontmatter
        frontmatter = self.create_frontmatter(title, sidebar_order)
        final_content = frontmatter + cleaned_content
        
        # Write target file
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            # Reduced verbose output - only show errors
        except Exception as e:
            print(f"Error writing {target_file}: {e}")
    
    def migrate_directory(self, source_dir: Path, book_code: str, relative_path: str = '', locale: str = 'romn'):
        """Recursively migrate a directory"""
        if not source_dir.exists():
            return
            
        sidebar_order = 1
        
        # Process files in current directory
        for item in sorted(source_dir.iterdir()):
            if item.is_file() and item.suffix == '.md':
                self.migrate_file(item, book_code, relative_path, locale, sidebar_order)
                sidebar_order += 1
            elif item.is_dir():
                # Recursively process subdirectories, replacing dots with dashes in dir names
                safe_dir_name = item.name.lower().replace('.', '-')
                new_relative_path = (relative_path + '/' if relative_path else '') + safe_dir_name
                self.migrate_directory(item, book_code, new_relative_path, locale)
    
    def migrate_book(self, book_code: str, locale: str = 'romn', show_progress: bool = True):
        """Migrate a complete book"""
        source_book_dir = self.source_dir / book_code
        if not source_book_dir.exists():
            return
            
        # Show progress if requested
        if show_progress:
            print(f"Processing book {book_code}...")
        
        # Migrate the main book file
        main_file = self.source_dir / f"{book_code}.md"
        if main_file.exists():
            self.migrate_file(main_file, book_code, '', locale, 1)
        
        # Migrate the book directory
        self.migrate_directory(source_book_dir, book_code, '', locale)
    
    def generate_sidebar_structure(self, locale: str = 'romn') -> list:
        """Generate sidebar structure for navigator.js"""
        sidebar = {
            "label": "Tipiṭaka",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Tipiṭaka", "mymr"),  
                "th": self.convert_text_with_aksharamukha("Tipiṭaka", "thai"),
                "si": self.convert_text_with_aksharamukha("Tipiṭaka", "sinh"),
                "en": "Tipiṭaka",
                "hi": self.convert_text_with_aksharamukha("Tipiṭaka", "deva"),
                "kh": self.convert_text_with_aksharamukha("Tipiṭaka", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Tipiṭaka", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Tipiṭaka", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        # Vinayapiṭaka
        vinaya_item = {
            "label": "Vinayapiṭaka",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Vinayapiṭaka", "mymr"),
                "th": self.convert_text_with_aksharamukha("Vinayapiṭaka", "thai"),
                "si": self.convert_text_with_aksharamukha("Vinayapiṭaka", "sinh"),
                "en": "Vinayapiṭaka",
                "hi": self.convert_text_with_aksharamukha("Vinayapiṭaka", "deva"),
                "kh": self.convert_text_with_aksharamukha("Vinayapiṭaka", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Vinayapiṭaka", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Vinayapiṭaka", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        for book_code in self.structure['tipitaka']['v']['books']:
            if book_code in self.book_mappings:
                book_info = self.book_mappings[book_code]
                vinaya_item["items"].append({
                    "label": book_info['name'],
                    "translations": {
                        "my": self.convert_text_with_aksharamukha(book_info['name'], "mymr"),
                        "th": self.convert_text_with_aksharamukha(book_info['name'], "thai"),
                        "si": self.convert_text_with_aksharamukha(book_info['name'], "sinh"),
                        "en": book_info['name'],
                        "hi": self.convert_text_with_aksharamukha(book_info['name'], "deva"),
                        "kh": self.convert_text_with_aksharamukha(book_info['name'], "khmr"),
                        "lo": self.convert_text_with_aksharamukha(book_info['name'], "laoo"),
                        "ln": self.convert_text_with_aksharamukha(book_info['name'], "lana")
                    },
                    "link": f"/tipitaka/v/{book_info['abbrev']}/"
                })
        
        sidebar["items"].append(vinaya_item)
        
        # Suttantapiṭaka
        sutta_item = {
            "label": "Suttantapiṭaka",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Suttantapiṭaka", "mymr"),
                "th": self.convert_text_with_aksharamukha("Suttantapiṭaka", "thai"),
                "si": self.convert_text_with_aksharamukha("Suttantapiṭaka", "sinh"),
                "en": "Suttantapiṭaka",
                "hi": self.convert_text_with_aksharamukha("Suttantapiṭaka", "deva"),
                "kh": self.convert_text_with_aksharamukha("Suttantapiṭaka", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Suttantapiṭaka", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Suttantapiṭaka", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        for nikaya_key in ['d', 'm', 's', 'a', 'khu']:
            nikaya_name_map = {
                'd': 'Dīghanikāya', 'm': 'Majjhimanikāya', 's': 'Saṃyuttanikāya', 
                'a': 'Aṅguttaranikāya', 'khu': 'Khuddakanikāya'
            }
            nikaya_item = {
                "label": nikaya_name_map[nikaya_key],
                "translations": {
                    "my": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "mymr"),
                    "th": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "thai"),
                    "si": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "sinh"),
                    "en": nikaya_name_map[nikaya_key],
                    "hi": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "deva"),
                    "kh": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "khmr"),
                    "lo": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "laoo"),
                    "ln": self.convert_text_with_aksharamukha(nikaya_name_map[nikaya_key], "lana")
                },
                "collapsed": True,
                "items": []
            }
            
            for book_code in self.structure['tipitaka']['sutta'][nikaya_key]['books']:
                if book_code in self.book_mappings:
                    book_info = self.book_mappings[book_code]
                    nikaya_item["items"].append({
                        "label": book_info['name'],
                        "translations": {
                            "my": self.convert_text_with_aksharamukha(book_info['name'], "mymr"),
                            "th": self.convert_text_with_aksharamukha(book_info['name'], "thai"),
                            "si": self.convert_text_with_aksharamukha(book_info['name'], "sinh"),
                            "en": book_info['name'],
                            "hi": self.convert_text_with_aksharamukha(book_info['name'], "deva"),
                            "kh": self.convert_text_with_aksharamukha(book_info['name'], "khmr"),
                            "lo": self.convert_text_with_aksharamukha(book_info['name'], "laoo"),
                            "ln": self.convert_text_with_aksharamukha(book_info['name'], "lana")
                        },
                        "link": f"/tipitaka/sutta/{nikaya_key}/{book_info['abbrev']}/"
                    })
            
            sutta_item["items"].append(nikaya_item)
        
        sidebar["items"].append(sutta_item)
        
        # Abhidhammapiṭaka
        abhi_item = {
            "label": "Abhidhammapiṭaka",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "mymr"),
                "th": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "thai"),
                "si": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "sinh"),
                "en": "Abhidhammapiṭaka",
                "hi": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "deva"),
                "kh": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Abhidhammapiṭaka", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        # Direct books
        for book_code in self.structure['tipitaka']['abhi']['books']:
            if book_code in self.book_mappings:
                book_info = self.book_mappings[book_code]
                abhi_item["items"].append({
                    "label": book_info['name'],
                    "translations": {
                        "my": self.convert_text_with_aksharamukha(book_info['name'], "mymr"),
                        "th": self.convert_text_with_aksharamukha(book_info['name'], "thai"),
                        "si": self.convert_text_with_aksharamukha(book_info['name'], "sinh"),
                        "en": book_info['name'],
                        "hi": self.convert_text_with_aksharamukha(book_info['name'], "deva"),
                        "kh": self.convert_text_with_aksharamukha(book_info['name'], "khmr"),
                        "lo": self.convert_text_with_aksharamukha(book_info['name'], "laoo"),
                        "ln": self.convert_text_with_aksharamukha(book_info['name'], "lana")
                    },
                    "link": f"/tipitaka/abhi/{book_info['abbrev']}/"
                })
        
        # Yamaka
        yamaka_item = {
            "label": "Yamaka",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Yamaka", "mymr"),
                "th": self.convert_text_with_aksharamukha("Yamaka", "thai"),
                "si": self.convert_text_with_aksharamukha("Yamaka", "sinh"),
                "en": "Yamaka",
                "hi": self.convert_text_with_aksharamukha("Yamaka", "deva"),
                "kh": self.convert_text_with_aksharamukha("Yamaka", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Yamaka", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Yamaka", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        for book_code in self.structure['tipitaka']['abhi']['y']['books']:
            if book_code in self.book_mappings:
                book_info = self.book_mappings[book_code]
                yamaka_item["items"].append({
                    "label": book_info['name'],
                    "translations": {
                        "my": self.convert_text_with_aksharamukha(book_info['name'], "mymr"),
                        "th": self.convert_text_with_aksharamukha(book_info['name'], "thai"),
                        "si": self.convert_text_with_aksharamukha(book_info['name'], "sinh"),
                        "en": book_info['name'],
                        "hi": self.convert_text_with_aksharamukha(book_info['name'], "deva"),
                        "kh": self.convert_text_with_aksharamukha(book_info['name'], "khmr"),
                        "lo": self.convert_text_with_aksharamukha(book_info['name'], "laoo"),
                        "ln": self.convert_text_with_aksharamukha(book_info['name'], "lana")
                    },
                    "link": f"/tipitaka/abhi/y/{book_info['abbrev']}/"
                })
        
        abhi_item["items"].append(yamaka_item)
        
        # Paṭṭhāna
        patthana_item = {
            "label": "Paṭṭhāna",
            "translations": {
                "my": self.convert_text_with_aksharamukha("Paṭṭhāna", "mymr"),
                "th": self.convert_text_with_aksharamukha("Paṭṭhāna", "thai"),
                "si": self.convert_text_with_aksharamukha("Paṭṭhāna", "sinh"),
                "en": "Paṭṭhāna",
                "hi": self.convert_text_with_aksharamukha("Paṭṭhāna", "deva"),
                "kh": self.convert_text_with_aksharamukha("Paṭṭhāna", "khmr"),
                "lo": self.convert_text_with_aksharamukha("Paṭṭhāna", "laoo"),
                "ln": self.convert_text_with_aksharamukha("Paṭṭhāna", "lana")
            },
            "collapsed": True,
            "items": []
        }
        
        patthana_sections = [
            ("anu", "Dhammānuloma"),
            ("pac", "Dhammapaccanīya"),
            ("anupac", "Dhammānulomapaccanīya"),
            ("pacanu", "Dhammapaccanīyānuloma")
        ]
        
        for section_key, section_label in patthana_sections:
            section_item = {
                "label": section_label,
                "translations": {
                    "my": self.convert_text_with_aksharamukha(section_label, "mymr"),
                    "th": self.convert_text_with_aksharamukha(section_label, "thai"),
                    "si": self.convert_text_with_aksharamukha(section_label, "sinh"),
                    "en": section_label,
                    "hi": self.convert_text_with_aksharamukha(section_label, "deva"),
                    "kh": self.convert_text_with_aksharamukha(section_label, "khmr"),
                    "lo": self.convert_text_with_aksharamukha(section_label, "laoo"),
                    "ln": self.convert_text_with_aksharamukha(section_label, "lana")
                },
                "collapsed": True,
                "items": []
            }
            
            for book_code in self.structure['tipitaka']['abhi']['p'][section_key]['books']:
                if book_code in self.book_mappings:
                    book_info = self.book_mappings[book_code]
                    section_item["items"].append({
                        "label": book_info['name'],
                        "translations": {
                            "my": self.convert_text_with_aksharamukha(book_info['name'], "mymr"),
                            "th": self.convert_text_with_aksharamukha(book_info['name'], "thai"),
                            "si": self.convert_text_with_aksharamukha(book_info['name'], "sinh"),
                            "en": book_info['name'],
                            "hi": self.convert_text_with_aksharamukha(book_info['name'], "deva"),
                            "kh": self.convert_text_with_aksharamukha(book_info['name'], "khmr"),
                            "lo": self.convert_text_with_aksharamukha(book_info['name'], "laoo"),
                            "ln": self.convert_text_with_aksharamukha(book_info['name'], "lana")
                        },
                        "link": f"/tipitaka/abhi/p/{section_key}/{book_info['abbrev']}/"
                    })
            
            patthana_item["items"].append(section_item)
        
        abhi_item["items"].append(patthana_item)
        sidebar["items"].append(abhi_item)
        
        return [sidebar]
    
    def create_navigator_js(self):
        """Create navigator.js file for sidebar configuration"""
        # Generate single sidebar structure with translations
        sidebar_structure = self.generate_sidebar_structure()
        
        # Compress JSON to reduce file size
        js_content = f"""// Auto-generated sidebar navigation for Tipitaka content
// Generated by migrate_tipitaka.py

export const sidebarConfig = {json.dumps(sidebar_structure, separators=(',', ':'), ensure_ascii=False)};

export default sidebarConfig;
"""
        
        # Save navigator.js to python/md directory
        script_dir = Path(__file__).parent
        navigator_file = script_dir / 'navigator.js'
        with open(navigator_file, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"Created navigator.js with {len(self.locales)} locales")

    def _collect_all_books(self, structure_node: dict) -> list:
        """Recursively collect all book codes from the structure."""
        books = []
        if isinstance(structure_node, dict):
            if 'books' in structure_node:
                books.extend(structure_node['books'])
            for key in structure_node:
                if key != 'books':
                    books.extend(self._collect_all_books(structure_node[key]))
        elif isinstance(structure_node, list):
            for item in structure_node:
                books.extend(self._collect_all_books(item))
        return books
    
    def migrate_all(self, target_locales=None):
        """Migrate all content for specified locales"""
        if target_locales is None:
            target_locales = self.locales
        elif isinstance(target_locales, str):
            target_locales = [target_locales]
        
        # Validate locales
        invalid_locales = [loc for loc in target_locales if loc not in self.locales]
        if invalid_locales:
            print(f"Error: Invalid locale(s): {', '.join(invalid_locales)}")
            print(f"Valid locales: {', '.join(self.locales)}")
            return
        
        print("Starting Tipitaka content migration...")
        print(f"Target locales: {', '.join(target_locales)}")
        
        # Clean and create base directories for specified locales only
        print("Cleaning target locale directories...")
        for locale in target_locales:
            locale_dir = self.target_dir / locale
            if locale_dir.exists():
                shutil.rmtree(locale_dir)
            locale_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect all books and sort them properly
        all_books = self._collect_all_books(self.structure)
        
        # Sort books by their numeric order for proper processing sequence
        def sort_key(book_code):
            # Extract numeric part for sorting (e.g., '1V' -> 1, '12S1' -> 12, etc.)
            import re
            match = re.match(r'(\d+)', book_code)
            return int(match.group(1)) if match else 999
        
        sorted_books = sorted(list(set(all_books)), key=sort_key)
        
        # Migrate content for specified locales
        for locale in target_locales:
            print(f"\nProcessing locale: {locale}")
            for book_code in sorted_books:
                self.migrate_book(book_code, locale, show_progress=True)
        
        # Create navigator.js (always include all locales for completeness)
        self.create_navigator_js()
        
        print(f"\nMigration completed for {len(target_locales)} locale(s)!")

def main():
    """Main function"""
    import sys
    
    # Set up paths
    script_dir = Path(__file__).parent
    source_dir = script_dir / 'tipitaka'
    target_dir = script_dir.parent.parent / 'src' / 'content' / 'docs'
    
    # Create migrator
    migrator = TipitakaMigrator(str(source_dir), str(target_dir))
    
    # Check command line arguments for locale selection
    if len(sys.argv) > 1:
        # Get specified locales from command line
        target_locales = sys.argv[1:]
        
        # Validate all provided locales
        invalid_locales = [loc for loc in target_locales if loc not in migrator.locales]
        if invalid_locales:
            print(f"Error: Invalid locale(s): {', '.join(invalid_locales)}")
            print(f"Valid locales: {', '.join(migrator.locales)}")
            print(f"Usage: python {sys.argv[0]} [locale1] [locale2] ...")
            print(f"Example: python {sys.argv[0]} mymr")
            print(f"Example: python {sys.argv[0]} thai sinh")
            print(f"Example: python {sys.argv[0]}  # (migrates all locales)")
            return
        
        migrator.migrate_all(target_locales)
    else:
        # No arguments provided, migrate all locales
        migrator.migrate_all()

if __name__ == "__main__":
    main()
