/**
 * Pali Text Wrapper Utility
 * ฟังก์ชันสำหรับจัดการข้อความภาษาบาลี เพื่อป้องกันการตัดคำกลางคำ
 * โดยห่อแต่ละคำด้วย span และใช้ flexbox layout
 */

/**
 * แปลงข้อความบาลีเป็น HTML ที่ไม่ตัดคำกลางคำ
 * @param {string} text - ข้อความภาษาบาลี
 * @param {Object} options - ตัวเลือกการจัดรูปแบบ
 * @returns {string} HTML ที่จัดรูปแบบแล้ว
 */
export function wrapPaliText(text, options = {}) {
    const {
        containerClass = 'pali-container',
        paragraphClass = 'pali-paragraph', 
        wordClass = 'pali-word',
        splitParagraphs = true
    } = options;

    if (!text || typeof text !== 'string') {
        return '';
    }

    // แยกย่อหน้า (ถ้าต้องการ)
    const paragraphs = splitParagraphs ? 
        text.split(/\n\s*\n/).filter(p => p.trim()) : 
        [text];

    const wrappedParagraphs = paragraphs.map((paragraph, index) => {
        // แยกคำด้วยช่องว่าง
        const words = paragraph.trim().split(/\s+/).filter(word => word);
        
        // ห่อแต่ละคำด้วย span
        const wrappedWords = words.map(word => 
            `<span class="${wordClass}">${escapeHtml(word)}</span>`
        ).join(' ');

        return `<div class="${paragraphClass}">${wrappedWords}</div>`;
    });

    return `<div class="${containerClass}">${wrappedParagraphs.join('')}</div>`;
}

/**
 * Escape HTML characters เพื่อความปลอดภัย
 * @param {string} text 
 * @returns {string}
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * สร้าง CSS สำหรับ Pali text (สำหรับใช้ใน JavaScript)
 * @returns {string} CSS rules
 */
export function getPaliCSS() {
    return `
        .pali-container {
            line-height: 1.8;
        }
        
        .pali-paragraph {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin-bottom: 1em;
            padding-left: 2em;
        }
        
        .pali-paragraph:first-child {
            padding-left: 0;
        }
        
        .pali-word {
            white-space: nowrap;
            margin-right: 0.25em;
            display: inline-block;
        }
        
        .pali-word:last-child {
            margin-right: 0;
        }
        
        /* สำหรับ responsive */
        @media (max-width: 768px) {
            .pali-paragraph {
                padding-left: 1em;
                justify-content: flex-start;
            }
        }
    `;
}

/**
 * ฟังก์ชันสำหรับใช้กับ DOM elements ที่มีอยู่แล้ว
 * @param {string} selector - CSS selector
 * @param {Object} options - ตัวเลือก
 */
export function initializePaliElements(selector = '.pali-text', options = {}) {
    const elements = document.querySelectorAll(selector);
    
    elements.forEach(element => {
        const originalText = element.textContent || element.innerText;
        const wrappedHTML = wrapPaliText(originalText, options);
        element.innerHTML = wrappedHTML;
        
        // เพิ่ม CSS class ถ้ายังไม่มี
        if (!element.classList.contains('pali-container')) {
            element.classList.add('pali-container');
        }
    });
}

/**
 * ตัวอย่างการใช้งาน
 */

/*
// ใน HTML:
<div class="pali-text">
เตน สมเยน พุทฺโธ ภควา สาวตฺถิยํ วิหรติ เชตวเน อนาถปิณฺฑิกสฺส อาราเม

เตน โข ปน สมเยน ปาริวาสิกา ภิกฺขู สาทิยนฺติ ปกตตฺตานํ ภิกฺขูนํ อภิวาทนํ
</div>

// ใน JavaScript:
import { initializePaliElements, getPaliCSS } from './pali-text-wrapper.js';

// เพิ่ม CSS
const style = document.createElement('style');
style.textContent = getPaliCSS();
document.head.appendChild(style);

// แปลงข้อความบาลีทั้งหมดในหน้า
initializePaliElements('.pali-text');

// หรือแปลงข้อความเฉพาะ
const paliText = "เตน สมเยน พุทฺโธ ภควา สาวตฺถิยํ วิหรติ";
const wrappedHTML = wrapPaliText(paliText);
document.getElementById('content').innerHTML = wrappedHTML;
*/