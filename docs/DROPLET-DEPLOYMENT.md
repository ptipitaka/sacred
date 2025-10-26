# DigitalOcean Droplet Deployment Guide

## 1. เตรียม Droplet

### สเปกแนะนำ

- **โปรดักชัน (เสิร์ฟ static)**: Basic Droplet (Premium AMD/Intel) 1 vCPU / 2 GB RAM / 50 GB SSD เพียงพอสำหรับผู้ใช้พร้อมกัน ~20 คน เพราะ nginx เสิร์ฟไฟล์จาก `dist` โดยแทบไม่ใช้ CPU
- **ช่วง Build ใหญ่ (>50k หน้า)**: Resize ชั่วคราวเป็น 4 vCPU / 8 GB RAM (หรือตั้ง Droplet ชั่วคราวในขนาดนี้แล้ว build เสร็จค่อยลดสเปก) เพื่อให้ `npm run build` เสร็จไวและไม่หมดหน่วยความจำ
- **Build ผ่าน GitHub Actions**: เลือก Droplet เบาๆ ที่มี nginx พร้อมใช้งาน (เช่น Basic 1 vCPU / 1–2 GB RAM พร้อม Ubuntu/Nginx Marketplace Image) ก็พอ เพราะขั้นตอน build จะเกิดบน GitHub Runner แทน
- **One-Click Image ที่ใช้**: สำหรับการเริ่มต้นที่ต้องการความสะดวก เลือก "Node.js 20 (Ubuntu 22.04)" บน DigitalOcean Marketplace ได้เลย มี Node.js LTS + npm ติดตั้งมาให้ และยังสามารถใช้สำหรับการ build บน Droplet หากจำเป็น
- **สเกล Storage**: เก็บภาพขนาดใหญ่ไว้บน DigitalOcean Spaces + CDN เพื่อลด IO/พื้นที่บน Droplet หลัก เหลือเฉพาะ HTML/JS/CSS บนเครื่อง
- **เผื่อโต**: ถ้าคาดว่าจะมีทราฟฟิกมากขึ้นในอนาคต ให้พิจารณา Load Balancer + Droplet หลายเครื่อง หรือย้ายไฟล์ไปใช้ CDN/front door เพิ่มเติม

1. เข้า https://cloud.digitalocean.com/droplets แล้วสร้าง Droplet ใหม่
2. เลือกสเปกตามคำแนะนำด้านบน (1 vCPU / 2 GB RAM สำหรับโปรดักชัน และขยายเป็น 4 vCPU / 8 GB RAM ช่วง build)
3. เลือก Image เป็น Node.js 20 (Ubuntu 22.04) One-Click หรือ Ubuntu LTS แล้วติดตั้ง Node.js เองหากต้องการ
4. ตั้งชื่อ host และผูก SSH key เพื่อความปลอดภัย

