
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
    output: 'static',
    build: {
        concurrency: 4,
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
                    maxParallelFileOps: 4,
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
            title: 'SACRED - ROMN',
            description: 'Scripture Archive - romn',
            expressiveCode: false,
            defaultLocale: 'romn',
            locales: {
                romn: {
                    label: 'Roman',
                    lang: 'en',
                }
            }
        }),
    ],
});
