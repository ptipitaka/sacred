// @ts-nocheck
/**
 * Simple Vanilla JavaScript Flipbook Viewer for Tipitaka
 * Fixed version with proper odd/even page layout
 */

class BookViewer {
    constructor() {
        /** @type {string|null} */
        this.currentVolume = null;
        
        /** @type {string|null} */
        this.currentEdition = null; // Required parameter, no default
        
        /** @type {number} */
        this.totalPages = 0;
        
        /** @type {number} */
        this.currentPageIndex = 0; // 0-based index
        
        /** @type {Array<{number: number, path: string}>} */
        this.pages = [];
        
        /** @type {Array<{id: string, name: string, folder: string}>} */
        this.volumes = this.generateVolumeList();
        
        /** @type {Map<string, number>} */
        this.pageCounts = new Map(); // Cache สำหรับจำนวนหน้าของแต่ละ volume
        
        /** @type {boolean} */
        this.isLoadingFromURL = false; // Flag เพื่อป้องกัน URL update ระหว่างโหลดจาก URL
        
        this.init();
    }

    generateVolumeList() {
        const volumes = [];
        for (let i = 1; i <= 40; i++) {
            // ใช้ตัวเลขธรรมดาทุกเล่ม ไม่มี zero padding
            const volumeId = i.toString();
            volumes.push({
                id: volumeId,
                name: `${i}`,
                folder: volumeId
            });
        }
        return volumes;
    }

    // ฟังก์ชันสำหรับทำให้ volume ID เป็นมาตรฐาน
    normalizeVolumeId(volume) {
        if (!volume) return null;
        
        const num = parseInt(volume);
        if (isNaN(num) || num < 1 || num > 40) return null;
        
        // ใช้ตัวเลขธรรมดาไม่มี zero padding เพราะโฟลเดอร์ใช้ชื่อ 9 ไม่ใช่ 09
        return num.toString();
    }

    // ฟังก์ชันสำหรับทำให้ edition เป็นมาตรฐาน
    normalizeEdition(edition) {
        if (!edition) return null; // ไม่มี default, ต้องใส่
        
        const ed = edition.toLowerCase().trim();
        
        // รองรับ editions ที่มีอยู่
        const validEditions = ['ch', 'mc'];
        
        if (validEditions.includes(ed)) {
            return ed;
        }
        
        // ถ้าไม่ใช่ edition ที่รองรับ ให้คืน null
        console.warn(`Invalid edition: ${edition}`);
        return null;
    }

    // แสดงข้อความเตือนเมื่อไม่มี edition
    showEditionRequired() {
        const container = document.querySelector('.container');
        if (container) {
            container.innerHTML = `
                <div class="header">
                    <h1>Book Viewer</h1>
                </div>
                <div style="text-align: center; padding: 40px; background: #f9f9f9; border-radius: 8px; margin: 20px;">
                    <h2 style="color: #d32f2f; margin-bottom: 20px;">⚠️ Edition Parameter Required</h2>
                    <p style="font-size: 1.1rem; margin-bottom: 20px;">กรุณาระบุ edition ใน URL parameter:</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                        <h3 style="color: #1976d2; margin-bottom: 15px;">📖 รูปแบบ URL ที่ถูกต้อง:</h3>
                        
                        <div style="margin-bottom: 20px;">
                            <h4 style="color: #1565c0; margin-bottom: 10px;">📝 Parameters ที่ต้องใส่:</h4>
                            <div style="margin: 10px 0; padding-left: 20px;">
                                <p><strong>edition/e</strong> = เลือกฉบับ (<span style="color:red;">*</span>)</p>
                                <p><strong>volume/v</strong> = เลขเล่ม</p>
                                <p><strong>page/p</strong> = เลขหน้า</p>
                            </div>
                        </div>
                        
                        <h4 style="color: #1565c0; margin: 15px 0 10px 0;">🔤 แบบเต็ม (Full Format):</h4>
                        <div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 4px; margin: 10px 0;">
                            <span style="color: #1976d2;">?edition=[ฉบับ]&volume=[เล่ม]&page=[หน้า]</span>
                        </div>
                        
                        <h4 style="color: #1565c0; margin: 15px 0 10px 0;">🔡 แบบย่อ (Short Format):</h4>
                        <div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 4px; margin: 10px 0;">
                            <span style="color: #1976d2;">?e=[ฉบับ]&v=[เล่ม]&p=[หน้า]</span>
                        </div>
                    </div>
                    

                </div>
            `;
        }
        
        // ซ่อน flipbook และ controls
        const flipbookContainer = document.getElementById('flipbook-container');
        const controls = document.getElementById('controls');
        if (flipbookContainer) flipbookContainer.style.display = 'none';
        if (controls) controls.style.display = 'none';
        
        console.error('Edition parameter is required. Please add &ed=ch or &ed=mc to URL');
    }