## 2. ติดตั้งแพ็กเกจพื้นฐานบน Droplet

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx build-essential curl
```

ติดตั้ง Node.js LTS (20.x):
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

> ถ้าใช้ Node.js 20 One-Click อยู่แล้ว หรือเลือก build ผ่าน GitHub Actions (Droplet เสิร์ฟ static อย่างเดียว) สามารถข้ามขั้นตอนติดตั้ง Node.js ได้

ถ้าต้องการใช้ pnpm/yarn ให้ติดตั้งเพิ่ม

## 3. ดึงโค้ดและตั้งค่าโปรเจ็กต์

```bash
sudo mkdir -p /var/www/sacred
sudo chown $USER:$USER /var/www/sacred
cd /var/www/sacred
git clone https://github.com/ptipitaka/sacred.git .
npm ci
```

> ถ้าเลือกใช้ GitHub Actions สำหรับ build/rsync ให้ข้ามการ clone repository บน Droplet และสร้างเพียงไดเรกทอรีปลายทาง (เช่น `/var/www/html`) พร้อมปรับสิทธิ์แทน

สร้างไฟล์ `.env` (ถ้ามีตัวแปรที่จำเป็น) และเก็บค่าไว้ใน Droplet เท่านั้น

## 4. Build และ Deploy

### ตัวเลือก A: Build บน Droplet

รัน build เพื่อทดสอบ:
```bash
npm run build
```

ไฟล์ผลลัพธ์จะอยู่ที่ `dist/`. คัดลอกไปยังไดเรกทอรีที่ nginx เสิร์ฟ (ตัวอย่างใช้ `/var/www/sacred/dist-live`):
```bash
sudo rm -rf /var/www/sacred/dist-live
sudo cp -r dist /var/www/sacred/dist-live
```

หากต้องการใช้ root เริ่มต้นของ nginx (`/var/www/html`)
```bash
sudo rm -rf /var/www/html/*
sudo cp -r dist/* /var/www/html/
```

ให้ปรับ `server { root ... }` ใน nginx ให้ตรงกับไดเรกทอรีที่เลือกไว้

### ตัวเลือก B: Build ด้วย GitHub Actions แล้ว Deploy อัตโนมัติ

1. สร้าง SSH key เฉพาะสำหรับ CI บนเครื่องนักพัฒนา:
     ```bash
     ssh-keygen -t ed25519 -C "github-actions@sacred" -f ~/.ssh/sacred_ci
     ```
     - เพิ่ม public key (`sacred_ci.pub`) เข้าไปใน `~/.ssh/authorized_keys` ของ Droplet (ผู้ใช้ที่ใช้ deploy เช่น `deploy` หรือ `root`)
     - เก็บ private key เป็น GitHub Secret ชื่อ `DROPLET_SSH_KEY`
     - เพิ่มค่าอื่นใน Secrets: `DROPLET_HOST`, `DROPLET_USER`, `DEPLOY_PATH` (เช่น `/var/www/html` หรือ `/var/www/sacred/dist-live`)

2. ถ้าจะเขียนลง `/var/www/html` ให้ตั้งสิทธิ์ไว้ก่อนหนึ่งครั้งบน Droplet:
     ```bash
     sudo mkdir -p /var/www/html
     sudo chown -R deploy:deploy /var/www/html  # เปลี่ยนเป็นผู้ใช้ที่ใช้เชื่อม
     ```

3. ตัวอย่าง workflow `.github/workflows/deploy.yml` ที่ build และ rsync ไฟล์ไปยัง Droplet:

```yaml
name: Deploy Astro

on:
    push:
        branches: [main]

jobs:
    build-deploy:
        runs-on: ubuntu-latest
        steps:
            - uses: actions/checkout@v4

            - name: Use Node.js 20
                uses: actions/setup-node@v4
                with:
                    node-version: 20
                    cache: npm

            - name: Install dependencies
                run: npm ci

            - name: Build
                run: npm run build

            - name: Prepare SSH
                run: |
                    mkdir -p ~/.ssh
                    echo "${{ secrets.DROPLET_SSH_KEY }}" > ~/.ssh/id_ed25519
                    chmod 600 ~/.ssh/id_ed25519
                    ssh-keyscan -H ${{ secrets.DROPLET_HOST }} >> ~/.ssh/known_hosts

            - name: Deploy via rsync
                run: |
                    rsync -avz --delete dist/ ${{ secrets.DROPLET_USER }}@${{ secrets.DROPLET_HOST }}:${{ secrets.DEPLOY_PATH }}/

            - name: Reload nginx
                run: |
                    ssh -i ~/.ssh/id_ed25519 ${{ secrets.DROPLET_USER }}@${{ secrets.DROPLET_HOST }} 'sudo systemctl reload nginx'
```

CI Runner จะ build โปรเจ็กต์แล้วส่งไฟล์ขึ้น Droplet โดยตรง ทำให้ Droplet ไม่ต้องใช้ CPU/RAM สูงและไม่ต้องติดตั้ง Node.js

## 5. ตั้งค่า nginx ให้เสิร์ฟ static site

สร้างไฟล์ `/etc/nginx/sites-available/sacred`:
```nginx
server {
    listen 80;
    server_name sacred.example.com; # เปลี่ยนเป็นโดเมนของคุณ

    root /var/www/sacred/dist-live;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # ตั้ง header พื้นฐานสำหรับไฟล์ภาพขนาดใหญ่ (ถ้ายังอยู่ใน dist)
    location ~* \.(png|jpg|jpeg|gif|svg)$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
```

ถ้าเลือกใช้ `/var/www/html` ให้ปรับ `root /var/www/html;` และแก้เส้นทางใน workflow/สคริปต์ deploy ให้สอดคล้อง

เปิดใช้งานและ reload nginx:
```bash
sudo ln -s /etc/nginx/sites-available/sacred /etc/nginx/sites-enabled/sacred
sudo nginx -t
sudo systemctl reload nginx
```

ถ้าต้องการ HTTPS ให้ติดตั้ง certbot:
```bash
sudo snap install --classic certbot
sudo certbot --nginx -d sacred.example.com
```

## 6. สคริปต์ deploy อัตโนมัติ (ตัวอย่าง)

สร้างไฟล์ `/usr/local/bin/deploy-sacred.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd /var/www/sacred

git fetch origin main
git reset --hard origin/main
npm ci
npm run build
sudo rm -rf /var/www/sacred/dist-live
sudo cp -r dist /var/www/sacred/dist-live
sudo systemctl reload nginx
```

ให้สิทธิ์รัน:
```bash
sudo chmod +x /usr/local/bin/deploy-sacred.sh
```

ตั้ง cron หรือ GitHub webhook ให้เรียก script ทุกครั้งที่มีการอัปเดต (เช่นผ่าน `curl` หรือ `ssh`)

## 7. จัดการไฟล์ภาพขนาดใหญ่

- ถ้า Droplet ไม่น่าจะรองรับไฟล์สแกนทั้งหมด ให้คงการเก็บภาพไว้บน Spaces + CDN
- แก้ URL ในโปรเจ็กต์ให้ชี้ไป `https://<bucket>.<region>.cdn.digitaloceanspaces.com/...`
- nginx จะเสิร์ฟเฉพาะ HTML/JS/CSS และดึงภาพจาก CDN อัตโนมัติ

## 8. การสำรองข้อมูลและ Monitoring

- ใช้ DigitalOcean Snapshots หรือ rsync สำรอง `/var/www/sacred` เป็นประจำ
- เปิด Monitoring ของ DO และตั้ง alert หาก CPU/RAM สูงผิดปกติ

## 9. การอัปเดตระบบ

```bash
sudo apt update && sudo apt upgrade -y
sudo npm install -g npm@latest  # ถ้าต้องการอัปเดต npm
```

ตรวจสอบว่าบริการ nginx ทำงานปกติหลังการอัปเดตทุกครั้ง

---

ด้วยขั้นตอนนี้ Static site จะถูกรันบน Droplet และคุณควบคุมทุกอย่างได้เต็มที่ โดยยังสามารถผนวก Spaces/CDN สำหรับไฟล์ขนาดใหญ่ได้ตามต้องการ
