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
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from aksharamukha import transliterate

class TipitakaMigrator:
    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.locales = ['romn', 'mymr', 'thai', 'sinh', 'deva', 'khmr', 'laoo', 'lana']
        
        # Setup logging (silent by default to preserve existing behavior)
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.ERROR)  # Only show errors by default
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.ERROR)
        
        # Cache for transliteration results (performance optimization)
        self._transliteration_cache = {}
        
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
        
        # Mapping book codes to directory abbreviations
        self.book_mappings = {
            # Vinayapiṭaka (vi)
            # parent directory is 'tipitaka/vi'
            '1V': {'abbrev': 'para', 'name': 'Pārājikapāḷi', 'references': ['1V', 'vi-para']},
            '2V': {'abbrev': 'paci', 'name': 'Pācittiyapāḷi', 'references': ['2V', 'vi-paci']},
            '3V': {'abbrev': 'maha', 'name': 'Mahāvaggapāḷi', 'references': ['3V', 'vi-maha']},
            '4V': {'abbrev': 'cula', 'name': 'Cūḷavaggapāḷi', 'references': ['4V', 'vi-cula']},
            '5V': {'abbrev': 'pari', 'name': 'Parivārapāḷi', 'references': ['5V', 'vi-pari']},
            
            # Dīghanikāya (dn)
            # parent directory is 'tipitaka/su/dn'
            '6D': {'abbrev': 'sila', 'name': 'Sīlakkhandhavaggapāḷi', 'references': ['6D', 'dn-sila']},
            '7D': {'abbrev': 'maha', 'name': 'Mahāvaggapāḷi', 'references': ['7D', 'dn-maha']},
            '8D': {'abbrev': 'pthi', 'name': 'Pāthikavaggapāḷi', 'references': ['8D', 'dn-pthi']},
            
            # Majjhimanikāya (mn)
            # parent directory is 'tipitaka/su/mn'
            '9M': {'abbrev': 'mula', 'name': 'Mūlapaṇṇāsapāḷi', 'references': ['9M', 'mn-mula']},
            '10M': {'abbrev': 'majj', 'name': 'Majjhimapaṇṇāsapāḷi', 'references': ['10M', 'mn-majj']},
            '11M': {'abbrev': 'upar', 'name': 'Uparipaṇṇāsapāḷi', 'references': ['11M', 'mn-upar']},
            
            # Saṃyuttanikāya (sn)
            # parent directory is 'tipitaka/su/sn'
            '12S1': {'abbrev': 'saga', 'name': 'Sagāthāvaggasaṃyuttapāḷi', 'references': ['12S1', 'sn-saga']},
            '12S2': {'abbrev': 'nida', 'name': 'Nidānavaggasaṃyuttapāḷi', 'references': ['12S2', 'sn-nida']},
            '13S3': {'abbrev': 'khan', 'name': 'Khandhavaggasaṃyuttapāḷi', 'references': ['13S3', 'sn-khan']},
            '13S4': {'abbrev': 'sala', 'name': 'Saḷāyatanavaggasaṃyuttapāḷi', 'references': ['13S4', 'sn-sala']},
            '14S5': {'abbrev': 'maha', 'name': 'Mahāvaggasaṃyuttapāḷi', 'references': ['14S5', 'sn-maha']},
            
            # Aṅguttaranikāya (an)
            # parent directory is 'tipitaka/su/an'
            '15A1': {'abbrev': 'eka', 'name': 'Ekakanipātapāḷi', 'references': ['15A1', 'an-eka']},
            '15A2': {'abbrev': 'duka', 'name': 'Dukanipātapāḷi', 'references': ['15A2', 'an-duka']},
            '15A3': {'abbrev': 'tika', 'name': 'Tikanipātapāḷi', 'references': ['15A3', 'an-tika']},
            '15A4': {'abbrev': 'catu', 'name': 'Catukkanipātapāḷi', 'references': ['15A4', 'an-catu']},
            '16A5': {'abbrev': 'panc', 'name': 'Pañcakanipātapāḷi', 'references': ['16A5', 'an-panc']},
            '16A6': {'abbrev': 'chak', 'name': 'Chakkanipātapāḷi', 'references': ['16A6', 'an-chak']},
            '16A7': {'abbrev': 'satt', 'name': 'Sattakanipātapāḷi', 'references': ['16A7', 'an-satt']},
            '17A8': {'abbrev': 'atth', 'name': 'Aṭṭhakanipātapāḷi', 'references': ['17A8', 'an-atth']},
            '17A9': {'abbrev': 'nava', 'name': 'Navakanipātapāḷi', 'references': ['17A9', 'an-nava']},
            '17A10': {'abbrev': 'dasa', 'name': 'Dasakanipātapāḷi', 'references': ['17A10', 'an-dasa']},
            '17A11': {'abbrev': 'ekad', 'name': 'Ekādasakanipātapāḷi', 'references': ['17A11', 'an-ekad']},
            
            # Khuddakanikāya (kn)
            # parent directory is 'tipitaka/su/kn'
            '18Kh': {'abbrev': 'kh', 'name': 'Khuddakapāṭhapāḷi', 'references': ['18Kh', 'kn-kh']},
            '18Dh': {'abbrev': 'dh', 'name': 'Dhammapadapāḷi', 'references': ['18Dh', 'kn-dh']},
            '18Ud': {'abbrev': 'ud', 'name': 'Udānapāḷi', 'references': ['18Ud', 'kn-ud']},
            '18It': {'abbrev': 'it', 'name': 'Itivuttakapāḷi', 'references': ['18It', 'kn-it']},
            '18Sn': {'abbrev': 'sn', 'name': 'Suttanipātapāḷi', 'references': ['18Sn', 'kn-sn']},
            '19Vv': {'abbrev': 'vv', 'name': 'Vimānavatthupāḷi', 'references': ['19Vv', 'kn-vv']},
            '19Pv': {'abbrev': 'pv', 'name': 'Petavatthupāḷi', 'references': ['19Pv', 'kn-pv']},
            '19Th1': {'abbrev': 'thrag', 'name': 'Theragāthāpāḷi', 'references': ['19Th1', 'kn-thrag']},
            '19Th2': {'abbrev': 'thrig', 'name': 'Therīgāthāpāḷi', 'references': ['19Th2', 'kn-thrig']},
            '20Ap1': {'abbrev': 'thraa', 'name': 'Therāpadānapāḷi', 'references': ['20Ap1', 'kn-thraa']},
            '20Ap2': {'abbrev': 'thria', 'name': 'Therīapadānapāḷi', 'references': ['20Ap2', 'kn-thria']},
            '21Bu': {'abbrev': 'bu', 'name': 'Buddhavaṃsapāḷi', 'references': ['21Bu', 'kn-bu']},
            '21Cp': {'abbrev': 'cp', 'name': 'Cariyāpiṭakapāḷi', 'references': ['21Cp', 'kn-cp']},
            '22J': {'abbrev': 'ja-1', 'name': 'Jātakapāḷi 1', 'references': ['22J', 'kn-ja-1']},
            '23J': {'abbrev': 'ja-2', 'name': 'Jātakapāḷi 2', 'references': ['23J', 'kn-ja-2']},
            '24Mn': {'abbrev': 'mn', 'name': 'Mahāniddesapāḷi', 'references': ['24Mn', 'kn-mn']},
            '25Cn': {'abbrev': 'cn', 'name': 'Cūḷaniddesapāḷi', 'references': ['25Cn', 'kn-cn']},
            '26Ps': {'abbrev': 'ps', 'name': 'Paṭisambhidāmaggapāḷi', 'references': ['26Ps', 'kn-ps']},
            '27Ne': {'abbrev': 'ne', 'name': 'Nettipāḷi', 'references': ['27Ne', 'kn-ne']},
            '27Pe': {'abbrev': 'pe', 'name': 'Peṭakopadesapāḷi', 'references': ['27Pe', 'kn-pe']},
            '28Mi': {'abbrev': 'mi', 'name': 'Milindapañhapāḷi', 'references': ['28Mi', 'kn-mi']},
            
            # Abhidhammapiṭaka (ab)
            # parent directory is 'tipitaka/ab'
            '29Dhs': {'abbrev': 'dhs', 'name': 'Dhammasaṅgaṇīpāḷi', 'references': ['29Dhs', 'ab-dhs']},
            '30Vbh': {'abbrev': 'vbh', 'name': 'Vibhaṅgapāḷi', 'references': ['30Vbh', 'ab-vbh']},
            '31Dht': {'abbrev': 'dht', 'name': 'Dhātukathāpāḷi', 'references': ['31Dht', 'ab-dht']},
            '31Pu': {'abbrev': 'pu', 'name': 'Puggalapaññattipāḷi', 'references': ['31Pu', 'ab-pu']},
            '32Kv': {'abbrev': 'kv', 'name': 'Kathāvatthupāḷi', 'references': ['32Kv', 'ab-kv']},
            
            # Yamaka (ab/yk)
            # parent directory is 'tipitaka/ab/yk'
            '33Y1': {'abbrev': 'yk1', 'name': 'Mūlayamakapāḷi', 'references': ['33Y1', 'yk1']},
            '33Y2': {'abbrev': 'yk2', 'name': 'Khandhayamakapāḷi', 'references': ['33Y2', 'yk2']},
            '33Y3': {'abbrev': 'yk3', 'name': 'Āyatanayamakapāḷi', 'references': ['33Y3', 'yk3']},
            '33Y4': {'abbrev': 'yk4', 'name': 'Dhātuyamakapāḷi', 'references': ['33Y4', 'yk4']},
            '33Y5': {'abbrev': 'yk5', 'name': 'Saccayamakapāḷi', 'references': ['33Y5', 'yk5']},
            '34Y6': {'abbrev': 'yk6', 'name': 'Saṅkhārayamakapāḷi', 'references': ['34Y6', 'yk6']},
            '34Y7': {'abbrev': 'yk7', 'name': 'Anusayayamakapāḷi', 'references': ['34Y7', 'yk7']},
            '34Y8': {'abbrev': 'yk8', 'name': 'Cittayamakapāḷi', 'references': ['34Y8', 'yk8']},
            '35Y9': {'abbrev': 'yk9', 'name': 'Dhammayamakapāḷi', 'references': ['35Y9', 'yk9']},
            '35Y10': {'abbrev': 'yk10', 'name': 'Indriyayamakapāḷi', 'references': ['35Y10', 'yk10']},
            
            # Paṭṭhāna (ab/pt) - Dhammānuloma
            # parent directory is 'tipitaka/ab/pt/anu'
            '36P1': {'abbrev': 'tika-1', 'name': 'Tikapaṭṭhānapāḷi 1', 'references': ['36P1', 'pt-anu-tika-1', 'pt1.1']},
            '37P1': {'abbrev': 'tika-2', 'name': 'Tikapaṭṭhānapāḷi 2', 'references': ['37P1', 'pt-anu-tika-2', 'pt1.2']},
            '38P2': {'abbrev': 'duka', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['38P2', 'pt-anu-duka', 'pt2']},
            '39P3': {'abbrev': 'dukatika', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['39P3', 'pt-anu-dukatika', 'pt3']},
            '39P4': {'abbrev': 'tikaduka', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['39P4', 'pt-anu-tikaduka', 'pt4']},
            '39P5': {'abbrev': 'tikatika', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['39P5', 'pt-anu-tikatika', 'pt5']},
            '39P6': {'abbrev': 'dukaduka', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['39P6', 'pt-anu-dukaduka', 'pt6']},
            
            # Paṭṭhāna - Dhammapaccanīya
            # parent directory is 'tipitaka/ab/pt/pac'
            '40P7': {'abbrev': 'tika', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P7', 'pt-pac-tika', 'pt7']},
            '40P8': {'abbrev': 'duka', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P8', 'pt-pac-duka', 'pt8']},
            '40P9': {'abbrev': 'dukatika', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P9', 'pt-pac-dukatika', 'pt9']},
            '40P10': {'abbrev': 'tikaduka', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P10', 'pt-pac-tikaduka', 'pt10']},
            '40P11': {'abbrev': 'tikatika', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P11', 'pt-pac-tikatika', 'pt11']},
            '40P12': {'abbrev': 'dukaduka', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P12', 'pt-pac-dukaduka', 'pt12']},
            
            # Paṭṭhāna - Dhammānulomapaccanīya
            # parent directory is 'tipitaka/ab/pt/anupac'
            '40P13': {'abbrev': 'tika', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P13', 'pt-anupac-tika', 'pt13']},
            '40P14': {'abbrev': 'duka', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P14', 'pt-anupac-duka', 'pt14']},
            '40P15': {'abbrev': 'dukatika', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P15', 'pt-anupac-dukatika', 'pt15']},
            '40P16': {'abbrev': 'tikaduka', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P16', 'pt-anupac-tikaduka', 'pt16']},
            '40P17': {'abbrev': 'tikatika', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P17', 'pt-anupac-tikatika', 'pt17']},
            '40P18': {'abbrev': 'dukaduka', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P18', 'pt-anupac-dukaduka', 'pt18']},
            
            # Paṭṭhāna - Dhammapaccanīyānuloma
            # parent directory is 'tipitaka/ab/pt/pacanu'
            '40P19': {'abbrev': 'tika', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P19', 'pt-pacanu-tika', 'pt19']},
            '40P20': {'abbrev': 'duka', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P20', 'pt-pacanu-duka', 'pt20']},
            '40P21': {'abbrev': 'dukatika', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P21', 'pt-pacanu-dukatika', 'pt21']},
            '40P22': {'abbrev': 'tikaduka', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P22', 'pt-pacanu-tikaduka', 'pt22']},
            '40P23': {'abbrev': 'tikatika', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P23', 'pt-pacanu-tikatika', 'pt23']},
            '40P24': {'abbrev': 'dukaduka', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P24', 'pt-pacanu-dukaduka', 'pt24']},
        }
        
        # Hierarchical structure mapping
        self.structure = {
            'tipitaka': {
                'vi': {  # Vinayapiṭaka
                    'books': ['1V', '2V', '3V', '4V', '5V']
                },
                'su': {  # Suttantapiṭaka
                    'dn': {  # Dīghanikāya
                        'books': ['6D', '7D', '8D']
                    },
                    'mn': {  # Majjhimanikāya
                        'books': ['9M', '10M', '11M']
                    },
                    'sn': {  # Saṃyuttanikāya
                        'books': ['12S1', '12S2', '13S3', '13S4', '14S5']
                    },
                    'an': {  # Aṅguttaranikāya
                        'books': ['15A1', '15A2', '15A3', '15A4', '16A5', '16A6', '16A7', '17A8', '17A9', '17A10', '17A11']
                    },
                    'kn': {  # Khuddakanikāya
                        'books': ['18Kh', '18Dh', '18Ud', '18It', '18Sn', '19Vv', '19Pv', '19Th1', '19Th2', 
                                 '20Ap1', '20Ap2', '21Bu', '21Cp', '22J', '23J', '24Mn', '25Cn', '26Ps', '27Ne', '27Pe', '28Mi']
                    }
                },
                'ab': {  # Abhidhammapiṭaka
                    'books': ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv'],
                    'yk': {  # Yamaka
                        'books': ['33Y1', '33Y2', '33Y3', '33Y4', '33Y5', '34Y6', '34Y7', '34Y8', '35Y9', '35Y10']
                    },
                    'pt': {  # Paṭṭhāna
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
    
    def _safe_read_file(self, file_path: Path) -> Optional[str]:
        """Safely read file with better error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # Preserve original behavior - silently handle missing files
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error in {file_path}: {e}")
            return None
        except Exception as e:
            # Log error but don't break the flow
            self.logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def _safe_write_file(self, file_path: Path, content: str) -> bool:
        """Safely write file with better error handling"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            # Print error to maintain visibility like original code
            print(f"Error writing {file_path}: {e}")
            return False
    
    def convert_text_with_aksharamukha(self, text: str, locale: str) -> str:
        """Convert text using aksharamukha transliteration with caching and improved error handling"""
        if locale == 'romn':
            return text  # No conversion needed for roman (source text is already in roman)
        
        # Check cache first for performance
        cache_key = (text, locale)
        if cache_key in self._transliteration_cache:
            return self._transliteration_cache[cache_key]
        
        config = self.transliteration_config.get(locale)
        if not config:
            return text  # Preserve original behavior - return unchanged text
        
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
                    except Exception as e:
                        # Log error but preserve original behavior - return unchanged segment
                        self.logger.error(f"Transliteration failed for segment '{segment}': {e}")
                        result_segments.append(segment)
                else:
                    result_segments.append(segment)
            
            result = ''.join(result_segments)
            
            # Cache the result for performance
            self._transliteration_cache[cache_key] = result
            return result
            
        except Exception as e:
            # Preserve original behavior - silently return original text
            self.logger.error(f"Transliteration failed for locale {locale}: {e}")
            return text
        
    def clean_content(self, content: str, book_code: str = '') -> str:
        """Remove breadcrumb navigation, go to previous/next links, and fix internal links."""
        lines = content.split('\n')
        cleaned_lines = []
        
        # Pattern to find markdown links like [text](link)
        link_pattern = re.compile(r'(\[.*?\]\()(.+?)(\))')

        for line in lines:
            # Skip breadcrumb lines (contains [Home](/) pattern or breadcrumb-like structure)
            if '[Home](/)' in line or ('/' in line and line.count('[') >= 2 and line.count(']') >= 2):
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
    
    def create_frontmatter(self, title: str, sidebar_order: int, references: list = None, basket: str = None) -> str:
        """Create Astro Starlight frontmatter"""
        frontmatter = f"""---
title: "{title}"
tableOfContents: false
sidebar:
  order: {sidebar_order}"""
        
        if references:
            # Format references as YAML array
            frontmatter += f"""
references: {json.dumps(references)}"""
        
        # Add type and basket before closing ---
        frontmatter += f"""
type: "tipitaka\""""
        
        if basket:
            frontmatter += f"""
basket: "{basket}\""""
        
        frontmatter += """
---

"""
        return frontmatter
    
    def extract_title_from_content(self, content: str) -> str:
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"
    
    def get_namo_formula(self, book_code: str, locale: str = 'romn') -> str:
        """Extract Namo formula from 0.md file if exists"""
        zero_file = self.source_dir / book_code / "0.md"
        if not zero_file.exists():
            return ""
            
        # Use safe file reading
        content = self._safe_read_file(zero_file)
        if content is None:
            return ""  # Preserve original behavior
                
        # Find the Namo formula line
        lines = content.split('\n')
        namo_line = ""
        
        for line in lines:
            # Look for the Namo formula pattern
            if "Namo tassa Bhagavato Arahato Sammāsambuddhassa" in line:
                namo_line = line.strip()
                break
            # Also check for numbered version
            elif line.strip().startswith("1\\. Namo tassa"):
                namo_line = line.strip()
                break
                
        if namo_line:
            # Apply transliteration for non-roman locales
            if locale != 'romn':
                namo_line = self.convert_text_with_aksharamukha(namo_line, locale)
            return namo_line
                
        return ""

    def get_target_path(self, book_code: str, relative_path: str, locale: str = 'romn') -> Path:
        """Generate target path based on hierarchical structure"""
        if book_code not in self.book_mappings:
            return None
            
        book_abbrev = self.book_mappings[book_code]['abbrev']
        
        # Determine the hierarchical path
        base_path = self.target_dir / locale
        
        # Find the book in the structure and build path
        if book_code.endswith('V'):  # Vinayapiṭaka
            target_path = base_path / 'tipitaka' / 'vi' / book_abbrev
        elif book_code.endswith('D'):  # Dīghanikāya
            target_path = base_path / 'tipitaka' / 'su' / 'dn' / book_abbrev
        elif book_code.endswith('M'):  # Majjhimanikāya
            target_path = base_path / 'tipitaka' / 'su' / 'mn' / book_abbrev
        elif book_code.startswith(('12S', '13S', '14S')):  # Saṃyuttanikāya
            target_path = base_path / 'tipitaka' / 'su' / 'sn' / book_abbrev
        elif book_code.startswith(('15A', '16A', '17A')):  # Aṅguttaranikāya
            target_path = base_path / 'tipitaka' / 'su' / 'an' / book_abbrev
        elif book_code.startswith(('18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28')):  # Khuddakanikāya
            target_path = base_path / 'tipitaka' / 'su' / 'kn' / book_abbrev
        elif book_code in ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv']:  # Abhidhammapiṭaka direct
            target_path = base_path / 'tipitaka' / 'ab' / book_abbrev
        elif book_code.startswith(('33Y', '34Y', '35Y')):  # Yamaka
            target_path = base_path / 'tipitaka' / 'ab' / 'yk' / book_abbrev
        elif book_code.startswith('36P') or book_code.startswith('37P') or book_code.startswith('38P') or book_code.startswith('39P'):  # Paṭṭhāna - Dhammānuloma
            target_path = base_path / 'tipitaka' / 'ab' / 'pt' / 'anu' / book_abbrev
        elif book_code.startswith('40P') and int(book_code[3:]) <= 12:  # Paṭṭhāna - Dhammapaccanīya
            target_path = base_path / 'tipitaka' / 'ab' / 'pt' / 'pac' / book_abbrev
        elif book_code.startswith('40P') and 13 <= int(book_code[3:]) <= 18:  # Paṭṭhāna - Dhammānulomapaccanīya
            target_path = base_path / 'tipitaka' / 'ab' / 'pt' / 'anupac' / book_abbrev
        elif book_code.startswith('40P') and int(book_code[3:]) >= 19:  # Paṭṭhāna - Dhammapaccanīyānuloma
            target_path = base_path / 'tipitaka' / 'ab' / 'pt' / 'pacanu' / book_abbrev
        else:
            return None
            
        # Add the relative path
        if relative_path and relative_path != '.':
            target_path = target_path / relative_path
            
        return target_path
    
    def _get_basket_for_book(self, book_code: str) -> str:
        """Determine basket based on book code using the structure mapping"""
        # Check Vinayapiṭaka
        if book_code in self.structure['tipitaka']['vi']['books']:
            return 'vi'
        
        # Check Suttantapiṭaka
        for nikaya in self.structure['tipitaka']['su'].values():
            if isinstance(nikaya, dict) and 'books' in nikaya:
                if book_code in nikaya['books']:
                    return 'su'
        
        # Check Abhidhammapiṭaka
        if book_code in self.structure['tipitaka']['ab']['books']:
            return 'ab'
        
        # Check Yamaka
        if book_code in self.structure['tipitaka']['ab']['yk']['books']:
            return 'ab'
        
        # Check Paṭṭhāna sections
        for section in self.structure['tipitaka']['ab']['pt'].values():
            if isinstance(section, dict) and 'books' in section:
                if book_code in section['books']:
                    return 'ab'
        
        return None
    
    def get_book_index_link(self, book_code: str, locale: str = 'romn') -> str:
        """Get the link to the book's index.mdx"""
        book_abbrev = self.book_mappings.get(book_code, {}).get('abbrev', book_code.lower())
        
        # Determine book link based on its category
        if book_code.endswith('V'):  # Vinayapiṭaka
            return f"/{locale}/tipitaka/vi/{book_abbrev}/"
        elif book_code.endswith('D'):  # Dīghanikāya
            return f"/{locale}/tipitaka/su/dn/{book_abbrev}/"
        elif book_code.endswith('M'):  # Majjhimanikāya
            return f"/{locale}/tipitaka/su/mn/{book_abbrev}/"
        elif book_code.startswith(('12S', '13S', '14S')):  # Saṃyuttanikāya
            return f"/{locale}/tipitaka/su/sn/{book_abbrev}/"
        elif book_code.startswith(('15A', '16A', '17A')):  # Aṅguttaranikāya
            return f"/{locale}/tipitaka/su/an/{book_abbrev}/"
        elif book_code.startswith(('18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28')):  # Khuddakanikāya
            return f"/{locale}/tipitaka/su/kn/{book_abbrev}/"
        elif book_code in ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv']:  # Abhidhammapiṭaka direct
            return f"/{locale}/tipitaka/ab/{book_abbrev}/"
        elif book_code.startswith(('33Y', '34Y', '35Y')):  # Yamaka
            return f"/{locale}/tipitaka/ab/yk/{book_abbrev}/"
        elif book_code.startswith(('36P', '37P', '38P', '39P')):  # Paṭṭhāna - Dhammānuloma
            return f"/{locale}/tipitaka/ab/pt/anu/{book_abbrev}/"
        elif book_code.startswith('40P'):
            book_num = int(book_code[3:])
            if book_num <= 12:  # Dhammapaccanīya
                return f"/{locale}/tipitaka/ab/pt/pac/{book_abbrev}/"
            elif 13 <= book_num <= 18:  # Dhammānulomapaccanīya
                return f"/{locale}/tipitaka/ab/pt/anupac/{book_abbrev}/"
            else:  # Dhammapaccanīyānuloma
                return f"/{locale}/tipitaka/ab/pt/pacanu/{book_abbrev}/"
        
        return f"/{locale}/tipitaka/{book_abbrev}/"
    
    def migrate_file(self, source_file: Path, book_code: str, relative_path: str = '', locale: str = 'romn', sidebar_order: int = 1):
        """Migrate a single file with improved safety"""
        if not source_file.exists():
            return  # Preserve original behavior
            
        # Use safe file reading
        content = self._safe_read_file(source_file)
        if content is None:
            # Preserve original behavior - silently skip if can't read
            return
            
        # Clean content
        cleaned_content = self.clean_content(content, book_code)
        if not cleaned_content.strip():
            return  # Preserve original behavior
            
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
            print(f"Could not determine target path for {book_code}")  # Preserve original print
            return
        
        # Determine basket based on book code using the structure mapping
        basket = self._get_basket_for_book(book_code)
            
        # Create target file
        # If it's a main book file (e.g. 1V.md), name it index.mdx
        if not relative_path and source_file.name == f"{book_code}.md":
            target_file = target_path / "index.mdx"
            # Get references for main book files (index.mdx only)
            book_references = self.book_mappings.get(book_code, {}).get('references', [])
            
            # Check for 0.md file in the book directory and extract Namo formula
            namo_content = self.get_namo_formula(book_code, locale)
            if namo_content:
                # Add Namo formula at the beginning of content
                if cleaned_content:
                    cleaned_content = namo_content + "\n\n" + cleaned_content
                else:
                    cleaned_content = namo_content
                    
        else:
            # Replace dots with dashes in filenames
            safe_stem = source_file.stem.lower().replace('.', '-')
            target_file = target_path / f"{safe_stem}.mdx"
            book_references = None  # No references for non-index files
        
        # Create content with frontmatter
        frontmatter = self.create_frontmatter(title, sidebar_order, book_references, basket)
        final_content = frontmatter + cleaned_content
        
        # Use safe file writing
        self._safe_write_file(target_file, final_content)
    
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
            "collapsed": False,
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
        
        for book_code in self.structure['tipitaka']['vi']['books']:
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
                    "link": f"/tipitaka/vi/{book_info['abbrev']}/"
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
        
        for nikaya_key in ['dn', 'mn', 'sn', 'an', 'kn']:
            nikaya_name_map = {
                'dn': 'Dīghanikāya', 'mn': 'Majjhimanikāya', 'sn': 'Saṃyuttanikāya', 
                'an': 'Aṅguttaranikāya', 'kn': 'Khuddakanikāya'
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
            
            for book_code in self.structure['tipitaka']['su'][nikaya_key]['books']:
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
                        "link": f"/tipitaka/su/{nikaya_key}/{book_info['abbrev']}/"
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
        for book_code in self.structure['tipitaka']['ab']['books']:
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
                    "link": f"/tipitaka/ab/{book_info['abbrev']}/"
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
        
        for book_code in self.structure['tipitaka']['ab']['yk']['books']:
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
                    "link": f"/tipitaka/ab/yk/{book_info['abbrev']}/"
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
            
            for book_code in self.structure['tipitaka']['ab']['pt'][section_key]['books']:
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
                        "link": f"/tipitaka/ab/pt/{section_key}/{book_info['abbrev']}/"
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
        """Migrate all content for specified locales with improved error handling"""
        if target_locales is None:
            target_locales = self.locales
        elif isinstance(target_locales, str):
            target_locales = [target_locales]
        
        # Validate locales (preserve original validation behavior)
        invalid_locales = [loc for loc in target_locales if loc not in self.locales]
        if invalid_locales:
            print(f"Error: Invalid locale(s): {', '.join(invalid_locales)}")
            print(f"Valid locales: {', '.join(self.locales)}")
            return  # Preserve original behavior - return without exception
        
        print("Starting Tipitaka content migration...")
        print(f"Target locales: {', '.join(target_locales)}")
        
        # Add basic error handling for directory operations
        try:
            print("Cleaning target locale directories...")
            for locale in target_locales:
                locale_dir = self.target_dir / locale
                if locale_dir.exists():
                    shutil.rmtree(locale_dir)
                locale_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error setting up directories: {e}")
            return  # Exit gracefully like original behavior
        
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
                # Add basic error handling but continue processing
                try:
                    self.migrate_book(book_code, locale, show_progress=True)
                except Exception as e:
                    print(f"Error processing book {book_code} for locale {locale}: {e}")
                    continue  # Continue with next book
        
        # Always try to create navigator.js
        try:
            self.create_navigator_js()
        except Exception as e:
            print(f"Error creating navigator.js: {e}")
        
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
