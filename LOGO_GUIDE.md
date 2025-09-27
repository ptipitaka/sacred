# คู่มือการใส่ Logo ในเว็บไซต์ SACRED

## วิธีที่ 1: ใช้การตั้งค่า Starlight (แนะนำ)

การตั้งค่านี้จะทำให้ logo ปรากฏในตำแหน่งมาตรฐานของ Starlight theme โดยอัตโนมัติ

### การตั้งค่าที่ได้ทำแล้ว:
- เพิ่ม logo config ใน `astro.config.mjs`
- คัดลอก favicon.svg ไปยัง `src/assets/logo.svg`

### ไฟล์ที่แก้ไข:
```javascript
// astro.config.mjs
starlight({
    title: 'SACRED',
    logo: {
        src: './src/assets/logo.svg',
    },
    // ... การตั้งค่าอื่นๆ
})
```

## วิธีที่ 2: ใช้ Custom Components

ถ้าต้องการปรับแต่งตำแหน่งหรือสไตล์ของ logo มากขึ้น

### Components ที่สร้างแล้ว:

#### 1. `src/components/Logo.astro`
- รองรับขนาดต่างๆ (sm, md, lg)
- มี hover effect
- รองรับ dark mode

#### 2. `src/components/Header.astro`
- Header component ที่มี logo
- Responsive design
- พร้อมใช้งานกับ navigation menu

### การใช้งาน Logo component:

```astro
---
import Logo from '@components/Logo.astro';
---

<!-- ขนาดต่างๆ -->
<Logo size="sm" />
<Logo size="md" />
<Logo size="lg" />

<!-- พร้อม custom class -->
<Logo size="md" class="my-custom-class" />
```

### การใช้งาน Header component:

```astro
---
import Header from '@components/Header.astro';
---

<Header />
```

## การปรับแต่ง Logo

### 1. เปลี่ยนไฟล์ logo:
- วางไฟล์ logo ใหม่ใน `src/assets/` 
- อัพเดต path ใน `astro.config.mjs`

### 2. ปรับขนาด logo ใน Starlight:
```javascript
logo: {
    src: './src/assets/logo.svg',
    replacesTitle: true, // ซ่อน title text
}
```

### 3. Logo สำหรับ Dark/Light mode:
```javascript
logo: {
    light: './src/assets/logo-light.svg',
    dark: './src/assets/logo-dark.svg',
}
```

## การทดสอบ

รันเซิร์ฟเวอร์พัฒนา:
```bash
npm run dev
```

จากนั้นเปิดเบราว์เซอร์ไปที่ `http://localhost:4321` เพื่อดูผลลัพธ์

## ตำแหน่งไฟล์ Logo

- **Logo หลัก**: `src/assets/logo.svg`
- **Favicon**: `public/favicon.svg` 
- **Logo components**: `src/components/Logo.astro`, `src/components/Header.astro`

## หมายเหตุ

- วิธีที่ 1 (Starlight config) เหมาะสำหรับใช้งานทั่วไป
- วิธีที่ 2 (Custom components) เหมาะสำหรับการปรับแต่งที่ซับซ้อน
- ไฟล์ logo ควรเป็น SVG เพื่อความคมชัดในทุกขนาด
- รองรับ responsive design และ dark mode