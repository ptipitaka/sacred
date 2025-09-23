import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

// Build script สำหรับ Tipitaka dataset แบบแยก locale
async function buildByLocale() {
    console.log('🚀 เริ่มต้น build process แบบแยก locale สำหรับ Tipitaka dataset...');
    console.log('📊 จำนวนไฟล์ทั้งหมด: ~161,529 files');
    
    // อ่าน locale จาก command line arguments
    const args = process.argv.slice(2);
    const allLocales = ['romn', 'thai', 'mymr', 'sinh', 'deva', 'khmr', 'laoo', 'lana'];
    
    let locales;
    if (args.length > 0) {
        // ใช้ locale ที่ระบุ
        locales = args.filter(locale => allLocales.includes(locale));
        if (locales.length === 0) {
            console.error('❌ Locale ที่ระบุไม่ถูกต้อง!');
            console.log('📋 Locale ที่รองรับ:', allLocales.join(', '));
            process.exit(1);
        }
        console.log(`🎯 Build เฉพาะ locale ที่ระบุ: ${locales.join(', ')}`);
    } else {
        // ใช้ทุก locale
        locales = allLocales;
        console.log(`🌍 Build ทุก locale: ${locales.join(', ')}`);
    }
    
    const buildOptions = {
        memory: '12288', // ใช้ 12GB (เหลือ 4GB สำหรับ OS)
        timeout: 0,
        stdio: 'inherit'
    };

    console.log('📝 เริ่ม build แยกตาม locale...');
    console.log(`📋 Locales ที่จะ build: ${locales.join(', ')}\n`);

    let successCount = 0;
    let failCount = 0;

    // แยก build ตาม locale ทีละตัว
    for (let i = 0; i < locales.length; i++) {
        const locale = locales[i];
        console.log(`\n🏗️  [${i + 1}/${locales.length}] กำลัง build locale: ${locale.toUpperCase()}`);
        console.log(`⏰ เวลาเริ่มต้น: ${new Date().toLocaleTimeString()}`);
        
        try {
            // สร้าง temp config สำหรับ locale นี้
            console.log(`📝 สร้าง config สำหรับ ${locale}...`);
            const tempConfigContent = createLocaleConfig(locale);
            const configFileName = `astro.config.${locale}.mjs`;
            fs.writeFileSync(configFileName, tempConfigContent);
            
            console.log(`🚀 เริ่ม build สำหรับ ${locale} (Memory: ${buildOptions.memory}MB)...`);
            const startTime = Date.now();
            
            execSync(`cross-env NODE_OPTIONS="--max-old-space-size=${buildOptions.memory}" astro build --config ${configFileName}`, {
                ...buildOptions
            });
            
            const endTime = Date.now();
            const duration = Math.round((endTime - startTime) / 1000);
            
            // ย้าย dist ไปยัง folder ของ locale
            if (fs.existsSync('dist')) {
                const distDir = `dist-${locale}`;
                if (fs.existsSync(distDir)) {
                    fs.rmSync(distDir, { recursive: true });
                }
                fs.renameSync('dist', distDir);
                console.log(`📁 ย้าย output ไป: ${distDir}`);
            }
            
            // ลบ temp config
            fs.unlinkSync(configFileName);
            
            successCount++;
            console.log(`✅ [${i + 1}/${locales.length}] Build สำเร็จสำหรับ ${locale.toUpperCase()} (${duration}s)`);
            console.log(`📊 Progress: ${successCount}/${locales.length} สำเร็จ, ${failCount} ล้มเหลว`);
            
        } catch (error) {
            failCount++;
            console.error(`❌ [${i + 1}/${locales.length}] Build ล้มเหลวสำหรับ ${locale.toUpperCase()}`);
            console.error(`💥 Error: ${error.message.split('\n')[0]}`);
            console.log(`📊 Progress: ${successCount}/${locales.length} สำเร็จ, ${failCount} ล้มเหลว`);
            
            // ลบ temp config ถ้ามี
            const configFileName = `astro.config.${locale}.mjs`;
            if (fs.existsSync(configFileName)) {
                fs.unlinkSync(configFileName);
            }
        }
    }
    
    console.log('\n🎉 Build process เสร็จสิ้น!');
    console.log(`📈 สรุปผลลัพธ์: ${successCount}/${locales.length} สำเร็จ, ${failCount} ล้มเหลว`);
    
    if (successCount > 0) {
        console.log('\n📁 โฟลเดอร์ที่สร้างสำเร็จ:');
        locales.forEach(locale => {
            if (fs.existsSync(`dist-${locale}`)) {
                console.log(`   📂 dist-${locale}/`);
            }
        });
    }
}

function createLocaleConfig(locale) {
    return `
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
    output: 'static',
    build: {
        concurrency: 1,
        inlineStylesheets: 'never',
        split: false,
        assets: '_astro'
    },
    vite: {
        build: {
            chunkSizeWarningLimit: 50000,
            minify: false,
            sourcemap: false,
            rollupOptions: {
                output: {
                    manualChunks: undefined, // ปิด manual chunks
                    maxParallelFileOps: 1,
                }
            },
            target: 'esnext'
        },
        resolve: {
            alias: {
                '@components': new URL('./src/components', import.meta.url).pathname,
            }
        },
        optimizeDeps: {
            noDiscovery: true,
            include: []
        }
    },
    integrations: [
        starlight({
            title: 'SACRED - ${locale.toUpperCase()}',
            description: 'Scripture Archive - ${locale}',
            expressiveCode: false,
            defaultLocale: '${locale}',
            locales: {
                ${locale}: {
                    label: '${getLocaleLabel(locale)}',
                    lang: '${getLocaleLang(locale)}',
                }
            }
        }),
    ],
});
`;
}

function getLocaleLabel(locale) {
    const labels = {
        'romn': 'Roman',
        'thai': 'ไทย', 
        'mymr': 'မြန်မာ',
        'sinh': 'සිංහල',
        'deva': 'देवनागरी',
        'khmr': 'ខ្មែរ',
        'laoo': 'ລາວ',
        'lana': 'ᩃᨶ᩠ᨶ'
    };
    return labels[locale] || locale;
}

function getLocaleLang(locale) {
    const langs = {
        'romn': 'en',
        'thai': 'th',
        'mymr': 'my', 
        'sinh': 'si',
        'deva': 'hi',
        'khmr': 'kh',
        'laoo': 'lo',
        'lana': 'ln'
    };
    return langs[locale] || 'en';
}

// เรียกใช้งาน
buildByLocale().catch(console.error);