import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js'

// https://astro.build/config
export default defineConfig({
    vite: {
        plugins: [
            {
                name: 'jsonc-loader',
                transform(code, id) {
                    if (id.includes('.jsonc?raw')) {
                        return `export default ${JSON.stringify(code)};`;
                    }
                    return null;
                },
                load(id) {
                    if (id.includes('.jsonc?raw')) {
                        const fs = require('fs');
                        const actualPath = id.replace('?raw', '');
                        try {
                            const content = fs.readFileSync(actualPath, 'utf-8');
                            return `export default ${JSON.stringify(content)};`;
                        } catch (error) {
                            console.warn(`Could not load JSONC file: ${actualPath}`);
                            return `export default "";`;
                        }
                    }
                    return null;
                }
            }
        ],
        build: {
            rollupOptions: {
                output: {
                    manualChunks: {
                        'sidebar': ['./python/md/navigator.js'],
                        'starlight': ['@astrojs/starlight']
                    }
                }
            },
            chunkSizeWarningLimit: 1000
        },
        resolve: {
            alias: {
                '@components': new URL('./src/components', import.meta.url).pathname,
            }
        },
        optimizeDeps: {
            include: ['@astrojs/starlight']
        }              
    },
    integrations: [
        starlight({
            title: 'SACRED',
            description: 'Scripture Archive of Canonical References, Editions, Digital corpus',
            social: [{ 
                icon: 'github', 
                label: 'GitHub', 
                href: 'https://github.com/withastro/starlight' 
            }],
            expressiveCode: false,
            customCss: [
                './src/assets/css/global.css',
                './src/assets/css/fonts.css',
            ],
            defaultLocale: 'romn',
            locales: {
                mymr: {
                    label: 'မြန်မာ',
                    lang: 'my',
                },
                thai: {
                    label: 'ไทย',
                    lang: 'th',
                },
                sinh: {
                    label: 'සිංහල',
                    lang: 'si',
                },
                romn: {
                    label: 'Roman',
                    lang: 'en',
                },
                deva: {
                    label: 'देवनागरी',
                    lang: 'hi',
                },
                khmr: {
                    label: 'ខ្មែរ',
                    lang: 'kh',
                },
                laoo: {
                    label: 'ລາວ',
                    lang: 'lo',
                },
                lana: {
                    label: 'ᩃᨶ᩠ᨶ',
                    lang: 'ln',
                },
            },
            sidebar: sidebarConfig
        }),
    ],
});