# TPTK Review Process & Status Management Guide

## 🔄 **Review Workflow Steps**

### **1. Draft → Review**
```bash
python python/utils/manage_review_status.py \
  --state review \
  --file "src/content/docs/thai/tipitaka/vi/para/1.mdx" \
  --updated-by "admin" \
  --notes "Ready for team review"
```
- เมื่อเนื้อหาพร้อมให้ทีมตรวจทาน
- **Hypothes.is**: ใช้ Private Group (RGMZekaj)

### **2. Review → Revision** 
```bash
python python/utils/manage_review_status.py \
  --state revision \
  --file "src/content/docs/thai/tipitaka/vi/para/1.mdx" \
  --updated-by "reviewer1" \
  --notes "Found issues in paragraph 3, need correction"
```
- เมื่อพบข้อผิดพลาดที่ต้องแก้ไข
- **Hypothes.is**: ยังใช้ Private Group (RGMZekaj)

### **3. Revision → Review**
```bash
python python/utils/manage_review_status.py \
  --state review \
  --file "src/content/docs/thai/tipitaka/vi/para/1.mdx" \
  --updated-by "editor1" \
  --notes "Fixed issues, ready for re-review"
```
- หลังแก้ไขแล้ว ส่งตรวจทานอีกครั้ง

### **4. Review → Approved**
```bash
python python/utils/manage_review_status.py \
  --state approved \
  --file "src/content/docs/thai/tipitaka/vi/para/1.mdx" \
  --updated-by "reviewer1" \
  --notes "All corrections verified, content approved"
```
- เมื่อผ่านการตรวจทานแล้ว
- **Hypothes.is**: เปลี่ยนเป็น Public Annotation

### **5. Approved → Published**
```bash
python python/utils/manage_review_status.py \
  --state published \
  --file "src/content/docs/thai/tipitaka/vi/para/1.mdx" \
  --updated-by "admin" \
  --notes "Published to community"
```
- เปิดให้สาธารณชนเข้าถึงและแสดงความคิดเห็น
- **Hypothes.is**: Public Annotation (ชุมชนใช้ได้)

---

## 👥 **บทบาทและสิทธิ์:**

### **Admin:**
- เปลี่ยนสถานะได้ทุกขั้นตอน
- ควบคุม workflow ทั้งหมด
- มีสิทธิ์ใน Private Group (RGMZekaj)

### **REVIEW_TEAM Members:**
- ตรวจทานเนื้อหาใน Private Group
- สร้าง annotations ใน status: review, revision
- แนะนำการเปลี่ยนสถานะให้ Admin

### **Community:**
- เห็น annotations เฉพาะ status: approved, published
- สร้าง public annotations ได้
- ไม่เห็น private team discussions

---

## 📊 **Hypothes.is Group Assignment:**

| Review Status | Group Used | Annotation Type | Who Can See |
|---------------|------------|-----------------|-------------|
| draft         | REVIEW_TEAM | Private (RGMZekaj) | ทีมงานเท่านั้น |
| review        | REVIEW_TEAM | Private (RGMZekaj) | ทีมงานเท่านั้น |
| revision      | REVIEW_TEAM | Private (RGMZekaj) | ทีมงานเท่านั้น |
| approved      | Public | Public | ทุกคน |
| published     | Public | Public | ทุกคน |

---

## 🔍 **Batch Operations:**

### **Review ทั้ง Basket:**
```bash
python python/utils/manage_review_status.py \
  --state review \
  --basket vi \
  --updated-by "admin" \
  --notes "Ready for Vinaya basket review"
```

### **Approve หลายไฟล์:**
```bash
python python/utils/manage_review_status.py \
  --state approved \
  --pattern "src/content/docs/thai/tipitaka/vi/para/*.mdx" \
  --updated-by "reviewer1" \
  --notes "Batch approval after review"
```

---

## 📈 **History Tracking:**

ทุกการเปลี่ยนสถานะจะถูกบันทึกใน frontmatter:
```yaml
review:
  current: approved
  updated: '2025-10-10T11:25:43.630727'
  updated_by: reviewer1
  notes: All corrections verified
  history:
  - state: approved
    date: '2025-10-10T11:25:43.630727'
    updated_by: reviewer1
    notes: All corrections verified
    previous_state: review
  - state: review
    date: '2025-10-09T21:28:45.251024'
    updated_by: admin
    notes: Ready for team review
    previous_state: draft
```

---

## 🎯 **Best Practices:**

1. **ใช้ notes ที่ชัดเจน** - อธิบายเหตุผลของการเปลี่ยนสถานะ
2. **ตรวจสอบก่อน approve** - ใช้ Private Group หารือกันก่อน
3. **Batch operations** - เพื่อประสิทธิภาพในการจัดการจำนวนมาก
4. **Track history** - เก็บประวัติการเปลี่ยนแปลงไว้ครบถ้วน