    init() {
        this.setupVolumeSelector();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.handleURLParameters(); // เพิ่มการจัดการ URL parameters
    }

    /**
     * Handle URL parameters - รองรับทั้ง query parameters และ hash parameters
     * Examples:
     * - book-viewer?volume=1&page=5
     * - book-viewer#volume=1&page=5
     * - book-viewer?v=1&p=5
     */
    handleURLParameters() {
        // ตรวจสอบ query parameters (?volume=1&page=5)
        const urlParams = new URLSearchParams(window.location.search);
        
        // ตรวจสอบ hash parameters (#volume=1&page=5)
        const hashParams = new URLSearchParams(window.location.hash.replace('#', ''));
        
        // รวม parameters จากทั้งสองแหล่ง (hash จะมีความสำคัญมากกว่า)
        const params = new URLSearchParams();
        
        // เพิ่ม query params ก่อน
        urlParams.forEach((value, key) => params.set(key, value));
        
        // เพิ่ม hash params ทับ (override)
        hashParams.forEach((value, key) => params.set(key, value));
        
        // รองรับเฉพาะ 2 รูปแบบ: แบบย่อ และ แบบเต็ม
        const rawVolume = params.get('volume') || params.get('v');
        const page = params.get('page') || params.get('p');
        const rawEdition = params.get('edition') || params.get('e');
        
        // ทำให้ volume ID และ edition เป็นมาตรฐาน
        const volume = this.normalizeVolumeId(rawVolume);
        const edition = this.normalizeEdition(rawEdition);
        
        console.log('URL Parameters detected:', { rawVolume, volume, page, rawEdition, edition });
        
        // ตรวจสอบว่ามี edition หรือไม่
        if (!edition) {
            this.showEditionRequired();
            return;
        }
        
        // ตั้งค่า edition ปัจจุบัน
        this.currentEdition = edition;
        
        // อัปเดต UI เพื่อแสดง edition
        this.updateEditionDisplay();
        
        if (volume) {
            // ตั้งค่า flag เพื่อป้องกัน URL update ซ้ำ
            this.isLoadingFromURL = true;
            
            // ตั้งค่า volume selector
            const volumeSelect = document.getElementById('volumeSelect');
            if (volumeSelect) {
                volumeSelect.value = volume;
                
                // โหลด volume แล้วไปหน้าที่ระบุ
                this.loadVolume(volume).then(() => {
                    if (page) {
                        const pageNum = parseInt(page);
                        if (pageNum > 0 && pageNum <= this.totalPages) {
                            this.goToPage(pageNum - 1); // Convert to 0-based index
                        }
                    }
                    // รีเซ็ต flag หลังจากโหลดเสร็จ
                    this.isLoadingFromURL = false;
                });
            }
        }
        
        // Listen for hash changes (สำหรับ single page app navigation)
        window.addEventListener('hashchange', () => {
            this.handleURLParameters();
        });
    }

    /**
     * Update edition display in UI
     */
    updateEditionDisplay() {
        // อัปเดต header title เพื่อแสดง edition
        const headerTitle = document.querySelector('.header h1');
        if (headerTitle) {
            const editionName = this.currentEdition.toUpperCase();
            headerTitle.textContent = editionName;
        }
        
        // อัปเดต document title
        document.title = `${this.currentEdition.toUpperCase()} - Book Viewer`;
    }

