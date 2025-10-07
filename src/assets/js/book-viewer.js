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
        this.volumes = []; // จะโหลดอีกทีหลังจากที่รู้ edition
        
        /** @type {Map<string, number>} */
        this.pageCounts = new Map(); // Cache สำหรับจำนวนหน้าของแต่ละ volume
        
        /** @type {Object|null} */
        this.bookViewerMetadata = null; // Cache สำหรับข้อมูล book viewer (titles, descriptions, pages)
        
        /** @type {boolean} */
        this.isLoadingFromURL = false; // Flag เพื่อป้องกัน URL update ระหว่างโหลดจาก URL
        
        /** @type {number|null} */
        this.preloadingTimeout = null; // สำหรับ smart preloading
        
        /** @type {Map<string, HTMLImageElement>} */
        this.imageCache = new Map(); // Cache สำหรับรูปภาพที่โหลดแล้ว
        
        /** @type {number} */
        this.maxCacheSize = 20; // จำกัดจำนวนรูปใน cache
        
        // เรียกใช้ init แบบ async
        this.init().catch(error => {
            console.error('Error during initialization:', error);
        });
    }

    async generateVolumeList(edition = null) {
        const volumes = [];
        
        try {
            // โหลด book viewer metadata ถ้ายังไม่มี
            if (!this.bookViewerMetadata) {
                await this.loadBookViewerMetadata();
            }
            
            // ถ้ามี edition ให้ใช้เฉพาะ edition นั้น
            if (edition && this.bookViewerMetadata && 
                this.bookViewerMetadata.editions && 
                this.bookViewerMetadata.editions[edition] &&
                this.bookViewerMetadata.editions[edition].volumes) {
                
                const volumeIds = Object.keys(this.bookViewerMetadata.editions[edition].volumes);
                volumeIds.sort((a, b) => parseInt(a) - parseInt(b)); // เรียงตามลำดับ
                
                volumeIds.forEach(volumeId => {
                    const volumeData = this.bookViewerMetadata.editions[edition].volumes[volumeId];
                    volumes.push({
                        id: volumeId,
                        name: `${volumeId}`,
                        folder: volumeId,
                        volumeName: volumeData.title || `เล่ม ${volumeId}`,
                        pages: volumeData.pages
                    });
                });
                
                console.log(`Generated ${volumes.length} volumes for edition ${edition.toUpperCase()}`);
                return volumes;
            }
            
            // ถ้าไม่มี edition หรือไม่มี metadata ให้ใช้ default (CH + MC รวมกัน)
            if (this.bookViewerMetadata && this.bookViewerMetadata.editions) {
                const allVolumeIds = new Set();
                
                // รวม volume IDs จากทุก edition
                Object.values(this.bookViewerMetadata.editions).forEach(editionData => {
                    if (editionData.volumes) {
                        Object.keys(editionData.volumes).forEach(volumeId => {
                            allVolumeIds.add(volumeId);
                        });
                    }
                });
                
                const sortedIds = Array.from(allVolumeIds).sort((a, b) => parseInt(a) - parseInt(b));
                
                sortedIds.forEach(volumeId => {
                    volumes.push({
                        id: volumeId,
                        name: `${volumeId}`,
                        folder: volumeId
                    });
                });
                
                console.log(`Generated ${volumes.length} volumes from metadata (all editions)`);
                return volumes;
            }
        } catch (error) {
            console.warn('Failed to load metadata, falling back to default volume list:', error);
        }
        
        // Fallback: ใช้ hard code เฉพาะเมื่อไม่สามารถโหลด metadata ได้
        for (let i = 1; i <= 45; i++) { // ใช้ 45 เพราะ MC มี 45 เล่ม
            const volumeId = i.toString();
            volumes.push({
                id: volumeId,
                name: `${i}`,
                folder: volumeId
            });
        }
        
        console.log(`Generated ${volumes.length} volumes (fallback mode)`);
        return volumes;
    }

    // ฟังก์ชันสำหรับทำให้ volume ID เป็นมาตรฐาน
    normalizeVolumeId(volume) {
        if (!volume) return null;
        
        const num = parseInt(volume);
        if (isNaN(num) || num < 1) return null;
        
        // ตรวจสอบว่า volume นี้มีอยู่ใน edition ปัจจุบันหรือไม่
        if (this.currentEdition && this.bookViewerMetadata && 
            this.bookViewerMetadata.editions &&
            this.bookViewerMetadata.editions[this.currentEdition] &&
            this.bookViewerMetadata.editions[this.currentEdition].volumes) {
            
            const volumeId = num.toString();
            if (this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeId]) {
                return volumeId;
            } else {
                console.warn(`Volume ${volumeId} not found in ${this.currentEdition.toUpperCase()} edition`);
                return null;
            }
        }
        
        // Fallback: ตรวจสอบช่วงทั่วไป (1-45)
        if (num <= 45) {
            return num.toString();
        }
        
        return null;
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

    async init() {
        await this.setupVolumeSelector();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupCleanup();
        await this.handleURLParameters(); // เพิ่มการจัดการ URL parameters
    }

    /**
     * Handle URL parameters - รองรับทั้ง query parameters และ hash parameters
     * Examples:
     * - book-viewer?volume=1&page=5
     * - book-viewer#volume=1&page=5
     * - book-viewer?v=1&p=5
     */
    async handleURLParameters() {
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
        await this.updateEditionDisplay();
        
        // ตรวจสอบว่า volume ที่ระบุใน URL มีอยู่หรือไม่
        if (rawVolume && !volume) {
            alert(`Volume ${rawVolume} not found in ${edition.toUpperCase()} edition\nPlease select an available volume from dropdown`);
            // เคลียร์ URL parameters ที่ไม่ถูกต้อง
            history.pushState(null, null, window.location.pathname + `?edition=${edition}`);
            return;
        }
        
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
    async updateEditionDisplay() {
        // โหลด book viewer metadata ถ้ายังไม่มี
        if (!this.bookViewerMetadata) {
            await this.loadBookViewerMetadata();
        }

        // อัปเดต header title เพื่อแสดง edition
        const headerTitle = document.querySelector('.header h1');
        if (headerTitle) {
            let displayTitle = this.currentEdition.toUpperCase();
            
            // ใช้ชื่อเต็มจาก metadata ถ้ามี
            if (this.bookViewerMetadata && 
                this.bookViewerMetadata.editions && 
                this.bookViewerMetadata.editions[this.currentEdition]) {
                displayTitle = this.bookViewerMetadata.editions[this.currentEdition].title;
            }
            
            headerTitle.textContent = displayTitle;
        }
        
        // อัปเดต document title
        let docTitle = this.currentEdition.toUpperCase();
        if (this.bookViewerMetadata && 
            this.bookViewerMetadata.editions && 
            this.bookViewerMetadata.editions[this.currentEdition]) {
            docTitle = this.bookViewerMetadata.editions[this.currentEdition].title;
        }
        document.title = `${docTitle} - Book Viewer`;
        
        // อัปเดต volume selector สำหรับ edition นี้
        await this.updateVolumeSelector(this.currentEdition);
    }

    /**
     * Update volume title display in UI
     */
    async updateVolumeDisplay(volumeId) {
        // โหลด book viewer metadata ถ้ายังไม่มี
        if (!this.bookViewerMetadata) {
            await this.loadBookViewerMetadata();
        }

        const volumeTitle = document.querySelector('.volume-title');
        if (!volumeTitle) return;

        if (volumeId && this.bookViewerMetadata && 
            this.bookViewerMetadata.editions && 
            this.bookViewerMetadata.editions[this.currentEdition] &&
            this.bookViewerMetadata.editions[this.currentEdition].volumes &&
            this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeId]) {
            
            const volumeData = this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeId];
            
            // Clear cache if data looks wrong (empty pages for volumes that should have them)
            if (volumeId === '1' && (!volumeData.pages || volumeData.pages === 0)) {
                console.log('⚠️ Detected missing pages for volume 1, clearing cache...');
                localStorage.removeItem('tipitaka-book-viewer');
                localStorage.removeItem('tipitaka-book-viewer-timestamp');
                // Reload metadata
                await this.loadBookViewerMetadata();
                // Get fresh data
                if (this.bookViewerMetadata && 
                    this.bookViewerMetadata.editions && 
                    this.bookViewerMetadata.editions[this.currentEdition] &&
                    this.bookViewerMetadata.editions[this.currentEdition].volumes &&
                    this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeId]) {
                    volumeData = this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeId];
                    console.log('🔄 Refreshed volume data:', volumeData);
                }
            }
            
            // สร้างข้อความจาก description และจำนวนหน้า
            let displayParts = [];
            if (volumeData.desc && volumeData.desc.trim() !== '') {
                displayParts.push(volumeData.desc.trim());
            }
            if (volumeData.pages) {
                displayParts.push(`${volumeData.pages} pages`);
            }
            
            // แสดง description : pages หรือ Volume ID เป็น fallback
            if (displayParts.length > 0) {
                volumeTitle.textContent = displayParts.join(' : ');
            } else {
                volumeTitle.textContent = `Volume ${volumeId}`;
            }
            
            // ไม่ต้องมี tooltip
            volumeTitle.title = '';
            
            volumeTitle.style.display = 'block';
        } else if (volumeId) {
            volumeTitle.textContent = `Volume ${volumeId}`;
            volumeTitle.title = '';
            volumeTitle.style.display = 'block';
        } else {
            volumeTitle.style.display = 'none';
        }
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

    async setupVolumeSelector() {
        const selector = document.getElementById('volumeSelect');
        if (!selector) return;
        
        // เคลียร์ options เดิมก่อน
        selector.innerHTML = '<option value="">-- Select Volume --</option>';
        
        // ใส่ placeholder ระหว่างโหลด
        const loadingOption = document.createElement('option');
        loadingOption.value = '';
        loadingOption.textContent = 'Loading volumes...';
        loadingOption.disabled = true;
        selector.appendChild(loadingOption);
    }
    
    async updateVolumeSelector(edition) {
        const selector = document.getElementById('volumeSelect');
        if (!selector || !edition) return;
        
        try {
            // โหลด volume list สำหรับ edition นี้
            this.volumes = await this.generateVolumeList(edition);
            
            // เคลียร์และสร้าง options ใหม่
            selector.innerHTML = '<option value="">-- Select Volume --</option>';
            
            this.volumes.forEach(volume => {
                const option = document.createElement('option');
                option.value = volume.folder;
                
                // สร้าง text สำหรับ option โดยใช้ title และ desc ถ้ามี
                let optionText = `Volume ${volume.name}`;
                if (volume.volumeName && volume.volumeName !== `เล่ม ${volume.id}`) {
                    // ถ้ามี volumeName (title) ที่ไม่ใช่ค่า default
                    optionText = `Volume ${volume.name} - ${volume.volumeName}`;
                }
                
                option.textContent = optionText;
                
                // เพิ่ม title attribute สำหรับ tooltip
                if (volume.pages) {
                    option.title = `${volume.pages} pages`;
                }
                
                selector.appendChild(option);
            });
            
            console.log(`Volume selector updated for ${edition.toUpperCase()}: ${this.volumes.length} volumes`);
            
        } catch (error) {
            console.error('Error updating volume selector:', error);
            
            // Fallback: แสดง error message
            selector.innerHTML = '<option value="">Error loading volume list</option>';
        }
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
                        alert('Invalid volume selected');
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
                alert('No images found in this volume');
                this.hideFlipbook();
                return;
            }

            // เริ่มต้นที่หน้า 1 และโหลดหน้าแรกๆ
            this.currentPageIndex = 0;
            this.pages = new Array(this.totalPages); // สร้าง array เปล่าไว้ก่อน
            this.preloadedPages = new Set(); // เก็บหน้าที่โหลดแล้ว
            
            // อัปเดตการแสดงชื่อเล่ม
            await this.updateVolumeDisplay(volumeFolder);
            
            this.showFlipbook();
            await this.preloadCurrentPages(); // โหลดหน้าปัจจุบัน
            this.updateDisplay();
            
            // อัปเดต URL (เฉพาะเมื่อไม่ได้โหลดจาก URL parameters)
            if (!this.isLoadingFromURL) {
                this.updateURL();
            }
            
        } catch (error) {
            console.error('Error loading volume:', error);
            alert('Error loading volume');
            this.hideFlipbook();
        }
    }

    async getTotalPages(volumeFolder) {
        // ตรวจสอบ cache ก่อน
        if (this.pageCounts.has(volumeFolder)) {
            console.log(`Using cached page count for volume ${volumeFolder}: ${this.pageCounts.get(volumeFolder)}`);
            return this.pageCounts.get(volumeFolder);
        }
        
        // โหลดข้อมูล book viewer metadata ถ้ายังไม่มี
        if (!this.bookViewerMetadata) {
            console.log('Loading book viewer metadata...');
            await this.loadBookViewerMetadata();
        }
        
        // ดึงจำนวนหน้าจาก metadata
        console.log('🔍 Checking metadata for:', {
            edition: this.currentEdition,
            volume: volumeFolder,
            hasMetadata: !!this.bookViewerMetadata,
            hasEdition: !!(this.bookViewerMetadata?.editions?.[this.currentEdition]),
            hasVolume: !!(this.bookViewerMetadata?.editions?.[this.currentEdition]?.volumes?.[volumeFolder])
        });
        
        if (this.bookViewerMetadata && 
            this.bookViewerMetadata.editions &&
            this.bookViewerMetadata.editions[this.currentEdition] && 
            this.bookViewerMetadata.editions[this.currentEdition].volumes &&
            this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeFolder]) {
            
            const volumeData = this.bookViewerMetadata.editions[this.currentEdition].volumes[volumeFolder];
            const pageCount = volumeData.pages;
            this.pageCounts.set(volumeFolder, pageCount);
            console.log(`✅ Volume ${volumeFolder} (${this.currentEdition.toUpperCase()}): ${pageCount} pages (from metadata)`);
            return pageCount;
        } else {
            console.warn('❌ Volume not found in metadata:', {
                edition: this.currentEdition,
                volume: volumeFolder,
                availableVolumes: this.bookViewerMetadata?.editions?.[this.currentEdition]?.volumes ? 
                    Object.keys(this.bookViewerMetadata.editions[this.currentEdition].volumes) : 'none'
            });
        }
        
        // ถ้าไม่พบใน metadata ให้ fallback กลับไปใช้วิธีเดิม
        console.warn(`Volume ${volumeFolder} not found in metadata, falling back to search method`);
        return await this.fallbackGetTotalPages(volumeFolder);
    }
    


    async loadBookViewerMetadata() {
        try {
            // ตรวจสอบ cache ใน localStorage
            const cachedData = localStorage.getItem('tipitaka-book-viewer');
            const cachedTimestamp = localStorage.getItem('tipitaka-book-viewer-timestamp');
            
            // ถ้ามี cache และอายุไม่เกิน 24 ชั่วโมง
            if (cachedData && cachedTimestamp) {
                const age = Date.now() - parseInt(cachedTimestamp);
                const maxAge = 24 * 60 * 60 * 1000; // 24 ชั่วโมง
                
                if (age < maxAge) {
                    console.log('Using cached book viewer metadata');
                    const metadata = JSON.parse(cachedData);
                    
                    // Validate cache - check if volume 1 has title
                    if (metadata?.editions?.ch?.volumes?.['1']?.title) {
                        this.bookViewerMetadata = metadata;
                        return;
                    } else {
                        console.log('⚠️ Cache validation failed - clearing invalid cache');
                        localStorage.removeItem('tipitaka-book-viewer');
                        localStorage.removeItem('tipitaka-book-viewer-timestamp');
                    }
                }
            }
            
            // โหลดจากไฟล์ JSON
            console.log('Fetching book viewer metadata from server...');
            const response = await fetch('/tipitaka/book-viewer.json', {
                cache: 'force-cache'
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load book viewer metadata: ${response.status}`);
            }
            
            this.bookViewerMetadata = await response.json();
            
            // เก็บไว้ใน localStorage
            localStorage.setItem('tipitaka-book-viewer', JSON.stringify(this.bookViewerMetadata));
            localStorage.setItem('tipitaka-book-viewer-timestamp', Date.now().toString());
            
            console.log('Book viewer metadata loaded successfully');
            
        } catch (error) {
            console.error('Error loading book viewer metadata:', error);
            this.bookViewerMetadata = null;
        }
    }
    
    async fallbackGetTotalPages(volumeFolder) {
        // Fallback: คืนค่า 0 เพราะไม่มี metadata
        console.warn(`No metadata available for volume ${volumeFolder}, returning 0 pages`);
        return 0;
    }


    

    


    async preloadCurrentPages() {
        // โหลดแค่หน้าที่แสดงอยู่ (left + right) บวกหน้าถัดไปอีก 1 หน้า
        const pagesToPreload = [];
        
        // หน้าปัจจุบัน (currentPageIndex และ currentPageIndex + 1)
        for (let i = this.currentPageIndex; 
             i <= Math.min(this.totalPages - 1, this.currentPageIndex + 2); 
             i++) {
            if (!this.preloadedPages.has(i)) {
                pagesToPreload.push(i);
            }
        }
        
        // โหลดหน้าที่จำเป็นทีละหน้า (ไม่รอกัน)
        const preloadPromises = pagesToPreload.map(pageIndex => 
            this.preloadSinglePage(pageIndex)
        );
        
        // รอให้โหลดครบแค่หน้าปัจจุบัน (2 หน้าแรก)
        if (preloadPromises.length > 0) {
            await Promise.all(preloadPromises.slice(0, 2));
            
            // หน้าอื่นๆ ให้โหลดใน background
            if (preloadPromises.length > 2) {
                Promise.all(preloadPromises.slice(2)).catch(console.warn);
            }
        }
        
        // เริ่ม smart preloading สำหรับหน้าถัดไป
        this.startSmartPreloading();
    }
    
    async preloadSinglePage(pageIndex) {
        try {
            const pageNum = pageIndex + 1;
            const imagePath = `/tipitaka/${this.currentEdition}/${this.currentVolume}/${pageNum}.png`;
            
            // ตรวจสอบใน cache ก่อน
            if (this.imageCache.has(imagePath)) {
                // สร้าง page object และใช้ image จาก cache
                this.pages[pageIndex] = {
                    number: pageNum,
                    path: imagePath,
                    cached: true
                };
                this.preloadedPages.add(pageIndex);
                return Promise.resolve(pageIndex);
            }
            
            // สร้าง page object
            this.pages[pageIndex] = {
                number: pageNum,
                path: imagePath
            };
            this.preloadedPages.add(pageIndex);
            
            // โหลดรูปใหม่และเก็บใน cache
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    // เพิ่มใน cache
                    this.addToImageCache(imagePath, img);
                    resolve(pageIndex);
                };
                img.onerror = () => {
                    console.warn(`Failed to preload page ${pageNum}`);
                    resolve(pageIndex); // resolve anyway เพื่อไม่ให้หยุดการทำงาน
                };
                img.src = imagePath;
            });
            
        } catch (error) {
            console.warn(`Error preloading page ${pageIndex + 1}:`, error);
        }
    }
    
    addToImageCache(imagePath, img) {
        // ถ้า cache เต็ม ให้ลบอันเก่าออกก่อน (LRU-like)
        if (this.imageCache.size >= this.maxCacheSize) {
            const firstKey = this.imageCache.keys().next().value;
            this.imageCache.delete(firstKey);
        }
        
        this.imageCache.set(imagePath, img);
        console.log(`Image cached: ${imagePath} (${this.imageCache.size}/${this.maxCacheSize})`);
    }
    

    
    clearImageCache() {
        this.imageCache.clear();
        console.log('Image cache cleared');
    }
    
    // Session State Management
    saveSessionState() {
        const state = {
            volume: this.currentVolume,
            edition: this.currentEdition,
            pageIndex: this.currentPageIndex,
            timestamp: Date.now()
        };
        
        try {
            sessionStorage.setItem('tipitaka-reader-state', JSON.stringify(state));
        } catch (error) {
            console.warn('Failed to save session state:', error);
        }
    }
    

    
    setupCleanup() {
        // ทำความสะอาดเมื่อปิดหน้าเว็บ
        window.addEventListener('beforeunload', () => {
            // บันทึก state สุดท้าย
            this.saveSessionState();
            
            // ล้าง timeout
            if (this.preloadingTimeout) {
                clearTimeout(this.preloadingTimeout);
            }
        });
        
        // จัดการหน่วยความจำเมื่อหน้าเว็บถูกซ่อน
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // ลด cache ลงเหลือครึ่ง เมื่อหน้าถูกซ่อน
                this.trimImageCache();
            }
        });
    }
    
    trimImageCache() {
        const targetSize = Math.floor(this.maxCacheSize / 2);
        while (this.imageCache.size > targetSize) {
            const firstKey = this.imageCache.keys().next().value;
            this.imageCache.delete(firstKey);
        }
        console.log(`Image cache trimmed to ${this.imageCache.size} items`);
    }
    
    startSmartPreloading() {
        // ยกเลิก preloading เก่าถ้ามี
        if (this.preloadingTimeout) {
            clearTimeout(this.preloadingTimeout);
        }
        
        // ตั้งเวลาโหลดหน้าถัดไปหลังจาก 1 วินาที
        this.preloadingTimeout = setTimeout(() => {
            this.preloadNextPages();
        }, 1000);
    }
    
    async preloadNextPages() {
        // โหลดหน้าถัดไป 3-4 หน้าใน background
        const startIndex = Math.max(0, this.currentPageIndex + 3);
        const endIndex = Math.min(this.totalPages - 1, this.currentPageIndex + 6);
        
        for (let i = startIndex; i <= endIndex; i++) {
            if (!this.preloadedPages.has(i)) {
                // โหลดทีละหน้า พร้อม delay เพื่อไม่ให้หนักเกินไป
                setTimeout(() => {
                    this.preloadSinglePage(i);
                }, (i - startIndex) * 200); // delay 200ms ต่อหน้า
            }
        }
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
        
        // บันทึก state ปัจจุบัน
        this.saveSessionState();
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
            
            // โหลดแค่หน้าที่จำเป็นทันที
            await this.preloadCurrentPages();
            this.updateDisplay();
        }
    }

    async nextPage() {
        if (this.currentPageIndex < this.totalPages - 2) {
            this.currentPageIndex += 2;
            
            // โหลดแค่หน้าที่จำเป็นทันที
            await this.preloadCurrentPages();
            this.updateDisplay();
        }
    }

    async goToPage(pageIndex) {
        if (pageIndex >= 0 && pageIndex < this.totalPages) {
            this.currentPageIndex = pageIndex;
            
            // โหลดแค่หน้าที่จำเป็นทันที
            await this.preloadCurrentPages();
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
        
        // ซ่อนชื่อเล่มเมื่อไม่มีเล่มที่เลือก
        this.updateVolumeDisplay(null);
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
• volume/v = เลขเล่ม (CH:1-40, MC:1-45)  
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