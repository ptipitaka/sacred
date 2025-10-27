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
import multiprocessing
import concurrent.futures
import time
import threading
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
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
        
        # Thread-safe locks
        self._cache_lock = threading.RLock()
        self._batch_lock = threading.RLock()
        self._progress_lock = threading.RLock()
        
        # Cache for transliteration results (performance optimization)
        self._transliteration_cache = {}
        
        # File content cache to reduce I/O operations
        self._file_content_cache = {}
        self._batch_write_buffer = {}  # Per-locale buffer
        self._batch_size = 100  # Files to buffer before batch write
        
        # Progress tracking
        self._progress_stats = {}
        self._completed_files = set()
        
        # Memory management
        self._cache_max_size = 10000  # Maximum cache entries
        self._cache_cleanup_threshold = 8000  # Start cleanup when reaching this
        
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
            '1V': {'abbrev': 'para', 'name': 'Pārājikapāḷi', 'references': ['1V', 'vi-para', 'para']},
            '2V': {'abbrev': 'paci', 'name': 'Pācittiyapāḷi', 'references': ['2V', 'vi-paci', 'paci']},
            '3V': {'abbrev': 'vi-maha', 'name': 'Mahāvaggapāḷi', 'references': ['3V', 'vi-maha', 'maha']},
            '4V': {'abbrev': 'cula', 'name': 'Cūḷavaggapāḷi', 'references': ['4V', 'vi-cula', 'cula']},
            '5V': {'abbrev': 'pari', 'name': 'Parivārapāḷi', 'references': ['5V', 'vi-pari', 'pari']},
            
            # Dīghanikāya (dn)
            # parent directory is 'tipitaka/su/dn'
            '6D': {'abbrev': 'sila', 'name': 'Sīlakkhandhavaggapāḷi', 'references': ['6D', 'dn-sila', 'sila']},
            '7D': {'abbrev': 'dn-maha', 'name': 'Mahāvaggapāḷi', 'references': ['7D', 'dn-maha', 'maha']},
            '8D': {'abbrev': 'pthi', 'name': 'Pāthikavaggapāḷi', 'references': ['8D', 'dn-pthi', 'pthi']},
            
            # Majjhimanikāya (mn)
            # parent directory is 'tipitaka/su/mn'
            '9M': {'abbrev': 'mula', 'name': 'Mūlapaṇṇāsapāḷi', 'references': ['9M', 'mn-mula', 'mula']},
            '10M': {'abbrev': 'majj', 'name': 'Majjhimapaṇṇāsapāḷi', 'references': ['10M', 'mn-majj', 'majj']},
            '11M': {'abbrev': 'upar', 'name': 'Uparipaṇṇāsapāḷi', 'references': ['11M', 'mn-upar', 'upar']},
            
            # Saṃyuttanikāya (sn)
            # parent directory is 'tipitaka/su/sn'
            '12S1': {'abbrev': 'saga', 'name': 'Sagāthāvaggasaṃyuttapāḷi', 'references': ['12S1', 'sn-saga', 'saga']},
            '12S2': {'abbrev': 'nida', 'name': 'Nidānavaggasaṃyuttapāḷi', 'references': ['12S2', 'sn-nida', 'nida']},
            '13S3': {'abbrev': 'khan', 'name': 'Khandhavaggasaṃyuttapāḷi', 'references': ['13S3', 'sn-khan', 'khan']},
            '13S4': {'abbrev': 'sala', 'name': 'Saḷāyatanavaggasaṃyuttapāḷi', 'references': ['13S4', 'sn-sala', 'sala']},
            '14S5': {'abbrev': 'sn-maha', 'name': 'Mahāvaggasaṃyuttapāḷi', 'references': ['14S5', 'sn-maha', 'maha']},
            
            # Aṅguttaranikāya (an)
            # parent directory is 'tipitaka/su/an'
            '15A1': {'abbrev': 'a1', 'name': 'Ekakanipātapāḷi', 'references': ['15A1', 'an-eka', 'a1']},
            '15A2': {'abbrev': 'a2', 'name': 'Dukanipātapāḷi', 'references': ['15A2', 'an-duka', 'a2']},
            '15A3': {'abbrev': 'a3', 'name': 'Tikanipātapāḷi', 'references': ['15A3', 'an-tika', 'a3']},
            '15A4': {'abbrev': 'a4', 'name': 'Catukkanipātapāḷi', 'references': ['15A4', 'an-catu', 'a4']},
            '16A5': {'abbrev': 'a5', 'name': 'Pañcakanipātapāḷi', 'references': ['16A5', 'an-panc', 'a5']},
            '16A6': {'abbrev': 'a6', 'name': 'Chakkanipātapāḷi', 'references': ['16A6', 'an-chak', 'a6']},
            '16A7': {'abbrev': 'a7', 'name': 'Sattakanipātapāḷi', 'references': ['16A7', 'an-satt', 'a7']},
            '17A8': {'abbrev': 'a8', 'name': 'Aṭṭhakanipātapāḷi', 'references': ['17A8', 'an-atth', 'a8']},
            '17A9': {'abbrev': 'a9', 'name': 'Navakanipātapāḷi', 'references': ['17A9', 'an-nava', 'a9']},
            '17A10': {'abbrev': 'a10', 'name': 'Dasakanipātapāḷi', 'references': ['17A10', 'an-dasa', 'a10']},
            '17A11': {'abbrev': 'a11', 'name': 'Ekādasakanipātapāḷi', 'references': ['17A11', 'an-ekad', 'a11']},
            
            # Khuddakanikāya (kn)
            # parent directory is 'tipitaka/su/kn'
            '18Kh': {'abbrev': 'kh', 'name': 'Khuddakapāṭhapāḷi', 'references': ['18Kh', 'kn-kh', 'kh']},
            '18Dh': {'abbrev': 'dh', 'name': 'Dhammapadapāḷi', 'references': ['18Dh', 'kn-dh', 'dh']},
            '18Ud': {'abbrev': 'ud', 'name': 'Udānapāḷi', 'references': ['18Ud', 'kn-ud', 'ud']},
            '18It': {'abbrev': 'it', 'name': 'Itivuttakapāḷi', 'references': ['18It', 'kn-it', 'it']},
            '18Sn': {'abbrev': 'sn', 'name': 'Suttanipātapāḷi', 'references': ['18Sn', 'kn-sn', 'sn']},
            '19Vv': {'abbrev': 'vv', 'name': 'Vimānavatthupāḷi', 'references': ['19Vv', 'kn-vv', 'vv']},
            '19Pv': {'abbrev': 'pv', 'name': 'Petavatthupāḷi', 'references': ['19Pv', 'kn-pv', 'pv']},
            '19Th1': {'abbrev': 'th1', 'name': 'Theragāthāpāḷi', 'references': ['19Th1', 'kn-thrag', 'thrag']},
            '19Th2': {'abbrev': 'th2', 'name': 'Therīgāthāpāḷi', 'references': ['19Th2', 'kn-thrig', 'thrig']},
            '20Ap1': {'abbrev': 'ap1', 'name': 'Therāpadānapāḷi', 'references': ['20Ap1', 'kn-thraa', 'thraa']},
            '20Ap2': {'abbrev': 'ap2', 'name': 'Therīapadānapāḷi', 'references': ['20Ap2', 'kn-thria', 'thria']},
            '21Bu': {'abbrev': 'bu', 'name': 'Buddhavaṃsapāḷi', 'references': ['21Bu', 'kn-bu', 'bu']},
            '21Cp': {'abbrev': 'cp', 'name': 'Cariyāpiṭakapāḷi', 'references': ['21Cp', 'kn-cp', 'cp']},
            '22J': {'abbrev': 'ja1', 'name': 'Jātakapāḷi 1', 'references': ['22J', 'kn-ja-1', 'ja-1']},
            '23J': {'abbrev': 'ja2', 'name': 'Jātakapāḷi 2', 'references': ['23J', 'kn-ja-2', 'ja-2']},
            '24Mn': {'abbrev': 'mn', 'name': 'Mahāniddesapāḷi', 'references': ['24Mn', 'kn-mn', 'mn']},
            '25Cn': {'abbrev': 'cn', 'name': 'Cūḷaniddesapāḷi', 'references': ['25Cn', 'kn-cn', 'cn']},
            '26Ps': {'abbrev': 'ps', 'name': 'Paṭisambhidāmaggapāḷi', 'references': ['26Ps', 'kn-ps', 'ps']},
            '27Ne': {'abbrev': 'ne', 'name': 'Nettipāḷi', 'references': ['27Ne', 'kn-ne', 'ne']},
            '27Pe': {'abbrev': 'pe', 'name': 'Peṭakopadesapāḷi', 'references': ['27Pe', 'kn-pe', 'pe']},
            '28Mi': {'abbrev': 'mi', 'name': 'Milindapañhapāḷi', 'references': ['28Mi', 'kn-mi', 'mi']},
            
            # Abhidhammapiṭaka (ab)
            # parent directory is 'tipitaka/ab'
            '29Dhs': {'abbrev': 'dhs', 'name': 'Dhammasaṅgaṇīpāḷi', 'references': ['29Dhs', 'ab-dhs', 'dhs']},
            '30Vbh': {'abbrev': 'vbh', 'name': 'Vibhaṅgapāḷi', 'references': ['30Vbh', 'ab-vbh', 'vbh']},
            '31Dht': {'abbrev': 'dht', 'name': 'Dhātukathāpāḷi', 'references': ['31Dht', 'ab-dht', 'dht']},
            '31Pu': {'abbrev': 'pu', 'name': 'Puggalapaññattipāḷi', 'references': ['31Pu', 'ab-pu', 'pu']},
            '32Kv': {'abbrev': 'kv', 'name': 'Kathāvatthupāḷi', 'references': ['32Kv', 'ab-kv', 'kv']},
            
            # Yamaka (ab/yk)
            # parent directory is 'tipitaka/ab/yk'
            '33Y1': {'abbrev': 'y1', 'name': 'Mūlayamakapāḷi', 'references': ['33Y1', 'y1']},
            '33Y2': {'abbrev': 'y2', 'name': 'Khandhayamakapāḷi', 'references': ['33Y2', 'y2']},
            '33Y3': {'abbrev': 'y3', 'name': 'Āyatanayamakapāḷi', 'references': ['33Y3', 'y3']},
            '33Y4': {'abbrev': 'y4', 'name': 'Dhātuyamakapāḷi', 'references': ['33Y4', 'y4']},
            '33Y5': {'abbrev': 'y5', 'name': 'Saccayamakapāḷi', 'references': ['33Y5', 'y5']},
            '34Y6': {'abbrev': 'y6', 'name': 'Saṅkhārayamakapāḷi', 'references': ['34Y6', 'y6']},
            '34Y7': {'abbrev': 'y7', 'name': 'Anusayayamakapāḷi', 'references': ['34Y7', 'y7']},
            '34Y8': {'abbrev': 'y8', 'name': 'Cittayamakapāḷi', 'references': ['34Y8', 'y8']},
            '35Y9': {'abbrev': 'y9', 'name': 'Dhammayamakapāḷi', 'references': ['35Y9', 'y9']},
            '35Y10': {'abbrev': 'y10', 'name': 'Indriyayamakapāḷi', 'references': ['35Y10', 'y10']},
            
            # Paṭṭhāna (ab/pt) - Dhammānuloma
            # parent directory is 'tipitaka/ab/pt/anu'
            '36P1': {'abbrev': 'p1-1', 'name': 'Tikapaṭṭhānapāḷi 1', 'references': ['36P1', 'pt-anu-tika-1', 'p1.1']},
            '37P1': {'abbrev': 'p1-2', 'name': 'Tikapaṭṭhānapāḷi 2', 'references': ['37P1', 'pt-anu-tika-2', 'p1.2']},
            '38P2': {'abbrev': 'p2', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['38P2', 'pt-anu-duka', 'p2']},
            '39P3': {'abbrev': 'p3', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['39P3', 'pt-anu-dukatika', 'p3']},
            '39P4': {'abbrev': 'p4', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['39P4', 'pt-anu-tikaduka', 'p4']},
            '39P5': {'abbrev': 'p5', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['39P5', 'pt-anu-tikatika', 'p5']},
            '39P6': {'abbrev': 'p6', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['39P6', 'pt-anu-dukaduka', 'p6']},
            
            # Paṭṭhāna - Dhammapaccanīya
            # parent directory is 'tipitaka/ab/pt/pac'
            '40P7': {'abbrev': 'p7', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P7', 'pt-pac-tika', 'p7']},
            '40P8': {'abbrev': 'p8', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P8', 'pt-pac-duka', 'p8']},
            '40P9': {'abbrev': 'p9', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P9', 'pt-pac-dukatika', 'p9']},
            '40P10': {'abbrev': 'p10', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P10', 'pt-pac-tikaduka', 'p10']},
            '40P11': {'abbrev': 'p11', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P11', 'pt-pac-tikatika', 'p11']},
            '40P12': {'abbrev': 'p12', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P12', 'pt-pac-dukaduka', 'p12']},
            
            # Paṭṭhāna - Dhammānulomapaccanīya
            # parent directory is 'tipitaka/ab/pt/anupac'
            '40P13': {'abbrev': 'p13', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P13', 'pt-anupac-tika', 'p13']},
            '40P14': {'abbrev': 'p14', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P14', 'pt-anupac-duka', 'p14']},
            '40P15': {'abbrev': 'p15', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P15', 'pt-anupac-dukatika', 'p15']},
            '40P16': {'abbrev': 'p16', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P16', 'pt-anupac-tikaduka', 'p16']},
            '40P17': {'abbrev': 'p17', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P17', 'pt-anupac-tikatika', 'p17']},
            '40P18': {'abbrev': 'p18', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P18', 'pt-anupac-dukaduka', 'p18']},
            
            # Paṭṭhāna - Dhammapaccanīyānuloma
            # parent directory is 'tipitaka/ab/pt/pacanu'
            '40P19': {'abbrev': 'p19', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P19', 'pt-pacanu-tika', 'p19']},
            '40P20': {'abbrev': 'p20', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P20', 'pt-pacanu-duka', 'p20']},
            '40P21': {'abbrev': 'p21', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P21', 'pt-pacanu-dukatika', 'p21']},
            '40P22': {'abbrev': 'p22', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P22', 'pt-pacanu-tikaduka', 'p22']},
            '40P23': {'abbrev': 'p23', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P23', 'pt-pacanu-tikatika', 'p23']},
            '40P24': {'abbrev': 'p24', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P24', 'pt-pacanu-dukaduka', 'p24']},
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
        
        # Precompute abbreviation lookups and prepare page mapping structures
        self._abbrev_to_book_code = {
            info['abbrev']: code for code, info in self.book_mappings.items()
        }
        self._book_number_cache = {
            abbrev: self._extract_book_number(code)
            for abbrev, code in self._abbrev_to_book_code.items()
        }
        self._book_reference_lookup = {}
        for code, info in self.book_mappings.items():
            references = set(info.get('references', []))
            references.add(info.get('abbrev', ''))
            references.add(code)
            for ref in references:
                normalized = (ref or '').strip().lower()
                if normalized:
                    self._book_reference_lookup[normalized] = code
        self._book_prefix_slugs: Set[str] = set()
        for code, info in self.book_mappings.items():
            candidates = {code, info.get('abbrev', '')}
            candidates.update(info.get('references', []) or [])
            for candidate in candidates:
                slug = self._slugify_link_segment(candidate)
                if slug:
                    self._book_prefix_slugs.add(slug)
        self._division_page_map: Dict[str, Dict[str, List[int]]] = {}
        self._division_page_state: Dict[str, Dict[str, int]] = {}
        self._page_map_loaded = False
        self._page_map_lock = threading.RLock()
        
        self.sidebar_data = {}
        
        # Performance configurations
        self.max_workers = min(32, (os.cpu_count() or 1) * 2)  # Optimal worker count
        self.chunk_size = 50  # Files to process in one chunk
        
        # Progress tracking
        self._start_time = None
        self._processed_files = 0
        self._total_files = 0
    
    def get_available_books(self) -> List[str]:
        """Get all available book codes"""
        return list(self.book_mappings.keys())
    
    def get_available_sections(self) -> List[str]:
        """Get all available section codes (vi, su, ab)"""
        return ['vi', 'su', 'ab']
    
    def validate_books(self, book_codes: List[str]) -> Tuple[List[str], List[str]]:
        """Validate book codes and return (valid_books, invalid_books)"""
        valid_books = []
        invalid_books = []
        available_books = self.get_available_books()
        
        for book in book_codes:
            if book in available_books:
                valid_books.append(book)
            else:
                invalid_books.append(book)
        
        return valid_books, invalid_books
    
    def filter_books_by_section(self, section: str) -> List[str]:
        """Get all books in a specific section (vi, su, ab)"""
        books = []
        
        # Look inside tipitaka structure
        if 'tipitaka' in self.structure:
            tipitaka_structure = self.structure['tipitaka']
            
            if section in tipitaka_structure:
                section_data = tipitaka_structure[section]
                
                if isinstance(section_data, dict):
                    # If section has direct books
                    if 'books' in section_data:
                        books.extend(section_data['books'])
                    
                    # If section has subsections with books
                    for sub_section, sub_data in section_data.items():
                        if sub_section != 'books' and isinstance(sub_data, dict):
                            if 'books' in sub_data:
                                books.extend(sub_data['books'])
                            else:
                                # For nested structures like pt -> anu -> books
                                for sub_sub_section, sub_sub_data in sub_data.items():
                                    if isinstance(sub_sub_data, dict) and 'books' in sub_sub_data:
                                        books.extend(sub_sub_data['books'])
        
        return books
    
    def should_process_book(self, book_code: str, target_books: Optional[List[str]] = None) -> bool:
        """Check if a book should be processed based on target_books filter"""
        if target_books is None:
            return True
        return book_code in target_books

    @staticmethod
    def _extract_book_number(book_code: str) -> str:
        """Extract the numeric volume prefix from a book code (e.g. 15A4 -> 15)"""
        if not book_code:
            return ''
        match = re.match(r'(\d+)', book_code)
        return match.group(1) if match else ''

    @staticmethod
    def _normalize_division_key(division_number: str) -> Optional[str]:
        """Normalize division identifiers to match numeric paragraph mapping keys"""
        if not division_number:
            return None
        match = re.match(r'(\d+)', division_number)
        return match.group(1) if match else None

    @staticmethod
    def _slugify_link_segment(segment: str) -> str:
        """Normalize a single path segment for internal links"""
        if not segment:
            return ''
        value = segment.strip()
        if not value:
            return ''
        if value.lower().endswith('.md'):
            value = value[:-3]
        value = value.replace(' ', '-')
        value = value.replace('.', '-')
        value = value.replace('_', '-')
        value = re.sub(r'-{2,}', '-', value)
        value = value.strip('-')
        return value.lower()

    def _normalize_internal_link(self, link: str, current_slug: str) -> str:
        """Convert legacy markdown links to Astro-friendly relative paths"""
        if not link:
            return link

        link = link.strip()
        if not link:
            return link

        lowered = link.lower()
        if lowered.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            return link
        if link.startswith('#'):
            return link

        anchor = ''
        if '#' in link:
            link, anchor = link.split('#', 1)
            anchor = '#' + anchor

        if not link:
            return anchor or link

        is_absolute = link.startswith('/')
        raw_parts = link.split('/')
        normalized_parts: List[str] = []

        for part in raw_parts:
            part = part.strip()
            if not part or part == '.':
                continue
            if part == '..':
                normalized_parts.append('..')
                continue

            slug = self._slugify_link_segment(part)
            if not slug:
                continue

            has_content = any(p not in ('..',) for p in normalized_parts)
            if not has_content:
                if slug == current_slug:
                    continue
                if slug in self._book_prefix_slugs:
                    continue

            normalized_parts.append(slug)

        if not normalized_parts:
            normalized_path = '/' if is_absolute else './'
        else:
            normalized_path = '/'.join(normalized_parts)

            if is_absolute:
                normalized_path = '/' + normalized_path.lstrip('/')
                if normalized_path != '/' and not normalized_path.endswith('/'):
                    normalized_path += '/'
            elif normalized_path.startswith('..'):
                if not normalized_path.endswith('/'):
                    normalized_path += '/'
            else:
                normalized_path = './' + normalized_path.lstrip('./')
                if not normalized_path.endswith('/'):
                    normalized_path += '/'

        return normalized_path + anchor

    def _ensure_paragraph_page_map(self):
        """Load paragraph -> page mappings from SQLite once per process"""
        if self._page_map_loaded:
            return
        with self._page_map_lock:
            if self._page_map_loaded:
                return
            page_map: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
            try:
                db_path = Path(__file__).resolve().parent.parent / 'db' / 'tipitaka_pali.db'
                if not db_path.exists():
                    self.logger.warning(f"Paragraph mapping database not found at {db_path}")
                    self._division_page_map = {}
                    self._page_map_loaded = True
                    return
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT book_abbrv, paragraph_number, page_number
                        FROM paragraphs
                        WHERE book_abbrv IS NOT NULL
                          AND paragraph_number IS NOT NULL
                          AND page_number IS NOT NULL
                        ORDER BY book_abbrv, page_number, paragraph_number, rowid
                        """
                    )
                    for book_abbrv, paragraph_number, page_number in cursor.fetchall():
                        book_abbrv = (book_abbrv or '').strip()
                        if not book_abbrv:
                            continue
                        key = str(int(paragraph_number))
                        page_map[book_abbrv][key].append(int(page_number))
            except Exception as e:
                self.logger.error(f"Failed to load paragraph-page mapping: {e}")
                page_map = defaultdict(lambda: defaultdict(list))
            # Convert nested defaultdicts to regular dicts for safer iteration later
            self._division_page_map = {
                abbr: {para: pages for para, pages in book_map.items()}
                for abbr, book_map in page_map.items()
            }
            self._page_map_loaded = True

    def _reset_page_tracking(self, book_abbrv: str):
        """Reset sequential mapping state for the specified book abbreviation"""
        if not book_abbrv:
            return
        self._ensure_paragraph_page_map()
        self._division_page_state[book_abbrv] = {}

    def _get_book_number(self, book_abbrv: str) -> str:
        """Get book volume number (as string) for a given book abbreviation"""
        return self._book_number_cache.get(book_abbrv, '')

    @staticmethod
    def _natural_sort_key(value: str) -> list:
        """Produce a list key that sorts strings using human-friendly numeric order"""
        if not value:
            return [0]
        parts = re.split(r'(\d+)', value)
        key = []
        for part in parts:
            if not part:
                continue
            if part.isdigit():
                key.append(int(part))
            else:
                key.append(part.lower())
        return key

    def _generate_lookup_keys(self, target: str) -> List[str]:
        """Generate prioritized lookup keys for a markdown link target"""
        if not target:
            return []
        value = target.split('#', 1)[0].strip()
        if not value or value.startswith('http'):
            return []
        while value.startswith('./'):
            value = value[2:]
        while value.startswith('../'):
            value = value[3:]
        value = value.lstrip('/')

        keys: List[str] = []
        def _append(key: str):
            if key and key not in keys:
                keys.append(key)

        _append(value)
        _append(value.lower())

        if value.endswith('.md'):
            stem = value[:-3]
            _append(stem)
            _append(stem.lower())

        if value.endswith('/'):
            trimmed = value.rstrip('/')
            _append(trimmed)
            _append(trimmed.lower())

        return keys

    def _build_entry_lookup(self, entries: List[Path], source_dir: Path, book_root: Path) -> Dict[str, Path]:
        """Build lookup table mapping link targets to actual filesystem entries"""
        lookup: Dict[str, Path] = {}
        try:
            relative_parts = source_dir.relative_to(book_root).parts
        except ValueError:
            relative_parts = ()

        for entry in entries:
            name = entry.name
            entry_keys = {name, name.lower()}
            if entry.is_dir():
                entry_keys.update({f"{name}/", f"{name.lower()}/"})
            if name.endswith('.md'):
                stem = name[:-3]
                entry_keys.update({stem, stem.lower()})

            if relative_parts:
                rel_path = '/'.join((*relative_parts, name))
            else:
                rel_path = name
            entry_keys.update({rel_path, rel_path.lower()})
            if entry.is_dir():
                entry_keys.update({f"{rel_path}/", f"{rel_path.lower()}/"})
            if rel_path.endswith('.md'):
                rel_stem = rel_path[:-3]
                entry_keys.update({rel_stem, rel_stem.lower()})

            # Include hyphenated variants for targets that already replaced dots
            hyphenated = name.replace('.', '-')
            entry_keys.add(hyphenated)
            entry_keys.add(hyphenated.lower())

            for key in entry_keys:
                if key not in lookup:
                    lookup[key] = entry
        return lookup

    def _order_entries_from_parent(self, source_dir: Path, entries: List[Path], book_code: str) -> Optional[List[Path]]:
        """Use parent markdown file to determine ordering when natural sort fails"""
        if not entries:
            return []

        parent_md = source_dir.parent / f"{source_dir.name}.md"
        book_root = self.source_dir / book_code

        if not parent_md.exists():
            if source_dir == book_root:
                parent_md = self.source_dir / f"{book_code}.md"
                if not parent_md.exists():
                    return None
            else:
                return None

        content = self._read_raw_file(parent_md)
        if content is None:
            return None

        entry_lookup = self._build_entry_lookup(entries, source_dir, book_root)
        pattern = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
        ordered_entries: List[Path] = []
        seen: Set[Path] = set()

        for target in pattern.findall(content):
            for key in self._generate_lookup_keys(target):
                entry = entry_lookup.get(key)
                if entry and entry not in seen:
                    ordered_entries.append(entry)
                    seen.add(entry)
                    break

        if not ordered_entries:
            return None

        remaining = [entry for entry in entries if entry not in seen]
        remaining.sort(key=lambda p: p.name.lower())
        ordered_entries.extend(remaining)
        return ordered_entries

    def _sort_directory_entries(self, source_dir: Path, book_code: str) -> List[Path]:
        """Sort directory entries, falling back to parent content when necessary"""
        entries = list(source_dir.iterdir())
        if not entries:
            return []

        try:
            return sorted(entries, key=lambda p: self._natural_sort_key(p.name))
        except TypeError:
            pass

        ordered = self._order_entries_from_parent(source_dir, entries, book_code)
        if ordered:
            return ordered

        # Final fallback: simple case-insensitive sort to keep deterministic order
        return sorted(entries, key=lambda p: p.name.lower())

    def _get_next_division_page(self, book_abbrv: str, division_number: str) -> Optional[int]:
        """Retrieve the next page reference for a division, consuming sequential duplicates"""
        if not book_abbrv or not division_number:
            return None
        self._ensure_paragraph_page_map()
        division_key = self._normalize_division_key(division_number)
        if not division_key:
            return None
        book_map = self._division_page_map.get(book_abbrv)
        if not book_map:
            return None
        pages = book_map.get(division_key)
        if not pages:
            return None
        state = self._division_page_state.setdefault(book_abbrv, {})
        index = state.get(division_key, 0)
        if index >= len(pages):
            return pages[-1]
        page = pages[index]
        state[division_key] = index + 1
        return page
    
    def _safe_read_file(self, file_path: Path) -> Optional[str]:
        """Safely read file with caching and better error handling"""
        cache_key = str(file_path)
        
        # Check cache first
        if cache_key in self._file_content_cache:
            return self._file_content_cache[cache_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Cache the raw content
            self._file_content_cache[cache_key] = content
            
            # ========== ทำการ normalize ทั้งหมดตั้งแต่อ่านไฟล์ ==========
            
            # 1. แปลง -- เป็น – สำหรับตัวเลข (normalize number ranges)
            content = re.sub(r'(\d+)--(\d+)', r'\1–\2', content)
            
            # 2. ทำการ clean content พื้นฐาน
            lines = content.split('\n')
            cleaned_lines = []
            
            # Pattern สำหรับตรวจสอบ
            link_pattern = re.compile(r'(\[.*?\]\()(.+?)(\))')
            title_list_pattern = re.compile(r'^[ \t]*\*[ \t]+[A-Za-zāīūēōṅñṭḍṇḷṃṅḍṭṇḷṃāīūēōĀĪŪĒŌ, ]+[ \t]*$')

            current_slug = self._slugify_link_segment(file_path.stem)
            
            for line in lines:
                # 3. Skip breadcrumb lines
                if '[Home](/)' in line or ('/' in line and line.count('[') >= 2 and line.count(']') >= 2):
                    continue
                    
                # 4. Skip navigation lines
                if line.startswith('[Go to '):
                    continue
                    
                # 5. Skip title-only list items
                if title_list_pattern.match(line):
                    continue
                
                # 6. Fix internal links (remove .md, lowercase, dots to dashes, remove book_code prefix)
                def fix_link(match):
                    pre, link, post = match.groups()
                    normalized_link = self._normalize_internal_link(link, current_slug)
                    return f"{pre}{normalized_link}{post}"
                
                line = link_pattern.sub(fix_link, line)
                
                # 7. Normalize PE spacing
                line = self._normalize_pe_spacing(line)
                
                cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines).strip()
            
            return content
            
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
    
    def _read_raw_file(self, file_path: Path) -> Optional[str]:
        """Read file content without post-processing (used for order detection)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as fh:
                return fh.read()
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.error(f"Failed to read raw file {file_path}: {exc}")
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
    
    def _batch_write_file(self, file_path: Path, content: str, locale: str):
        """Add file to batch write buffer (thread-safe, per-locale)"""
        with self._batch_lock:
            if locale not in self._batch_write_buffer:
                self._batch_write_buffer[locale] = []
            
            self._batch_write_buffer[locale].append((file_path, content))
            
            # Flush if buffer is full
            if len(self._batch_write_buffer[locale]) >= self._batch_size:
                self._flush_batch_writes(locale)
    
    def _flush_batch_writes(self, locale: str = None):
        """Write all buffered files to disk (thread-safe)"""
        with self._batch_lock:
            locales_to_flush = [locale] if locale else list(self._batch_write_buffer.keys())
            
            for loc in locales_to_flush:
                if loc not in self._batch_write_buffer or not self._batch_write_buffer[loc]:
                    continue
                    
                for file_path, content in self._batch_write_buffer[loc]:
                    try:
                        # Ensure parent directory exists
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Write file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                            
                    except Exception as e:
                        self.logger.error(f"Failed to write {file_path}: {e}")
                
                # Clear buffer for this locale
                self._batch_write_buffer[loc].clear()
    
    def _clear_caches(self):
        """Clear all caches to free memory"""
        self._file_content_cache.clear()
        self._transliteration_cache.clear()
        self._flush_batch_writes()
    
    def _update_progress(self, increment: int = 1, locale: str = None):
        """Update progress counter thread-safely"""
        with self._progress_lock:
            self._processed_files += increment
            
            # Update per-locale stats if provided
            if locale and locale in self._progress_stats:
                self._progress_stats[locale]['processed'] += increment
            
            if self._total_files > 0 and self._processed_files % 10 == 0:
                progress = (self._processed_files / self._total_files) * 100
                elapsed = time.time() - self._start_time if self._start_time else 0
                
                if elapsed > 0:
                    rate = self._processed_files / elapsed
                    eta = (self._total_files - self._processed_files) / rate if rate > 0 else 0
                    print(f"Progress: {progress:.1f}% ({self._processed_files}/{self._total_files}) "
                          f"Rate: {rate:.1f} files/s ETA: {eta:.0f}s", end='\r')
    
    def _estimate_total_files(self, books: List[str]) -> int:
        """Estimate total number of files to process"""
        total = 0
        for book_code in books:
            book_dir = self.source_dir / book_code
            if book_dir.exists():
                # Count .md files recursively
                for item in book_dir.rglob('*.md'):
                    total += 1
                # Add main book file
                main_file = self.source_dir / f"{book_code}.md"
                if main_file.exists():
                    total += 1
        return total
    
    def _calculate_content_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content for validation"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _validate_migration_result(self, original_path: Path, migrated_path: Path, 
                                   original_content: str, migrated_content: str, 
                                   locale: str) -> bool:
        """Validate that migration preserved content integrity"""
        try:
            # For romn locale, content should be identical (except for formatting)
            if locale == 'romn':
                # Normalize whitespace for comparison
                orig_normalized = re.sub(r'\s+', ' ', original_content.strip())
                migrated_normalized = re.sub(r'\s+', ' ', migrated_content.strip())
                
                if orig_normalized != migrated_normalized:
                    self.logger.warning(f"Content mismatch for {original_path} -> {migrated_path}")
                    return False
            
            # Check basic structure is preserved
            orig_lines = len(original_content.split('\n'))
            migrated_lines = len(migrated_content.split('\n'))
            
            # Allow some flexibility in line count (due to formatting changes)
            if abs(orig_lines - migrated_lines) > 5:
                self.logger.warning(f"Significant line count difference: {orig_lines} -> {migrated_lines}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed for {original_path}: {e}")
            return False
    
    def _cleanup_cache_if_needed(self):
        """Clean up caches if they get too large"""
        with self._cache_lock:
            if len(self._transliteration_cache) > self._cache_max_size:
                # Remove oldest half of entries
                items = list(self._transliteration_cache.items())
                keep_count = self._cache_cleanup_threshold
                self._transliteration_cache = dict(items[-keep_count:])
            
            if len(self._file_content_cache) > self._cache_max_size:
                items = list(self._file_content_cache.items())
                keep_count = self._cache_cleanup_threshold
                self._file_content_cache = dict(items[-keep_count:])
    
    def post_process_transliteration(self, text: str, locale: str) -> str:
        """Post-process transliteration results to fix common errors"""
        if locale == 'romn' or not text:
            return text
        
        # Define correction mappings for each locale
        corrections = {
            'thai': {
                # Fix common Thai transliteration errors
                'ึ': 'ิํ',  # Fix niggahita representation
                'ปโญฺห': 'ปญฺโห',
                'ตุเมฺห': 'ตุมฺเห',
                'อโสฺสสิ': 'อสฺโสสิ',
                'เทฺว': 'ทฺเว',
                # Add more Thai corrections as needed
            },
            'sinh': {
                # Fix common Sinhala transliteration errors
                # Add Sinhala corrections as needed
            },
            'mymr': {
                # Fix common Myanmar transliteration errors
                # Add Myanmar corrections as needed
            },
            'deva': {
                # Fix common Devanagari transliteration errors
                # Add Devanagari corrections as needed
            },
            'khmr': {
                # Fix common Khmer transliteration errors
                # Add Khmer corrections as needed
            },
            'laoo': {
                # Fix common Lao transliteration errors
                # Add Lao corrections as needed
            },
            'lana': {
                # Fix common Tai Tham transliteration errors
                # Add Tai Tham corrections as needed
            }
        }
        
        # Apply corrections for the specific locale
        if locale in corrections:
            for wrong, correct in corrections[locale].items():
                text = text.replace(wrong, correct)
        
        return text

    def convert_text_with_aksharamukha(self, text: str, locale: str) -> str:
        """Convert text using aksharamukha transliteration with caching and improved error handling"""
        if locale == 'romn':
            return text  # No conversion needed for roman (source text is already in roman)
        
        # Check cache first for performance (thread-safe)
        cache_key = (text, locale)
        with self._cache_lock:
            if cache_key in self._transliteration_cache:
                return self._transliteration_cache[cache_key]
        
        config = self.transliteration_config.get(locale)
        if not config:
            return text  # Preserve original behavior - return unchanged text
        
        try:
            # Extract and protect markdown links from transliteration
            import re
            
            # Find all markdown links [text](url)
            link_pattern = re.compile(r'(\[.*?\]\()(.+?)(\))')
            links = []
            
            def replace_link(match):
                nonlocal links
                pre, url, post = match.groups()
                # Store the URL and replace with placeholder
                placeholder = f"__LINK_PLACEHOLDER_{len(links)}__"
                # Keep the URL as-is since it was already processed in _safe_read_file
                links.append(url)
                return f"{pre}{placeholder}{post}"
            
            # Replace links with placeholders
            protected_text = link_pattern.sub(replace_link, text)
            
            # Split text into segments, preserving numbers and symbols
            segments = re.split(r'(\d+|[^\w\u0100-\u017F\u1E00-\u1EFF]+)', protected_text)
            result_segments = []
            
            for segment in segments:
                if re.match(r'^\d+$|^[^\w\u0100-\u017F\u1E00-\u1EFF]+$', segment):
                    # Keep numbers and non-Pali characters as is
                    result_segments.append(segment)
                elif segment.strip():
                    # Check if this segment contains a link placeholder
                    if '__LINK_PLACEHOLDER_' in segment:
                        # Don't transliterate link placeholders
                        result_segments.append(segment)
                    else:
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
            
            # Restore original URLs in links
            for i, original_url in enumerate(links):
                placeholder = f"__LINK_PLACEHOLDER_{i}__"
                result = result.replace(placeholder, original_url)
            
            # Apply post-processing corrections
            result = self.post_process_transliteration(result, locale)
            
            # Cache the result for performance (thread-safe)
            with self._cache_lock:
                self._transliteration_cache[cache_key] = result
                # Cleanup cache if needed
                self._cleanup_cache_if_needed()
            return result
            
        except Exception as e:
            # Preserve original behavior - silently return original text
            self.logger.error(f"Transliteration failed for locale {locale}: {e}")
            return text
    
    def _bulk_transliterate(self, texts: List[str], locale: str) -> Dict[str, str]:
        """Bulk transliterate multiple texts for better performance"""
        if locale == 'romn':
            return {text: text for text in texts}
        
        config = self.transliteration_config.get(locale)
        if not config:
            return {text: text for text in texts}
        
        results = {}
        uncached_texts = []
        
        # Check cache for existing translations (thread-safe)
        with self._cache_lock:
            for text in texts:
                cache_key = (text, locale)
                if cache_key in self._transliteration_cache:
                    results[text] = self._transliteration_cache[cache_key]
                else:
                    uncached_texts.append(text)
        
        # Bulk process uncached texts
        for text in uncached_texts:
            try:
                converted = self.convert_text_with_aksharamukha(text, locale)
                results[text] = converted
            except Exception as e:
                self.logger.error(f"Bulk transliteration failed for '{text}': {e}")
                results[text] = text
        
        return results
    
    def convert_emphasis_to_component(self, text: str) -> tuple[str, bool]:
        """Convert **text** to <Emphasis>text</Emphasis> and return whether Emphasis import is needed
        Returns tuple of (converted_text, needs_emphasis_import)
        """
        import re
        
        # Check if text contains **text** patterns
        emphasis_pattern = r'\*\*([^*]+)\*\*'
        
        if not re.search(emphasis_pattern, text):
            return text, False
        
        # Convert **text** to <Emphasis>text</Emphasis>
        converted_text = re.sub(emphasis_pattern, r'<Emphasis>\1</Emphasis>', text)
        
        return converted_text, True
    
    def _normalize_pe_spacing(self, text: str) -> str:
        """Normalize spacing around ...pe... patterns
        Ensures there's exactly one space before and after ...pe... if not at line boundaries
        """
        import re
        
        # Pattern to match ...pe... with various ellipsis formats
        # Matches: ...pe..., …pe…, . . . pe . . ., etc.
        pe_patterns = [
            r'(\.{3}pe\.{3})',      # ...pe...
            r'(…pe…)',              # …pe… (Unicode ellipsis)
            r'(\.\.\.pe\.\.\.)',    # ...pe... (explicit dots)
            r'(\.\s*\.\s*\.\s*pe\s*\.\s*\.\s*\.)', # . . . pe . . .
        ]
        
        for pattern in pe_patterns:
            # Find all matches with their positions
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            # Process matches from right to left to preserve positions
            for match in reversed(matches):
                start, end = match.span()
                pe_text = match.group(1)
                
                # Check if there's space before and after
                has_space_before = start == 0 or text[start - 1].isspace()
                has_space_after = end == len(text) or text[end].isspace()
                
                # Build replacement with proper spacing
                replacement = pe_text
                
                # Add space before if needed (not at start of line)
                if start > 0 and not has_space_before:
                    replacement = ' ' + replacement
                
                # Add space after if needed (not at end of line)  
                if end < len(text) and not has_space_after:
                    replacement = replacement + ' '
                
                # Replace in text
                text = text[:start] + replacement + text[end:]
        
        return text
        
    def clean_content(self, content: str, book_code: str = '') -> str:
        """Link cleaning is now handled in _safe_read_file, so this function does minimal processing"""
        return content  # All link processing moved to _safe_read_file for consistency
    
    def extract_book_id_from_path(self, file_path: Path) -> str:
        """Extract book identifier from file path for PageFind metadata"""
        path_parts = file_path.parts
        if 'tipitaka' not in path_parts:
            return ''

        tipitaka_index = path_parts.index('tipitaka')

        # Preserve previous fallback behaviour in case a match is still not found
        primary_candidate = ''
        if tipitaka_index + 2 < len(path_parts):
            next_segment = path_parts[tipitaka_index + 2]
            if tipitaka_index + 3 < len(path_parts) and next_segment in ['sn', 'an', 'kn', 'mn', 'dn']:
                primary_candidate = path_parts[tipitaka_index + 3]
            else:
                primary_candidate = next_segment

        suffix_parts = list(path_parts[tipitaka_index + 1:])

        # Check each path segment after tipitaka for a known book reference
        for segment in suffix_parts:
            if '.' in segment:
                continue  # Skip file names like index.mdx
            normalized = segment.strip().lower()
            if not normalized or not re.search(r'[a-z]', normalized):
                continue
            match = self._book_reference_lookup.get(normalized)
            if match:
                return match

        # Try combined adjacent segments (e.g., pt + anu -> pt-anu)
        for left, right in zip(suffix_parts, suffix_parts[1:]):
            if '.' in left or '.' in right:
                continue
            combined = f"{left.strip().lower()}-{right.strip().lower()}"
            match = self._book_reference_lookup.get(combined)
            if match:
                return match

        return primary_candidate
    
    def is_verses_content(self, content: str) -> bool:
        """Check if content appears to be verses based on italic markdown formatting"""
        lines = content.split('\n')
        
        # Count lines that are not empty
        non_empty_lines = [line for line in lines if line.strip()]
        
        if len(non_empty_lines) == 0:
            return False
        
        # Count lines that contain italic markdown formatting (_text_)
        italic_lines = 0
        for line in non_empty_lines:
            line = line.strip()
            # Check if line contains italic formatting with underscore
            if '_' in line and line.count('_') >= 2:
                # Simple check: if line starts and ends with _, or contains _text_
                if (line.startswith('_') and line.endswith('_')) or \
                   re.search(r'_[^_]+_', line):
                    italic_lines += 1
        
        # If most lines (>= 70%) have italic formatting, consider it verses
        return italic_lines / len(non_empty_lines) >= 0.7
    
    def detect_table_of_contents(self, content: str) -> tuple[bool, list, str]:
        """Detect if content contains a table of contents list
        Returns tuple of (has_toc, toc_lines, remaining_content)
        """
        lines = content.split('\n')
        toc_lines = []
        non_toc_lines = []
        in_toc_section = False
        toc_found = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a markdown list item with a link pattern like:
            # * [1.1.1 Paṭhamapārājikasikkhāpada](1-1/1-1-1)
            toc_pattern = re.match(r'^\s*\*\s+\[([^\]]+)\]\(([^)]+)\)', line)
            
            if toc_pattern:
                if not in_toc_section:
                    # Start of TOC section
                    in_toc_section = True
                    toc_found = True
                
                toc_lines.append(line)
                i += 1
                continue
            
            # If we were in TOC section and hit non-TOC line
            if in_toc_section and line.strip() != '':
                # End of TOC section
                in_toc_section = False
            
            # If not in TOC section, add to non-TOC lines
            if not in_toc_section:
                non_toc_lines.append(line)
            
            i += 1
        
        remaining_content = '\n'.join(non_toc_lines)
        return toc_found, toc_lines, remaining_content
    
    def wrap_toc_with_component(self, toc_lines: list, book_id: str = '', section_title: str = '') -> str:
        """Wrap table of contents lines with TableOfContents component"""
        if not toc_lines:
            return ""
        
        # Extract section from title if available (e.g., "1.1" from "1.1 Pārājikakaṇḍa")
        section = ""
        if section_title:
            # Try to extract number pattern like "1.1", "1.2.3", etc.
            section_match = re.match(r'^(\d+(?:\.\d+)*)', section_title)
            if section_match:
                section = section_match.group(1)
        
        # Build component opening tag
        if book_id and section:
            component_open = f'<TableOfContents book="{book_id}" section="{section}">'
        elif book_id:
            component_open = f'<TableOfContents book="{book_id}">'
        else:
            component_open = '<TableOfContents>'
        
        # Combine lines
        result = [component_open]
        result.extend(toc_lines)
        result.append('</TableOfContents>')
        
        return '\n'.join(result)
    
    def convert_emphasis_markdown(self, text: str) -> str:
        """Convert **text** to <Emphasis>text</Emphasis> component"""
        # Pattern to match **text** where text doesn't contain ** inside
        pattern = r'\*\*([^*]+)\*\*'
        
        def replace_emphasis(match):
            content = match.group(1)
            return f'<Emphasis>{content}</Emphasis>'
        
        return re.sub(pattern, replace_emphasis, text)
    
    def convert_to_mdx_with_components(self, content: str, book_id: str = '', title: str = '') -> tuple[str, str]:
        """Convert markdown content to MDX with Astro components
        Returns tuple of (imports_content, converted_content)
        """
        # Check for table of contents first
        has_toc, toc_lines, remaining_content = self.detect_table_of_contents(content)
        
        # Add component imports (include TableOfContents if needed)
        imports = """import Division from '@components/Division.astro';
import Paragraph from '@components/Paragraph.astro';
import Emphasis from '@components/Emphasis.astro';"""
        
        if has_toc:
            imports += """
import TableOfContents from '@components/TableOfContents.astro';"""
        
        imports += """

"""
        
        # Use remaining content (without TOC) for component processing
        lines = remaining_content.split('\n')
        converted_lines = []
        current_division = None
        after_separator = False
        in_paragraph = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for content separator --- (skip it from output)
            if line.strip() == '---':
                after_separator = True
                # Close any open paragraph before separator
                if in_paragraph:
                    converted_lines.append('</Paragraph>')
                    in_paragraph = False
                # Close current division before separator
                if current_division is not None:
                    converted_lines.append('</Division>')
                    current_division = None
                
                # Skip adding the --- separator to output
                i += 1
                continue
            
            # Check for division pattern (24.), (25.), (504–512.), etc.
            division_match = re.match(r'^\((\d+(?:(?:--|–)\d+)?)\.\)$', line.strip())
            if division_match:
                division_num = division_match.group(1)
                
                # Close any open paragraph
                if in_paragraph:
                    converted_lines.append('</Paragraph>')
                    in_paragraph = False
                
                # Close previous division if exists
                if current_division is not None:
                    converted_lines.append('</Division>')
                
                # Start new division
                division_attributes = [f'number="{division_num}"']
                if book_id:
                    division_attributes.append(f'book="{book_id}"')
                # Always include edition code, defaulting to 'ch'
                division_attributes.append('e="ch"')
                if book_id:
                    book_no = self._get_book_number(book_id)
                else:
                    book_no = ''
                if book_no:
                    division_attributes.append(f'v="{book_no}"')
                page_ref = self._get_next_division_page(book_id, division_num) if book_id else None
                if page_ref is not None:
                    division_attributes.append(f'p="{page_ref}"')
                division_tag = ' '.join(division_attributes)
                converted_lines.append(f'<Division {division_tag}>')
                
                current_division = division_num
                i += 1
                continue
            
            # Detect markdown headings that actually contain paragraph numbers (e.g., ## 396\.)
            heading_match = re.match(r'^\s*(#{1,6})\s+(.*)$', line)
            if heading_match:
                heading_content = heading_match.group(2).strip()
                heading_para_match = re.match(r'^(\d+)\\?\.\s*(.*)$', heading_content)
                if heading_para_match:
                    para_num = heading_para_match.group(1)
                    para_text = heading_para_match.group(2).strip()

                    # Close any open paragraph before starting a new one
                    if in_paragraph:
                        converted_lines.append('</Paragraph>')
                        in_paragraph = False

                    # Always render these as centered paragraphs per requirement
                    paragraph_open = [f'<Paragraph number="{para_num}" type="center"']
                    if book_id:
                        paragraph_open.append(f'book="{book_id}"')
                    paragraph_open_str = ' '.join(paragraph_open) + '>'
                    converted_lines.append(paragraph_open_str)

                    # Make the paragraph text bold; fall back to showing the number if text missing
                    display_text = para_text if para_text else f'{para_num}.'
                    bold_text = f'**{display_text}**'
                    converted_lines.append(self.convert_emphasis_markdown(bold_text))
                    converted_lines.append('</Paragraph>')
                    i += 1
                    continue

            # Check for paragraph pattern 41\., 42\., etc.
            paragraph_match = re.match(r'^(\d+)\\?\.\s+(.*)$', line)
            if paragraph_match:
                para_num = paragraph_match.group(1)
                para_content = paragraph_match.group(2)
                
                # Close any previous open paragraph
                if in_paragraph:
                    converted_lines.append('</Paragraph>')
                
                # Collect full paragraph content for analysis
                full_para_content = para_content
                
                # Look ahead to collect multi-line paragraph content for verse detection
                j = i + 1
                temp_lines = [para_content]
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Stop if we hit another paragraph number or division
                    if re.match(r'^\d+\\?\.\s+', next_line) or re.match(r'^\(\d+\.\)$', next_line.strip()):
                        break
                    
                    # Stop if we hit separator
                    if next_line.strip() == '---':
                        break
                    
                    # Stop if we hit markdown links (close paragraph before links)
                    if re.match(r'^\s*\*\s+\[.*\]\(.*\)', next_line):
                        break
                    
                    # Stop if we hit empty line followed by something that should close paragraph
                    if next_line.strip() == '' and j + 1 < len(lines):
                        peek_line = lines[j + 1]
                        if (re.match(r'^\s*\*\s+\[.*\]\(.*\)', peek_line) or 
                            re.match(r'^\(\d+\.\)$', peek_line.strip()) or
                            re.match(r'^\d+\\?\.\s+', peek_line)):
                            break
                    
                    temp_lines.append(next_line)
                    j += 1
                
                full_para_content = '\n'.join(temp_lines)
                
                # Check if this paragraph contains niṭṭhito/niṭṭhitā/niṭṭhitaṃ or Namo formula or Tassuddānaṃ or ...pe... for center alignment
                # Only apply center alignment for paragraphs OUTSIDE of divisions
                should_center = False
                
                # Check if this paragraph content appears to be verses
                is_verses = self.is_verses_content(full_para_content)
                
                if current_division is None:
                    has_nitthita = re.search(r'\bniṭṭhito\b|\bniṭṭhitā\b|\bniṭṭhitaṃ\b', line)  # Check full line for Unicode characters
                    has_namo = line.strip() == "Namo tassa Bhagavato Arahato Sammāsambuddhassa." or \
                              para_content.strip() == "Namo tassa Bhagavato Arahato Sammāsambuddhassa."
                    has_tassuddana = re.search(r'\bTassuddānaṃ\b', line)
                    # Check for ...pe... pattern (ellipsis indicating omitted text)
                    has_pe = full_para_content.strip() == "…pe…" or full_para_content.strip() == "...pe..."
                    
                    # NEW CONDITIONS: Add additional criteria for centering
                    # 1. Not under division (already checked above)
                    # 2. Not verses content  
                    # 3. Content length not exceeding 80 characters
                    content_length = len(full_para_content.strip())
                    meets_new_criteria = not is_verses and content_length <= 80
                    
                    should_center = (has_nitthita or has_namo or has_tassuddana or has_pe) or meets_new_criteria

                # Start new paragraph with appropriate type
                paragraph_type = "normal"
                if should_center:
                    paragraph_type = "center"
                elif is_verses:
                    paragraph_type = "verses"
                
                if book_id:
                    if paragraph_type != "normal":
                        converted_lines.append(f'<Paragraph number="{para_num}" type="{paragraph_type}" book="{book_id}">')
                    else:
                        converted_lines.append(f'<Paragraph number="{para_num}" book="{book_id}">')
                else:
                    if paragraph_type != "normal":
                        converted_lines.append(f'<Paragraph number="{para_num}" type="{paragraph_type}">')
                    else:
                        converted_lines.append(f'<Paragraph number="{para_num}">')
                
                # Convert emphasis markdown in paragraph content
                converted_para_content = self.convert_emphasis_markdown(para_content)
                converted_lines.append(converted_para_content)
                in_paragraph = True
                
                # Add the collected multi-line content (also convert emphasis)
                k = i + 1
                while k < j:
                    line_content = self.convert_emphasis_markdown(lines[k])
                    converted_lines.append(line_content)
                    k += 1
                
                converted_lines.append('</Paragraph>')
                in_paragraph = False
                i = j
                continue
            
            # Check for lines outside Division that should be centered
            # Original conditions: niṭṭhito/niṭṭhitā/niṭṭhitaṃ or Namo formula or Tassuddānaṃ or ...pe...
            # New conditions: not verses content AND content length <= 80 characters
            if (current_division is None and line.strip()):
                # Check original centering conditions
                has_original_conditions = (
                    re.search(r'\bniṭṭhito\b|\bniṭṭhitā\b|\bniṭṭhitaṃ\b', line) or 
                    line.strip() == "Namo tassa Bhagavato Arahato Sammāsambuddhassa." or
                    re.search(r'\bTassuddānaṃ\b', line) or
                    line.strip() == "…pe…" or line.strip() == "...pe..."
                )
                
                # Check new centering conditions
                line_content = line.strip()
                is_single_line_verses = self.is_verses_content(line_content)
                content_length = len(line_content)
                has_new_conditions = not is_single_line_verses and content_length <= 80
                
                if has_original_conditions or has_new_conditions:
                    # Close any open paragraph first
                    if in_paragraph:
                        converted_lines.append('</Paragraph>')
                        in_paragraph = False
                    
                    # Wrap in Paragraph component with type="center"
                    if book_id:
                        converted_lines.append(f'<Paragraph type="center" book="{book_id}">')
                    else:
                        converted_lines.append('<Paragraph type="center">')
                    # Convert emphasis markdown in center paragraph content
                    converted_line = self.convert_emphasis_markdown(line)
                    converted_lines.append(converted_line)
                    converted_lines.append('</Paragraph>')
                    i += 1
                    continue
            
            # Regular line - convert emphasis and add as is
            converted_line = self.convert_emphasis_markdown(line)
            converted_lines.append(converted_line)
            i += 1
        
        # Close any remaining open paragraph
        if in_paragraph:
            converted_lines.append('</Paragraph>')
        
        # Close any remaining open division
        if current_division is not None:
            converted_lines.append('</Division>')
        
        final_content = '\n'.join(converted_lines)
        
        # If we found TOC, position it after Namo tassa... (maintaining traditional order)
        if has_toc:
            toc_component = self.wrap_toc_with_component(toc_lines, book_id, title)
            
            # Split content to find insertion point
            content_lines = final_content.split('\n')
            toc_inserted = False
            
            # Look for Namo tassa paragraph and insert TOC after it
            for i in range(len(content_lines)):
                line = content_lines[i].strip()
                
                # Look for line containing "Namo tassa"
                if 'Namo tassa' in line:
                    # Find the end of this paragraph component
                    j = i
                    while j < len(content_lines):
                        if content_lines[j].strip().endswith('</Paragraph>'):
                            # Insert TOC after this paragraph
                            content_lines.insert(j + 1, '')
                            content_lines.insert(j + 2, toc_component)
                            content_lines.insert(j + 3, '')
                            toc_inserted = True
                            break
                        j += 1
                    
                    if toc_inserted:
                        break
            
            if toc_inserted:
                final_content = '\n'.join(content_lines)
            else:
                # If no Namo tassa found, append TOC at the end
                final_content = final_content + '\n\n' + toc_component
        
        return imports, final_content
    
    def create_frontmatter(self, title: str, sidebar_order: int, references: list = None, basket: str = None, book_id: str = None) -> str:
        """Create Astro Starlight frontmatter"""
        lines = [
            "---",
            f'title: "{title}"',
            "tableOfContents: false",
            "sidebar:",
            f"  order: {sidebar_order}",
            'type: "tipitaka"',
        ]

        if basket:
            lines.append(f'basket: "{basket}"')

        if book_id:
            lines.append(f'book: "{book_id}"')

        if references:
            lines.append("references:")
            for ref in references:
                lines.append(f'  - "{ref}"')

        lines.append("---")
        lines.append("")

        return "\n".join(lines)
    
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

    def migrate_book_parallel(self, book_code: str, locale: str, show_progress: bool = False) -> tuple:
        """Thread-safe version of migrate_book that returns result"""
        try:
            start_time = time.time()
            
            # Source directory for this book
            source_book_dir = self.source_dir / book_code
            if not source_book_dir.exists():
                return (book_code, locale, False, f"Directory not found: {source_book_dir}")

            book_abbreviation = self.book_mappings.get(book_code, {}).get('abbrev')
            if book_abbreviation:
                self._reset_page_tracking(book_abbreviation)
            
            # Migrate the main .md file first
            main_file = self.source_dir / f"{book_code}.md"
            if main_file.exists():
                self.migrate_file(main_file, book_code, '', locale, 1)
            
            # Migrate the book directory
            self.migrate_directory(source_book_dir, book_code, '', locale)
            
            elapsed = time.time() - start_time
            return (book_code, locale, True, f"Completed in {elapsed:.2f}s")
            
        except Exception as e:
            return (book_code, locale, False, f"Error: {str(e)}")
    
    def migrate_locale_parallel(self, locale: str, target_books: Optional[List[str]] = None, 
                               show_progress: bool = False) -> dict:
        """Process all books for a locale using threading"""
        print(f"\nProcessing locale: {locale}")
        
        # Get books to process
        if target_books is None:
            all_books = self.get_available_books()
        else:
            all_books = target_books
        
        # Initialize progress tracking
        with self._progress_lock:
            self._start_time = time.time()
            self._processed_files = 0
            self._total_files = self._estimate_total_files(all_books)
            self._progress_stats[locale] = {
                'started': time.time(),
                'total_files': self._total_files,
                'processed': 0
            }
            
        # Sort books for consistent processing order
        def sort_key(book_code):
            import re
            match = re.match(r'(\d+)', book_code)
            return int(match.group(1)) if match else 999
        
        sorted_books = sorted(list(set(all_books)), key=sort_key)
        
        results = {
            'locale': locale,
            'total_books': len(sorted_books),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'start_time': time.time()
        }
        
        # Use ThreadPoolExecutor for books within a locale
        max_threads = min(self.max_workers // 2, len(sorted_books))  # Leave resources for other locales
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Submit all book migration tasks
            future_to_book = {
                executor.submit(self.migrate_book_parallel, book_code, locale, show_progress): book_code 
                for book_code in sorted_books
            }
            
            # Process completed tasks
            for future in concurrent.futures.as_completed(future_to_book):
                book_code, locale_result, success, message = future.result()
                
                if success:
                    results['successful'] += 1
                    if show_progress:
                        print(f"  ✓ {book_code}: {message}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{book_code}: {message}")
                    if show_progress:
                        print(f"  ✗ {book_code}: {message}")
        
        results['end_time'] = time.time()
        results['total_time'] = results['end_time'] - results['start_time']
        
        # Flush any remaining batch writes for this locale
        self._flush_batch_writes(locale)
        
        # Update progress stats
        with self._progress_lock:
            if locale in self._progress_stats:
                self._progress_stats[locale]['completed'] = time.time()
                print(f"Completed {locale}: {self._progress_stats[locale]['processed']}/{self._progress_stats[locale]['total_files']} files")
        
        return results

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
        """Migrate a single file with improved safety and MDX component conversion"""
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
            
            # Check for 0.md file in the book directory and extract Namo formula
            namo_content = self.get_namo_formula(book_code, locale)
            if namo_content:
                # Add Namo formula at the beginning of content
                if cleaned_content:
                    cleaned_content = namo_content + "\n\n" + cleaned_content
                else:
                    cleaned_content = namo_content
                    
        else:
            # Replace dots with dashes in filenames และแปลง -- เป็น –
            safe_stem = source_file.stem.lower().replace('.', '-')
            safe_stem = re.sub(r'(\d+)--(\d+)', r'\1–\2', safe_stem)
            target_file = target_path / f"{safe_stem}.mdx"
        
        # Convert to MDX with components if content has divisions/paragraphs
        book_id = self.extract_book_id_from_path(target_file)
        component_imports = ""
        
        # Get book abbreviation for frontmatter
        book_abbreviation = None
        if book_id and book_id in self.book_mappings:
            book_abbreviation = self.book_mappings[book_id]['abbrev']
        
        # Check if content needs component conversion (has division/paragraph patterns or TOC)
        has_divisions = re.search(r'^\(\d+(?:(?:--|–)\d+)?\.\)$', cleaned_content, re.MULTILINE)
        has_paragraphs = re.search(r'^\d+\\?\.\s+', cleaned_content, re.MULTILINE)
        has_toc, _, _ = self.detect_table_of_contents(cleaned_content)
        
        if has_divisions or has_paragraphs or has_toc:
            component_imports, cleaned_content = self.convert_to_mdx_with_components(cleaned_content, book_abbreviation, title)
        
        # Create content with frontmatter
        frontmatter = self.create_frontmatter(title, sidebar_order, None, basket, book_abbreviation)
        
        # Add DynamicBreadcrumb for non-index and non-0 files
        breadcrumb_content = ""
        file_stem = target_file.stem
        if file_stem != "index" and file_stem != "0":
            breadcrumb_content = """import DynamicBreadcrumb from '@components/DynamicBreadcrumb.astro';

<DynamicBreadcrumb />

"""
        
        # Combine all content parts
        final_content = frontmatter + component_imports + breadcrumb_content + cleaned_content
        
        # Store original content for validation
        original_content = content
        
        # Validate migration result  
        if not self._validate_migration_result(source_file, target_file, original_content, 
                                               final_content, locale):
            self.logger.warning(f"Migration validation failed for {source_file}")
        
        # Use batch file writing for better performance
        self._batch_write_file(target_file, final_content, locale)
        
        # Update progress
        self._update_progress()
    
    def migrate_directory(self, source_dir: Path, book_code: str, relative_path: str = '', locale: str = 'romn'):
        """Recursively migrate a directory"""
        if not source_dir.exists():
            return
            
        sidebar_order = 1
        
        entries = self._sort_directory_entries(source_dir, book_code)

        # Process files in current directory
        for item in entries:
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

        book_abbreviation = None
        if book_code in self.book_mappings:
            book_abbreviation = self.book_mappings[book_code].get('abbrev')
            if book_abbreviation:
                self._reset_page_tracking(book_abbreviation)
            
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
    
    def migrate_all(self, target_locales=None, target_books=None):
        """Migrate all content for specified locales with improved error handling
        
        Args:
            target_locales: List of locale codes to migrate (default: all locales)
            target_books: List of book codes to migrate (default: all books)
        """
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
        
        # Validate books if specified
        if target_books is not None:
            if isinstance(target_books, str):
                target_books = [target_books]
            
            valid_books, invalid_books = self.validate_books(target_books)
            if invalid_books:
                print(f"Error: Invalid book(s): {', '.join(invalid_books)}")
                print(f"Valid books: {', '.join(self.get_available_books())}")
                return
            
            target_books = valid_books
        
        print("Starting Tipitaka content migration...")
        print(f"Target locales: {', '.join(target_locales)}")
        if target_books:
            print(f"Target books: {', '.join(target_books)}")
        
        # Add basic error handling for directory operations
        try:
            print("Setting up target locale directories...")
            for locale in target_locales:
                locale_dir = self.target_dir / locale
                # Create directory only if it doesn't exist (preserve existing content)
                locale_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error setting up directories: {e}")
            return  # Exit gracefully like original behavior
        
        # Collect all books and sort them properly
        all_books = self._collect_all_books(self.structure)
        
        # Filter books if target_books is specified
        if target_books:
            all_books = [book for book in all_books if book in target_books]
        
        # Sort books by their numeric order for proper processing sequence
        def sort_key(book_code):
            # Extract numeric part for sorting (e.g., '1V' -> 1, '12S1' -> 12, etc.)
            import re
            match = re.match(r'(\d+)', book_code)
            return int(match.group(1)) if match else 999
        
        sorted_books = sorted(list(set(all_books)), key=sort_key)
        
        # Start parallel migration
        start_time = time.time()
        
        print(f"\n🚀 Parallel Migration Starting")
        print(f"📚 Books: {len(sorted_books)} ({', '.join(sorted_books)})")
        print(f"🌍 Locales: {len(target_locales)} ({', '.join(target_locales)})")
        print(f"⚡ CPU cores: {os.cpu_count()}, Workers: {self.max_workers}")
        print(f"{'='*60}")
        
        # Use ProcessPoolExecutor for locales (true parallelism)
        max_processes = min(len(target_locales), os.cpu_count() or 1)
        
        all_results = []
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_processes) as executor:
            # Submit locale processing tasks
            future_to_locale = {
                executor.submit(migrate_locale_worker, str(self.source_dir), str(self.target_dir), 
                               locale, sorted_books, self.locales, self.max_workers): locale 
                for locale in target_locales
            }
            
            # Process completed locales
            for future in concurrent.futures.as_completed(future_to_locale):
                try:
                    result = future.result()
                    all_results.append(result)
                    
                    # Print summary for this locale
                    locale = result['locale']
                    print(f"✅ {locale}: {result['successful']}/{result['total_books']} books "
                          f"({result['total_time']:.1f}s)")
                    
                    if result['errors']:
                        print(f"   ⚠️  {len(result['errors'])} errors:")
                        for error in result['errors'][:3]:  # Show first 3 errors
                            print(f"      • {error}")
                        if len(result['errors']) > 3:
                            print(f"      ... and {len(result['errors']) - 3} more")
                            
                except Exception as e:
                    locale = future_to_locale[future]
                    print(f"❌ {locale}: Process failed - {e}")
        
        # Always try to create navigator.js
        try:
            print("\n📋 Creating navigator.js...")
            self.create_navigator_js()
            print("✅ Navigator.js created successfully")
        except Exception as e:
            print(f"❌ Error creating navigator.js: {e}")
        
        # Final summary
        total_time = time.time() - start_time
        total_books_processed = sum(r['successful'] for r in all_results)
        total_books_failed = sum(r['failed'] for r in all_results)
        
        print(f"\n{'='*60}")
        print(f"🎉 Migration Complete!")
        print(f"📊 Summary:")
        print(f"   • Total time: {total_time:.1f}s")
        print(f"   • Locales processed: {len(all_results)}")
        print(f"   • Books successful: {total_books_processed}")
        print(f"   • Books failed: {total_books_failed}")
        
        if total_books_processed > 0:
            avg_time = total_time / total_books_processed
            print(f"   • Average time per book: {avg_time:.2f}s")
            books_per_minute = (total_books_processed / total_time) * 60
            print(f"   • Processing rate: {books_per_minute:.1f} books/minute")
        
        print(f"{'='*60}")

# Worker function for multiprocessing (must be at module level)
def migrate_locale_worker(source_dir, target_dir, locale, target_books, available_locales, max_workers):
    """Worker function to migrate a locale - must be at module level for multiprocessing"""
    # Create a new migrator instance for this process
    migrator = TipitakaMigrator(str(source_dir), str(target_dir))
    migrator.max_workers = max_workers
    
    # Process this locale
    return migrator.migrate_locale_parallel(locale, target_books, show_progress=True)

def main():
    """Main function with improved argument parsing"""
    import sys
    import argparse
    
    # Set up paths
    script_dir = Path(__file__).parent
    source_dir = script_dir / 'tipitaka'
    target_dir = script_dir.parent.parent / 'src' / 'content' / 'docs'
    
    # Create migrator
    migrator = TipitakaMigrator(str(source_dir), str(target_dir))
    
    # Check if arguments contain --book or --section (new format)
    # OR if first argument starts with -- (no locale specified)
    has_new_format = any(arg.startswith('--') for arg in sys.argv[1:])
    
    if has_new_format or (len(sys.argv) > 1 and sys.argv[1].startswith('--')):
        # Use argparse for new format
        parser = argparse.ArgumentParser(
            description='Migrate Tipitaka content to Starlight structure',
            epilog=f"""
Examples:
  python {sys.argv[0]}                        # Migrate all locales (all books)
  python {sys.argv[0]} --book 1V              # Migrate all locales, book 1V only
  python {sys.argv[0]} --book 1V,2V           # Migrate all locales, books 1V and 2V  
  python {sys.argv[0]} --section vi           # Migrate all locales, Vinaya section only
  python {sys.argv[0]} romn                   # Migrate romn locale (all books)
  python {sys.argv[0]} romn --book 1V         # Migrate romn locale, book 1V only
  python {sys.argv[0]} thai sinh              # Migrate thai and sinh locales (all books)

Available locales: {', '.join(migrator.locales)}
Available books: {', '.join(migrator.get_available_books())}
Available sections: {', '.join(migrator.get_available_sections())}
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        parser.add_argument('locales', nargs='*', 
                          help='Locale codes to migrate (default: all locales)')
        parser.add_argument('--book', '--books', 
                          help='Comma-separated list of book codes to migrate (e.g., 1V,2V)')
        parser.add_argument('--section', 
                          help='Section to migrate: vi (Vinaya), su (Sutta), or ab (Abhidhamma)')
        
        args = parser.parse_args()
        
        # Process arguments
        target_locales = args.locales if args.locales else None
        target_books = None
        
        # Handle book selection
        if args.book:
            target_books = [book.strip() for book in args.book.split(',')]
        elif args.section:
            if args.section not in migrator.get_available_sections():
                print(f"Error: Invalid section '{args.section}'")
                print(f"Valid sections: {', '.join(migrator.get_available_sections())}")
                return
            target_books = migrator.filter_books_by_section(args.section)
        
        # Validate locales if provided
        if target_locales:
            invalid_locales = [loc for loc in target_locales if loc not in migrator.locales]
            if invalid_locales:
                print(f"Error: Invalid locale(s): {', '.join(invalid_locales)}")
                print(f"Valid locales: {', '.join(migrator.locales)}")
                return
        
        # Run migration
        migrator.migrate_all(target_locales, target_books)
        
    else:
        # Backward compatibility: old format (locales only)
        if len(sys.argv) > 1:
            # Get specified locales from command line
            target_locales = sys.argv[1:]
            
            # Validate all provided locales
            invalid_locales = [loc for loc in target_locales if loc not in migrator.locales]
            if invalid_locales:
                print(f"Error: Invalid locale(s): {', '.join(invalid_locales)}")
                print(f"Valid locales: {', '.join(migrator.locales)}")
                print(f"Usage: python {sys.argv[0]} [locale1] [locale2] ...")
                print(f"       python {sys.argv[0]} [locale] --book [book1,book2] ...")
                print(f"       python {sys.argv[0]} [locale] --section [vi|su|ab]")
                print(f"Example: python {sys.argv[0]} mymr")
                print(f"Example: python {sys.argv[0]} thai sinh")
                print(f"Example: python {sys.argv[0]} romn --book 1V,2V")
                print(f"Example: python {sys.argv[0]} romn --section vi")
                print(f"Example: python {sys.argv[0]}  # (migrates all locales)")
                return
            
            migrator.migrate_all(target_locales)
        else:
            # No arguments provided, migrate all locales
            migrator.migrate_all()

"""
CHANGELOG - URL Fix Updates

2025-09-26: Fixed internal link URL generation issue
- Problem: Book code prefixes (like 29dhs/, 6d/, 12s1/) were appearing in internal links,
  creating incorrect URLs like /romn/tipitaka/ab/dhs/29dhs/1 instead of /romn/tipitaka/ab/dhs/1
- Solution: Enhanced fix_link() function in _safe_read_file() to remove book_code prefixes
- Changes made:
  1. Updated regex patterns in fix_link() to handle case-insensitive book codes:
     - r'^(\d+[A-Za-z]+\d*)\/' for patterns like 29Dhs/, 12S1/
     - r'^(\d+[A-Za-z]+)\/' for patterns like 6D/, 29Dhs/  
     - r'^([A-Za-z]+\d*)\/' for patterns like Dhs/, S1/
  2. Disabled clean_content() function call to prevent double processing of links
  3. Ensured link processing occurs before transliteration to preserve fixed URLs
- Testing: Verified with DHS book - URLs now generate as (1), (2) instead of (29dhs/1), (29dhs/2)
- Backup: Code saved as migrate_tipitaka_bk.py before modifications
- Impact: All internal links now generate correct nested URLs without book code prefixes
"""

if __name__ == "__main__":
    main()