    /**
     * Update URL when volume, page, or edition changes
     */
    updateURL(volume = null, page = null, edition = null) {
        // ไม่ update URL ถ้ากำลังโหลดจาก URL parameters
        if (this.isLoadingFromURL) {
            return;
        }
        
        if (!volume) volume = this.currentVolume;
        if (!edition) edition = this.currentEdition;
        if (!page && this.pages.length > 0) {
            // ใช้หน้าขวา (odd page) เป็น reference
            const currentPage = this.pages[this.currentPageIndex];
            if (currentPage && currentPage.number % 2 === 1) {
                page = currentPage.number;
            } else if (this.currentPageIndex + 1 < this.totalPages) {
                const nextPage = this.pages[this.currentPageIndex + 1];
                if (nextPage && nextPage.number % 2 === 1) {
                    page = nextPage.number;
                }
            }
        }

        // ตรวจสอบรูปแบบ parameter ที่ใช้อยู่เดิม
        const currentParams = new URLSearchParams(window.location.search);
        const hashParams = new URLSearchParams(window.location.hash.replace('#', ''));
        
        // ตรวจสอบว่าใช้รูปแบบย่อหรือเต็ม
        let useShortForm = false;
        if (currentParams.has('v') || currentParams.has('p') || currentParams.has('e') ||
            hashParams.has('v') || hashParams.has('p') || hashParams.has('e')) {
            useShortForm = true;
        }

        // ตรวจสอบว่ามี query parameters อยู่แล้วหรือไม่
        const hasQueryParams = window.location.search.length > 0;
        
        if (hasQueryParams) {
            // ใช้ query parameters - ลบ parameters เก่าทั้งหมดแล้วใส่ใหม่
            const url = new URL(window.location.href);
            
            // ล้าง parameters เก่าทั้งหมด
            ['volume', 'v', 'page', 'p', 'edition', 'e', 'ed'].forEach(param => {
                url.searchParams.delete(param);
            });
            
            // เพิ่ม parameters ใหม่ตามรูปแบบที่กำหนด
            if (useShortForm) {
                if (edition) url.searchParams.set('e', edition);
                if (volume) url.searchParams.set('v', volume);
                if (page) url.searchParams.set('p', page.toString());
            } else {
                if (edition) url.searchParams.set('edition', edition);
                if (volume) url.searchParams.set('volume', volume);
                if (page) url.searchParams.set('page', page.toString());
            }
            
            // อัปเดต URL โดยไม่ reload หน้า
            const newURL = url.pathname + url.search;
            if (window.location.pathname + window.location.search !== newURL) {
                history.replaceState(null, null, newURL);
            }
        } else {
            // ถ้าไม่มี query parameters ให้ใช้ hash parameters
            const params = new URLSearchParams();
            
            // ใช้รูปแบบเต็มสำหรับ hash (default)
            if (edition) params.set('edition', edition);
            if (volume) params.set('volume', volume);
            if (page) params.set('page', page.toString());
            
            // อัปเดต URL hash โดยไม่ reload หน้า
            if (params.toString()) {
                const newHash = '#' + params.toString();
                if (window.location.hash !== newHash) {
                    history.pushState(null, null, newHash);
                }
            }
        }
    }

    setupVolumeSelector() {
        const selector = document.getElementById('volumeSelect');
        if (!selector) return;
        
        this.volumes.forEach(volume => {
            const option = document.createElement('option');
            option.value = volume.folder;
            option.textContent = volume.name;
            selector.appendChild(option);
        });
    }

