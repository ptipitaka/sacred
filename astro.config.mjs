import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js';

import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
  // Server-side rendering for dynamic content
  output: 'server',
  
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
    // Production build optimizations - minimize bundle size
    build: {
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            if (id.includes('node_modules')) {
              if (id.includes('@astrojs/starlight')) return 'starlight';
              return 'vendor';
            }
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
    // Optimized for smaller function size - exclude images from functions
    webAnalytics: { enabled: true },
    functionPerRoute: true, // Split routes to reduce individual function size
    edgeMiddleware: false,
    maxDuration: 15,
    // Images stay as static assets, not bundled in functions
    includeFiles: [],
    excludeFiles: [
      'python/**/*',
      'work_around/**/*', 
      'public/tipitaka/**/*.{md,txt,log,jpg,jpeg,png,gif,webp}'
    ]
  }),
});