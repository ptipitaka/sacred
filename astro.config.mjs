import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeRapide from 'starlight-theme-rapide'
import { sidebarConfig } from './python/md/navigator.js'

// https://astro.build/config
export default defineConfig({
	output: 'static',
	build: {
		concurrency: 4, // เพิ่มเป็น 4 เพื่อความเร็ว
		assets: '_astro',
		inlineStylesheets: 'never',
		split: true,
	},
	vite: {
		assetsInclude: ['**/*.jsonc'],
		build: {
			target: 'esnext',
			chunkSizeWarningLimit: 5000,
			rollupOptions: {
				output: {
					manualChunks: (id) => {
						if (id.includes('node_modules/@astrojs/starlight')) {
							return 'starlight';
						}
						if (id.includes('node_modules')) {
							return 'vendor';
						}
						if (id.includes('src/components')) {
							return 'components';
						}
						if (id.includes('src/content/docs/thai')) {
							return 'content-thai';
						}
						if (id.includes('src/content/docs/mymr')) {
							return 'content-mymr';
						}
						if (id.includes('src/content/docs/sinh')) {
							return 'content-sinh';
						}
						if (id.includes('src/content/docs')) {
							return 'content-other';
						}
					},
					maxParallelFileOps: 4,
				}
			},
			minify: false, // ปิด minify ช่วงแรกเพื่อประหยัด memory
		},
		resolve: {
			alias: {
				'@components': new URL('./src/components', import.meta.url).pathname,
			}
		},
		optimizeDeps: {
			include: ['@astrojs/starlight']
		},
		ssr: {
			noExternal: ['@astrojs/starlight']
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
            plugins: [starlightThemeRapide()],
			customCss: [
				'./src/assets/css/global.css',
				'./src/assets/css/fonts.css',
			],
			expressiveCode: false, // ปิด expressive code เพื่อหลีกเลี่ยง jsonc error
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