    setupEventListeners() {
        const volumeSelect = document.getElementById('volumeSelect');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const firstBtn = document.getElementById('firstBtn');
        const lastBtn = document.getElementById('lastBtn');
        const helpBtn = document.getElementById('helpBtn');

        if (volumeSelect) {
            volumeSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    // Normalize volume ID ก่อนโหลด
                    const normalizedVolume = this.normalizeVolumeId(e.target.value);
                    console.log('Volume selected:', e.target.value, '-> normalized:', normalizedVolume);
                    
                    if (normalizedVolume) {
                        this.loadVolume(normalizedVolume);
                    } else {
                        alert('เล่มที่เลือกไม่ถูกต้อง');
                    }
                } else {
                    this.hideFlipbook();
                    // Clear URL parameters
                    history.pushState(null, null, window.location.pathname);
                }
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.prevPage());
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextPage());
        }

        if (firstBtn) {
            firstBtn.addEventListener('click', () => this.goToPage(0));
        }

        if (lastBtn) {
            lastBtn.addEventListener('click', () => this.goToPage(this.totalPages - 1));
        }

        if (helpBtn) {
            helpBtn.addEventListener('click', () => this.showHelp());
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (!this.pages.length) return;
            
            switch(e.key) {
                case 'ArrowRight':
                case ' ':
                    e.preventDefault();
                    this.nextPage();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.prevPage();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.goToPage(0);
                    break;
                case 'End':
                    e.preventDefault();
                    this.goToPage(this.totalPages - 1);
                    break;
            }
        });
    }

    async loadVolume(volumeFolder) {
        this.currentVolume = volumeFolder;
        this.showLoading();
        
        try {
            // หาจำนวนหน้าทั้งหมดโดยไม่โหลดรูปจริง
            this.totalPages = await this.getTotalPages(volumeFolder);
            
            if (this.totalPages === 0) {
                alert('ไม่พบรูปภาพในเล่มนี้');
                this.hideFlipbook();
                return;
            }

            // เริ่มต้นที่หน้า 1 และโหลดหน้าแรกๆ
            this.currentPageIndex = 0;
            this.pages = new Array(this.totalPages); // สร้าง array เปล่าไว้ก่อน
            this.preloadedPages = new Set(); // เก็บหน้าที่โหลดแล้ว
            
            this.showFlipbook();
            await this.preloadCurrentPages(); // โหลดหน้าปัจจุบัน
            this.updateDisplay();
            
            // อัปเดต URL (เฉพาะเมื่อไม่ได้โหลดจาก URL parameters)
            if (!this.isLoadingFromURL) {
                this.updateURL();
            }
            
        } catch (error) {
            console.error('Error loading volume:', error);
            alert('เกิดข้อผิดพลาดในการโหลดเล่ม');
            this.hideFlipbook();
        }
    }

    async getTotalPages(volumeFolder) {
        // ตรวจสอบ cache ก่อน
        if (this.pageCounts.has(volumeFolder)) {
            console.log(`Using cached page count for volume ${volumeFolder}: ${this.pageCounts.get(volumeFolder)}`);
            return this.pageCounts.get(volumeFolder);
        }
        
        // ใช้ progressive search เพื่อลด 404 errors
        // เริ่มจากหน้าที่คาดการณ์ไว้ตาม volume
        let expectedPages = this.getExpectedPageCount(volumeFolder);
        let testRange = [Math.max(1, expectedPages - 50), expectedPages + 50];
        
        // ลองหาใกล้ ๆ range ที่คาดการณ์ไว้ก่อน
        let lastFoundPage = await this.searchInRange(volumeFolder, testRange[0], testRange[1]);
        
        // ถ้าไม่พบ ให้ขยายการค้นหา
        if (lastFoundPage === 0) {
            console.log('Expanding search range for volume', volumeFolder);
            lastFoundPage = await this.binarySearchPages(volumeFolder, 1, 600);
        }
        
        // เก็บผลลัพธ์ไว้ใน cache
        if (lastFoundPage > 0) {
            this.pageCounts.set(volumeFolder, lastFoundPage);
        }
        
        console.log(`Volume ${volumeFolder}: Found ${lastFoundPage} pages`);
        return lastFoundPage;
    }
    
    getExpectedPageCount(volumeFolder) {
        // กำหนดจำนวนหน้าโดยประมาณตาม volume (ปรับตามข้อมูลจริง)
        const expectedCounts = {
            '1': 200, '2': 180, '3': 220, '4': 190, '5': 210,
            '6': 185, '7': 280, '8': 195, '9': 175, '09': 175,
            '10': 160, '11': 145, '12': 170, '13': 155, '14': 165,
            '15': 180, '16': 165, '17': 190, '18': 145, '19': 160,
            '20': 175, '21': 140, '22': 320, '23': 280, '24': 200,
            '25': 185, '26': 160, '27': 155, '28': 170, '29': 165,
            '30': 180, '31': 155, '32': 160, '33': 240, '34': 220,
            '35': 200, '36': 190, '37': 185, '38': 180, '39': 175,
            '40': 380 // สมมติว่าเล่ม 40 มีหน้าเยอะที่สุด
        };
        return expectedCounts[volumeFolder] || 200; // default 200 pages
    }
    
    async searchInRange(volumeFolder, start, end) {
        let lastFound = 0;
        let consecutiveNotFound = 0;
        const maxMissing = 5; // หยุดหลังจากไม่พบ 5 หน้าติดต่อกัน
        
        for (let page = start; page <= end && consecutiveNotFound < maxMissing; page++) {
            const imagePath = `/tipitaka/${this.currentEdition}/${volumeFolder}/${page}.png`;
            
            try {
                const exists = await this.checkImageExists(imagePath);
                if (exists) {
                    lastFound = page;
                    consecutiveNotFound = 0;
                } else {
                    consecutiveNotFound++;
                }
            } catch (error) {
                consecutiveNotFound++;
            }
            
            // เพิ่ม delay เล็กน้อยเพื่อไม่ให้ส่ง request มากเกินไป
            if (page % 10 === 0) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }
        
        return lastFound;
    }
    
    async binarySearchPages(volumeFolder, low, high) {
        let lastFoundPage = 0;
        let attempts = 0;
        const maxAttempts = 15; // จำกัดจำนวน attempts
        
        while (low <= high && attempts < maxAttempts) {
            attempts++;
            const mid = Math.floor((low + high) / 2);
            // ใช้ currentEdition ใน path
            const imagePath = `/tipitaka/${this.currentEdition}/${volumeFolder}/${mid}.png`;
            
            try {
                const imageExists = await this.checkImageExists(imagePath);
                if (imageExists) {
                    lastFoundPage = mid;
                    low = mid + 1;
                } else {
                    high = mid - 1;
                }
            } catch (error) {
                high = mid - 1;
            }
            
            // เพิ่ม delay เล็กน้อย
            await new Promise(resolve => setTimeout(resolve, 50));
        }
        
        return lastFoundPage;
    }

    async preloadCurrentPages() {
        const pagesToPreload = [];
        
        // โหลดหน้าปัจจุบัน ± 2 หน้า
        for (let i = Math.max(0, this.currentPageIndex - 1); 
             i <= Math.min(this.totalPages - 1, this.currentPageIndex + 3); 
             i++) {
            if (!this.preloadedPages.has(i)) {
                pagesToPreload.push(i);
            }
        }
        
        // โหลดหน้าที่ต้องการ
        for (const pageIndex of pagesToPreload) {
            const pageNum = pageIndex + 1;
            const imagePath = `/tipitaka/${this.currentEdition}/${this.currentVolume}/${pageNum}.png`;
            
            this.pages[pageIndex] = {
                number: pageNum,
                path: imagePath
            };
            this.preloadedPages.add(pageIndex);
            
            // Preload image ไว้ใน browser cache
            const img = new Image();
            img.src = imagePath;
        }
    }

    checkImageExists(imagePath) {
        return fetch(imagePath, { 
            method: 'HEAD',
            cache: 'force-cache', // ใช้ cache เพื่อลด requests
            signal: AbortSignal.timeout(5000) // timeout 5 วินาที
        })
        .then(response => response.ok)
        .catch(() => false);
    }

    /**
     * Update display - CORRECTED VERSION
     * LEFT side = EVEN pages (2, 4, 6, 8...)
     * RIGHT side = ODD pages (1, 3, 5, 7...)
     */
    updateDisplay() {
        const leftPageImg = document.getElementById('leftPageImg');
        const rightPageImg = document.getElementById('rightPageImg');
        const leftPageNum = document.getElementById('leftPageNum');
        const rightPageNum = document.getElementById('rightPageNum');
        
        console.log('Current page index:', this.currentPageIndex);
        console.log('Total pages:', this.totalPages);
        
        // RIGHT PAGE (ODD NUMBERS): Show page at currentPageIndex if it's odd
        let rightPageData = null;
        if (this.currentPageIndex < this.totalPages) {
            // สร้าง page object สำหรับหน้าปัจจุบัน (ถ้ายังไม่มี)
            if (!this.pages[this.currentPageIndex]) {
                const pageNum = this.currentPageIndex + 1;
                this.pages[this.currentPageIndex] = {
                    number: pageNum,
                    path: `/tipitaka/${this.currentEdition}/${this.currentVolume}/${pageNum}.png`
                };
            }
            
            const currentPage = this.pages[this.currentPageIndex];
            console.log('Current page number:', currentPage.number);
            
            // If current page is odd, show it on the right
            if (currentPage.number % 2 === 1) {
                rightPageData = currentPage;
            } else {
                // If current page is even, look for the next odd page
                const nextPageIndex = this.currentPageIndex + 1;
                if (nextPageIndex < this.totalPages) {
                    if (!this.pages[nextPageIndex]) {
                        const pageNum = nextPageIndex + 1;
                        this.pages[nextPageIndex] = {
                            number: pageNum,
                            path: `/tipitaka/${this.currentEdition}/${this.currentVolume}/${pageNum}.png`
                        };
                    }
                    if (this.pages[nextPageIndex].number % 2 === 1) {
                        rightPageData = this.pages[nextPageIndex];
                    }
                }
            }
        }
        
        // Display right page (odd numbers)
        if (rightPageData && rightPageImg && rightPageNum) {
            rightPageImg.src = rightPageData.path;
            rightPageImg.style.display = 'block';
            rightPageNum.textContent = rightPageData.number.toString();
            rightPageNum.style.display = 'block'; // แสดงหมายเลขหน้าพร้อมพื้นหลัง
            console.log('Right page (odd):', rightPageData.number);
        } else if (rightPageImg && rightPageNum) {
            rightPageImg.style.display = 'none';
            rightPageNum.textContent = '';
            rightPageNum.style.display = 'none'; // ซ่อนพื้นหลังหมายเลขหน้า
        }
        
        // LEFT PAGE (EVEN NUMBERS): Look for previous even page
        let leftPageData = null;
        if (rightPageData && rightPageData.number > 1) {
            // Find the previous even page before the right page
            const leftPageNum = rightPageData.number - 1;
            const leftPageIndex = leftPageNum - 1; // Convert to 0-based index
            
            if (leftPageIndex >= 0 && leftPageIndex < this.totalPages) {
                if (!this.pages[leftPageIndex]) {
                    this.pages[leftPageIndex] = {
                        number: leftPageNum,
                        path: `/tipitaka/${this.currentEdition}/${this.currentVolume}/${leftPageNum}.png`
                    };
                }
                leftPageData = this.pages[leftPageIndex];
            }
        }
        
        // Display left page (even numbers)
        if (leftPageData && leftPageImg && leftPageNum) {
            leftPageImg.src = leftPageData.path;
            leftPageImg.style.display = 'block';
            leftPageNum.textContent = leftPageData.number.toString();
            leftPageNum.style.display = 'block'; // แสดงหมายเลขหน้าพร้อมพื้นหลัง
            console.log('Left page (even):', leftPageData.number);
        } else if (leftPageImg && leftPageNum) {
            leftPageImg.style.display = 'none';
            leftPageNum.textContent = '';
            leftPageNum.style.display = 'none'; // ซ่อนพื้นหลังหมายเลขหน้า
        }
        
        this.updatePageInfo(leftPageData, rightPageData);
        this.updateControls();
        
        // อัปเดต URL หลังจากเปลี่ยนหน้า
        this.updateURL();
    }

    updatePageInfo(leftPageData, rightPageData) {
        const currentPage = document.getElementById('currentPage');
        const currentPage2 = document.getElementById('currentPage2');
        const totalPages = document.getElementById('totalPages');
        
        // Left = even numbers, Right = odd numbers
        if (currentPage) {
            currentPage.textContent = leftPageData ? leftPageData.number.toString() : '-';
        }
        if (currentPage2) {
            currentPage2.textContent = rightPageData ? rightPageData.number.toString() : '-';
        }
        if (totalPages) {
            totalPages.textContent = this.totalPages.toString();
        }
    }

    updateControls() {
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const firstBtn = document.getElementById('firstBtn');
        const lastBtn = document.getElementById('lastBtn');

        if (prevBtn) prevBtn.disabled = this.currentPageIndex <= 0;
        if (nextBtn) nextBtn.disabled = this.currentPageIndex >= this.totalPages - 1;
        if (firstBtn) firstBtn.disabled = this.currentPageIndex <= 0;
        if (lastBtn) lastBtn.disabled = this.currentPageIndex >= this.totalPages - 1;
    }

    async prevPage() {
        if (this.currentPageIndex > 1) {
            this.currentPageIndex -= 2;
            if (this.currentPageIndex < 0) this.currentPageIndex = 0;
            await this.preloadCurrentPages(); // โหลดหน้าใหม่ที่อาจต้องการ
            this.updateDisplay();
        }
    }

    async nextPage() {
        if (this.currentPageIndex < this.totalPages - 2) {
            this.currentPageIndex += 2;
            await this.preloadCurrentPages(); // โหลดหน้าใหม่ที่อาจต้องการ
            this.updateDisplay();
        }
    }

    async goToPage(pageIndex) {
        if (pageIndex >= 0 && pageIndex < this.totalPages) {
            this.currentPageIndex = pageIndex;
            await this.preloadCurrentPages(); // โหลดหน้าใหม่ที่อาจต้องการ
            this.updateDisplay(); // จะเรียก updateURL() อัตโนมัติ
        }
    }

    showLoading() {
        const loading = document.getElementById('loading');
        const container = document.getElementById('flipbook-container');
        const controls = document.getElementById('controls');
        
        if (loading) loading.style.display = 'block';
        if (container) container.style.display = 'block';
        if (controls) controls.style.display = 'none';
    }

    showFlipbook() {
        const loading = document.getElementById('loading');
        const container = document.getElementById('flipbook-container');
        const controls = document.getElementById('controls');
        
        if (loading) loading.style.display = 'none';
        if (container) container.style.display = 'block';
        if (controls) controls.style.display = 'block';
    }

    hideFlipbook() {
        const container = document.getElementById('flipbook-container');
        const controls = document.getElementById('controls');
        
        if (container) container.style.display = 'none';
        if (controls) controls.style.display = 'none';
    }

    showHelp() {
        const helpText = `การใช้งาน Flipbook Viewer:

⌨️ แป้นพิมพ์:
• → หรือ Space: หน้าถัดไป
• ←: หน้าก่อนหน้า  
• Home: ไปหน้าแรก
• End: ไปหน้าสุดท้าย

🔘 ปุ่มควบคุม:
• หน้าก่อน/หน้าถัดไป
• หน้าแรก/หน้าสุดท้าย

💡 รูปแบบการแสดงหน้า:
• ด้านซ้าย: หน้าเลขคู่ (2, 4, 6, 8...)
• ด้านขวา: หن้าเลขคี่ (1, 3, 5, 7...)

🔗 URL Parameters (Required):
📝 Parameters ที่ต้องมี:
• edition/e = เลือกฉบับ (จำเป็น)
• volume/v = เลขเล่ม (1-40)  
• page/p = เลขหน้า

📄 แบบเต็ม:
• ?edition=[ฉบับ]&volume=[เล่ม]&page=[หน้า]

📝 แบบย่อ:
• ?e=[ฉบับ]&v=[เล่ม]&p=[หน้า]

💡 เคล็ดลับ:
• Edition parameter เป็นสิ่งจำเป็น ต้องระบุทุกครั้ง
• ใช้รูปแบบเดียวกัน (เต็ม หรือ ย่อ) เพื่อความสอดคล้อง
• แชร์ URL เพื่อให้ผู้อื่นเปิดหน้าเดียวกัน
• ใช้แป้นพิมพ์สำหรับความเร็วในการเปลี่ยนหน้า`;

        alert(helpText);
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    try {
        new BookViewer();
        console.log('✅ Flipbook Viewer initialized successfully');
    } catch (error) {
        console.error('❌ Error initializing Flipbook Viewer:', error);
    }
});