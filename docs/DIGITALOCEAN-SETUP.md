# DigitalOcean Spaces Setup Guide

## ขั้นตอนการตั้งค่า

### 1. สร้าง DigitalOcean Space

1. ไปที่ https://cloud.digitalocean.com/spaces
2. คลิก **Create a Space**
3. เลือก:
   - **Region**: Singapore (sgp1) หรือที่ใกล้ที่สุด
   - **Enable CDN**: ✅ เลือก (สำคัญ!)
   - **Space name**: ชื่อที่ต้องการ (เช่น `sacred-tipitaka`)
   - **File Listing**: Restricted (แนะนำ)
4. คลิก **Create Space**

### 2. สร้าง Spaces Access Keys

1. ไปที่ **Space ที่สร้างไว้** ใน https://cloud.digitalocean.com/spaces
2. คลิกที่ Space ของคุณ (เช่น `sacred-tipitaka`)
3. คลิกแท็บ **Settings** ทางซ้ายมือ
4. เลื่อนลงไปหา **Spaces access keys**
5. คลิก **Generate New Key**
6. ตั้งชื่อ: `GitHub Actions Deploy`
7. **คัดลอกและเก็บ Key และ Secret ไว้ทันที** (จะไม่แสดงอีกครั้ง!)

**หรือ** สร้างจากเมนูหลัก:
1. ไปที่ https://cloud.digitalocean.com/account/api/spaces
2. คลิก **Generate New Key**
3. ตั้งชื่อและเก็บ Key + Secret ไว้

### 3. ตั้งค่า GitHub Secrets

1. ไปที่ https://github.com/ptipitaka/sacred/settings/secrets/actions
2. คลิก **New repository secret** และเพิ่มทีละตัว:

   ```
   DO_SPACES_ACCESS_KEY = <Access Key จากขั้นตอน 2>
   DO_SPACES_SECRET_KEY = <Secret Key จากขั้นตอน 2>
   DO_SPACES_BUCKET = <Space name ที่สร้างไว้ เช่น sacred-tipitaka>
   DO_SPACES_REGION = <Region ที่เลือก เช่น sgp1>
   ```

### 4. Upload ไฟล์ภาพไป Spaces (ครั้งเดียว)

1. ติดตั้ง Python และ s3cmd:
   ```powershell
   pip install s3cmd
   ```

2. รัน upload script:
   ```powershell
   .\scripts\upload-images-to-spaces.ps1
   ```

3. ใส่ข้อมูลตามที่ถาม:
   - Bucket name
   - Region
   - Access Key
   - Secret Key

4. รอการ upload เสร็จ (อาจใช้เวลาหลายชั่วโมง สำหรับ 7.9GB)

### 5. ตรวจสอบไฟล์

1. ไปที่ Space ของคุณใน DigitalOcean
2. ควรเห็นโฟลเดอร์ `tipitaka/` พร้อมไฟล์ภาพทั้งหมด
3. เช็ค CDN URL:
   ```
   https://<bucket-name>.<region>.cdn.digitaloceanspaces.com/tipitaka/
   ```

### 6. Deploy ครั้งแรก

1. Commit และ push code:
   ```bash
   git add .
   git commit -m "Setup DigitalOcean Spaces deployment"
   git push origin main
   ```

2. GitHub Actions จะ build และ deploy อัตโนมัติ
3. ดูสถานะที่: https://github.com/ptipitaka/sacred/actions

### 7. เข้าถึง Site

Site จะอยู่ที่:
```
https://<bucket-name>.<region>.cdn.digitaloceanspaces.com/
```

## การใช้งาน Custom Domain (Optional)

หากต้องการใช้ domain ของตัวเอง:

1. ไปที่ Space settings → CDN
2. คลิก **Add a Custom Domain**
3. ใส่ domain (เช่น `sacred.example.com`)
4. เพิ่ม CNAME record ที่ DNS provider:
   ```
   CNAME: sacred → <bucket-name>.<region>.cdn.digitaloceanspaces.com
   ```
5. รอ DNS propagate (5-30 นาที)

## ราคา

**DigitalOcean Spaces: $5/เดือน**
- 250 GB storage
- 1 TB bandwidth (CDN)
- เพิ่มเติม: $0.02/GB storage, $0.01/GB bandwidth

สำหรับ site ของคุณ (7.9 GB):
- Storage: $5 (รวมในแพ็กเกจ)
- Bandwidth: ขึ้นกับ traffic
- **รวม: ~$5-10/เดือน**

## Troubleshooting

### Build ใช้เวลานาน
- ปกติครับ เพราะมีไฟล์เยอะ
- GitHub Actions รอได้ถึง 6 ชั่วโมง

### Build ไม่ผ่าน (Out of Memory)
- Workflow ใช้ RAM 8GB แล้ว
- หากยังไม่พอ แจ้งให้แก้ไข

### ไฟล์ภาพไม่โหลด
- เช็ค CDN URL ให้ถูกต้อง
- เช็คว่า Space เปิด public read
- เช็ค path ในโค้ดว่าชี้ไปที่ CDN

## Next Steps

1. ✅ Upload images ไป Spaces
2. ✅ ตั้งค่า GitHub Secrets
3. ✅ Push code เพื่อ deploy
4. Optional: ตั้งค่า custom domain
5. Optional: เพิ่มการ optimize รูปภาพ
