import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeRapide from 'starlight-theme-rapide'
import { sidebarConfig } from './python/md/navigator.js'

// https://astro.build/config
export default defineConfig({
	vite: {
		resolve: {
			alias: {
				'@components': new URL('./src/components', import.meta.url).pathname,
			}
		},
		server: {
			fs: {
				// เพิ่มเวลา timeout สำหรับการโหลดไฟล์ (หน่วยเป็นมิลลิวินาที)
				// กำหนดให้เป็น 250 วินาที เพื่อให้มีเวลาประมวลผลนานขึ้น
				watch: {
					awaitWriteFinish: {
						stabilityThreshold: 300000, // 5 minutes
						pollInterval: 1000
					}
				}
			}
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
            plugins: [starlightThemeRapide()],
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
