import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js';

import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
  vite: {
      resolve: {
          alias: {
              '@components': '/src/components',
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

  adapter: vercel(),
});