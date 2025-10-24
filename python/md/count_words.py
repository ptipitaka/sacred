#!/usr/bin/env python3
import os
import re
from pathlib import Path
from collections import defaultdict

# This data is copied from migrate_tipitaka.py
book_mappings = {
    # Vinayapiṭaka (vi)
    '1V': {'abbrev': 'para', 'name': 'Pārājikapāḷi', 'references': ['1V', 'vi-para', 'para']},
    '2V': {'abbrev': 'paci', 'name': 'Pācittiyapāḷi', 'references': ['2V', 'vi-paci', 'paci']},
    '3V': {'abbrev': 'vi-maha', 'name': 'Mahāvaggapāḷi', 'references': ['3V', 'vi-maha', 'maha']},
    '4V': {'abbrev': 'cula', 'name': 'Cūḷavaggapāḷi', 'references': ['4V', 'vi-cula', 'cula']},
    '5V': {'abbrev': 'pari', 'name': 'Parivārapāḷi', 'references': ['5V', 'vi-pari', 'pari']},
    
    # Dīghanikāya (dn)
    '6D': {'abbrev': 'sila', 'name': 'Sīlakkhandhavaggapāḷi', 'references': ['6D', 'dn-sila', 'sila']},
    '7D': {'abbrev': 'dn-maha', 'name': 'Mahāvaggapāḷi', 'references': ['7D', 'dn-maha', 'maha']},
    '8D': {'abbrev': 'pthi', 'name': 'Pāthikavaggapāḷi', 'references': ['8D', 'dn-pthi', 'pthi']},
    
    # Majjhimanikāya (mn)
    '9M': {'abbrev': 'mula', 'name': 'Mūlapaṇṇāsapāḷi', 'references': ['9M', 'mn-mula', 'mula']},
    '10M': {'abbrev': 'majj', 'name': 'Majjhimapaṇṇāsapāḷi', 'references': ['10M', 'mn-majj', 'majj']},
    '11M': {'abbrev': 'upar', 'name': 'Uparipaṇṇāsapāḷi', 'references': ['11M', 'mn-upar', 'upar']},
    
    # Saṃyuttanikāya (sn)
    '12S1': {'abbrev': 'saga', 'name': 'Sagāthāvaggasaṃyuttapāḷi', 'references': ['12S1', 'sn-saga', 'saga']},
    '12S2': {'abbrev': 'nida', 'name': 'Nidānavaggasaṃyuttapāḷi', 'references': ['12S2', 'sn-nida', 'nida']},
    '13S3': {'abbrev': 'khan', 'name': 'Khandhavaggasaṃyuttapāḷi', 'references': ['13S3', 'sn-khan', 'khan']},
    '13S4': {'abbrev': 'sala', 'name': 'Saḷāyatanavaggasaṃyuttapāḷi', 'references': ['13S4', 'sn-sala', 'sala']},
    '14S5': {'abbrev': 'sn-maha', 'name': 'Mahāvaggasaṃyuttapāḷi', 'references': ['14S5', 'sn-maha', 'maha']},
    
    # Aṅguttaranikāya (an)
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
    '29Dhs': {'abbrev': 'dhs', 'name': 'Dhammasaṅgaṇīpāḷi', 'references': ['29Dhs', 'ab-dhs', 'dhs']},
    '30Vbh': {'abbrev': 'vbh', 'name': 'Vibhaṅgapāḷi', 'references': ['30Vbh', 'ab-vbh', 'vbh']},
    '31Dht': {'abbrev': 'dht', 'name': 'Dhātukathāpāḷi', 'references': ['31Dht', 'ab-dht', 'dht']},
    '31Pu': {'abbrev': 'pu', 'name': 'Puggalapaññattipāḷi', 'references': ['31Pu', 'ab-pu', 'pu']},
    '32Kv': {'abbrev': 'kv', 'name': 'Kathāvatthupāḷi', 'references': ['32Kv', 'ab-kv', 'kv']},
    
    # Yamaka (ab/yk)
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
    '36P1': {'abbrev': 'p1-1', 'name': 'Tikapaṭṭhānapāḷi 1', 'references': ['36P1', 'pt-anu-tika-1', 'p1.1']},
    '37P1': {'abbrev': 'p1-2', 'name': 'Tikapaṭṭhānapāḷi 2', 'references': ['37P1', 'pt-anu-tika-2', 'p1.2']},
    '38P2': {'abbrev': 'p2', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['38P2', 'pt-anu-duka', 'p2']},
    '39P3': {'abbrev': 'p3', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['39P3', 'pt-anu-dukatika', 'p3']},
    '39P4': {'abbrev': 'p4', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['39P4', 'pt-anu-tikaduka', 'p4']},
    '39P5': {'abbrev': 'p5', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['39P5', 'pt-anu-tikatika', 'p5']},
    '39P6': {'abbrev': 'p6', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['39P6', 'pt-anu-dukaduka', 'p6']},
    
    # Paṭṭhāna - Dhammapaccanīya
    '40P7': {'abbrev': 'p7', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P7', 'pt-pac-tika', 'p7']},
    '40P8': {'abbrev': 'p8', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P8', 'pt-pac-duka', 'p8']},
    '40P9': {'abbrev': 'p9', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P9', 'pt-pac-dukatika', 'p9']},
    '40P10': {'abbrev': 'p10', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P10', 'pt-pac-tikaduka', 'p10']},
    '40P11': {'abbrev': 'p11', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P11', 'pt-pac-tikatika', 'p11']},
    '40P12': {'abbrev': 'p12', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P12', 'pt-pac-dukaduka', 'p12']},
    
    # Paṭṭhāna - Dhammānulomapaccanīya
    '40P13': {'abbrev': 'p13', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P13', 'pt-anupac-tika', 'p13']},
    '40P14': {'abbrev': 'p14', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P14', 'pt-anupac-duka', 'p14']},
    '40P15': {'abbrev': 'p15', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P15', 'pt-anupac-dukatika', 'p15']},
    '40P16': {'abbrev': 'p16', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P16', 'pt-anupac-tikaduka', 'p16']},
    '40P17': {'abbrev': 'p17', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P17', 'pt-anupac-tikatika', 'p17']},
    '40P18': {'abbrev': 'p18', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P18', 'pt-anupac-dukaduka', 'p18']},
    
    # Paṭṭhāna - Dhammapaccanīyānuloma
    '40P19': {'abbrev': 'p19', 'name': 'Tikapaṭṭhānapāḷi', 'references': ['40P19', 'pt-pacanu-tika', 'p19']},
    '40P20': {'abbrev': 'p20', 'name': 'Dukapaṭṭhānapāḷi', 'references': ['40P20', 'pt-pacanu-duka', 'p20']},
    '40P21': {'abbrev': 'p21', 'name': 'Dukatikapaṭṭhānapāḷi', 'references': ['40P21', 'pt-pacanu-dukatika', 'p21']},
    '40P22': {'abbrev': 'p22', 'name': 'Tikadukapaṭṭhānapāḷi', 'references': ['40P22', 'pt-pacanu-tikaduka', 'p22']},
    '40P23': {'abbrev': 'p23', 'name': 'Tikatikapaṭṭhānapāḷi', 'references': ['40P23', 'pt-pacanu-tikatika', 'p23']},
    '40P24': {'abbrev': 'p24', 'name': 'Dukadukapaṭṭhānapāḷi', 'references': ['40P24', 'pt-pacanu-dukaduka', 'p24']},
}

structure = {
    'tipitaka': {
        'vi': {
            'books': ['1V', '2V', '3V', '4V', '5V']
        },
        'su': {
            'dn': {
                'books': ['6D', '7D', '8D']
            },
            'mn': {
                'books': ['9M', '10M', '11M']
            },
            'sn': {
                'books': ['12S1', '12S2', '13S3', '13S4', '14S5']
            },
            'an': {
                'books': ['15A1', '15A2', '15A3', '15A4', '16A5', '16A6', '16A7', '17A8', '17A9', '17A10', '17A11']
            },
            'kn': {
                'books': ['18Kh', '18Dh', '18Ud', '18It', '18Sn', '19Vv', '19Pv', '19Th1', '19Th2', 
                         '20Ap1', '20Ap2', '21Bu', '21Cp', '22J', '23J', '24Mn', '25Cn', '26Ps', '27Ne', '27Pe', '28Mi']
            }
        },
        'ab': {
            'books': ['29Dhs', '30Vbh', '31Dht', '31Pu', '32Kv'],
            'yk': {
                'books': ['33Y1', '33Y2', '33Y3', '33Y4', '33Y5', '34Y6', '34Y7', '34Y8', '35Y9', '35Y10']
            },
            'pt': {
                'anu': {
                    'books': ['36P1', '37P1', '38P2', '39P3', '39P4', '39P5', '39P6']
                },
                'pac': {
                    'books': ['40P7', '40P8', '40P9', '40P10', '40P11', '40P12']
                },
                'anupac': {
                    'books': ['40P13', '40P14', '40P15', '40P16', '40P17', '40P18']
                },
                'pacanu': {
                    'books': ['40P19', '40P20', '40P21', '40P22', '40P23', '40P24']
                }
            }
        }
    }
}


def count_words(content: str) -> int:
    """Counts words in content after removing frontmatter and tags."""
    content = re.sub(r'---.*?---', '', content, flags=re.DOTALL)
    content = re.sub(r'<.*?>', '', content, flags=re.DOTALL)
    content = re.sub(r'[#*\[\]\(\)`_]', '', content)
    words = content.split()
    return len(words)

def analyze_word_counts(target_dir: Path, locale: str = 'romn'):
    """Analyzes and displays word counts for each book."""
    
    path_to_book_map = {}
    
    def build_path_map(struct, path_prefix):
        for key, data in struct.items():
            if key == 'books':
                for book_code in data:
                    if book_code in book_mappings:
                        abbrev = book_mappings[book_code]['abbrev']
                        full_path = f"{path_prefix}/{abbrev}".strip('/')
                        path_to_book_map[full_path] = book_code
            elif isinstance(data, dict):
                build_path_map(data, f"{path_prefix}/{key}".strip('/'))

    build_path_map(structure, '')

    results = defaultdict(lambda: {'file_count': 0, 'word_count': 0})
    locale_path = target_dir / locale
    if not locale_path.exists():
        print(f"Directory not found: {locale_path}")
        return None

    all_mdx_files = list(locale_path.rglob('*.mdx'))
    if not all_mdx_files:
        print(f"No .mdx files found in {locale_path}")
        return None

    # Sort keys by length, descending, to match most specific path first
    sorted_paths = sorted(path_to_book_map.keys(), key=len, reverse=True)

    for mdx_file in all_mdx_files:
        try:
            relative_dir_str = os.path.normpath(mdx_file.parent.relative_to(locale_path).as_posix()).replace('\\', '/')
            
            book_code = None
            for path_prefix in sorted_paths:
                if relative_dir_str.startswith(path_prefix):
                    book_code = path_to_book_map[path_prefix]
                    break
            
            if book_code:
                content = mdx_file.read_text('utf-8')
                word_count = count_words(content)
                results[book_code]['file_count'] += 1
                results[book_code]['word_count'] += word_count
        except Exception as e:
            print(f"Could not process {mdx_file}: {e}")

    return results

def print_results(results):
    """Prints the word count results in a structured format."""
    
    total_files = 0
    total_words = 0

    print("สรุปจำนวนไฟล์และจำนวนคำในแต่ละเล่ม (จากไฟล์ .mdx)")
    print("="*60)

    def process_level(level_structure, level_name, indent=""):
        nonlocal total_files, total_words
        
        level_total_files = 0
        level_total_words = 0
        
        print(f"\n{indent}### {level_name} ###")
        
        books_in_level = level_structure.get('books', [])
        sorted_books = sorted(books_in_level, key=lambda x: (int(re.search(r'\d+', x).group()), x))

        for book_code in sorted_books:
            if book_code in results:
                info = results[book_code]
                book_name = book_mappings[book_code]['name']
                print(f"{indent}- {book_name} ({book_code}): {info['file_count']:,} ไฟล์, {info['word_count']:,} คำ")
                level_total_files += info['file_count']
                level_total_words += info['word_count']

        sub_level_total_files = 0
        sub_level_total_words = 0
        for sub_level_key, sub_level_data in level_structure.items():
            if sub_level_key != 'books' and isinstance(sub_level_data, dict):
                sub_name_map = {'dn': 'ทีฆนิกาย', 'mn': 'มัชฌิมนิกาย', 'sn': 'สังยุตตนิกาย', 'an': 'อังคุตตรนิกาย', 'kn': 'ขุททกนิกาย', 'yk': 'ยมก', 'pt': 'ปัฏฐาน', 'anu': 'ธัมมานุโลม', 'pac': 'ธัมมปัจจนีย', 'anupac': 'ธัมมานุโลมปัจจนีย', 'pacanu': 'ธัมมปัจจนียานุโลม'}
                sub_level_name = sub_name_map.get(sub_level_key, sub_level_key.capitalize())
                
                sub_files, sub_words = process_level(sub_level_data, sub_level_name, indent + "  ")
                sub_level_total_files += sub_files
                sub_level_total_words += sub_words

        level_total_files += sub_level_total_files
        level_total_words += sub_level_total_words

        if level_total_files > 0:
            print(f"{indent}  รวม {level_name}: {level_total_files:,} ไฟล์, {level_total_words:,} คำ")
        
        total_files += level_total_files
        total_words += level_total_words
        return level_total_files, level_total_words

    process_level(structure['tipitaka']['vi'], "พระวินัยปิฎก")
    process_level(structure['tipitaka']['su'], "พระสุตตันตปิฎก")
    process_level(structure['tipitaka']['ab'], "พระอภิธรรมปิฎก")
    
    print("\n" + "="*60)
    # The total is double-counted due to recursion, so we divide by 2
    print(f"สรุปรวมทั้งหมด: {total_files // 2:,} ไฟล์, {total_words // 2:,} คำ")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    target_dir = project_root / 'src' / 'content' / 'docs'
    
    print(f"Analyzing files in: {target_dir}")
    word_count_results = analyze_word_counts(target_dir, 'mymr')
    
    if word_count_results:
        print_results(word_count_results)
    else:
        print("ไม่พบข้อมูลไฟล์ .mdx ที่จะทำการนับ")
        print(f"กรุณาตรวจสอบว่ามีไฟล์อยู่ใน: {target_dir / 'romn'}")
