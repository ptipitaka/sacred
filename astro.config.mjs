import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js';

// https://astro.build/config
export default defineConfig({
    vite: {
        resolve: {
            alias: {
                '@components': '/src/components',
                '@layouts': '/src/layouts',
                '@assets': '/src/assets',
                '@utils': '/src/utils',
                '@content': '/src/content',
            },
        },
    },
    integrations: [
        starlight({
            title: 'SACRED',
            description: 'Scripture Archive of Canonical References, Editions, Digital corpus',
            logo: {
                src: './src/assets/logo.svg',
                // หรือถ้าต้องการใช้ favicon ที่มีอยู่
                // src: './public/favicon.svg',
            },
            social: [
                {
                    label: 'GitHub',
                    icon: 'github',
                    href: 'https://github.com/ptipitaka/sacred'
                }
            ],
            customCss: [
                './src/assets/css/global.css',
                './src/assets/css/fonts.css',
                './src/assets/css/annotations.css',
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
                romn: {
                    label: 'Roman',
                    lang: 'en',
                },
            },
            sidebar: sidebarConfig
        }),
    ],
    trailingSlash: 'always',
    output: 'static',
});