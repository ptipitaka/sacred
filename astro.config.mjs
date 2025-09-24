import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { sidebarConfig } from './python/md/navigator.js';

// https://astro.build/config
export default defineConfig({
  esbuild: {
    loader: {
      '.jsonc': 'json',
    },
  },
  vite: {
    // Add the alias for @components here
    resolve: {
      alias: {
        '@components': '/workspace/src/components',
      },
    },
    optimizeDeps: {
      exclude: ['@astrojs/starlight'],
    },
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
      expressiveCode: {
        themes: [],
        useThemedScrollbars: false,
        useThemedSelectionColors: false,
      },
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