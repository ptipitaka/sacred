import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js';

import vercel from '@astrojs/vercel/serverless';

// https://astro.build/config
export default defineConfig({
  // Hybrid rendering: static by default, opt-in to SSR per page
  output: 'hybrid',
  
  vite: {
    resolve: {
      alias: {
        '@components': '/src/components',
        '@assets': '/src/assets',
        '@utils': '/src/utils',
        '@content': '/src/content',
        '@types': '/src/types',
      },
    },
    // Production build optimizations
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'starlight': ['@astrojs/starlight'],
          }
        }
      }
    }
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

  adapter: vercel({
    // Vercel best practices for Astro
    webAnalytics: { enabled: true },
    speedInsights: { enabled: true },
    imageService: true,
    imagesConfig: {
      sizes: [640, 750, 828, 1080, 1200, 1920, 2048],
      formats: ['image/webp'],
      minimumCacheTTL: 86400, // 24 hours
    },
    functionPerRoute: false, // Bundle API routes together for better cold starts
    edgeMiddleware: false, // Use serverless for better compatibility
    maxDuration: 30, // 30 seconds max for functions
  }),
});