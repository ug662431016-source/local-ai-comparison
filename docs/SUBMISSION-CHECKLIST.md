# รายการตรวจงานก่อนส่ง

รายการนี้ใช้เชื่อมไฟล์ในโปรเจกต์กับเกณฑ์ `DevOps26Class_performance.pdf` โดยสรุปหมวดเพื่อช่วยตรวจตนเอง ผลตรวจเอกสารไม่ใช่การรับรองคะแนนจากผู้สอน และหัวข้อที่ต้องสาธิตต้องมีหลักฐานรันจริงประกอบ

ขอบเขตตามที่ผู้จัดทำยืนยัน: อาจารย์ให้ทำผ่าน Docker เท่านั้น จึงตรวจการติดตั้งโมเดลและรันระบบใน Docker ชื่อเกณฑ์ในตารางคงตาม PDF โดยไม่เพิ่มการติดตั้ง Ollama บน host เป็นงานที่ขาด

## ภาพรวมตามเกณฑ์

| เกณฑ์ | น้ำหนัก | หลักฐานและสถานะ |
|---|---:|---|
| f1 Define/research problem | ×1 | README อธิบายปัญหาและวัตถุประสงค์ ผู้จัดทำควรเชื่อมกับงานที่ตนต้องการแก้ |
| f2 Identify/explore methods | ×1 | README อธิบายวิธีถาม–ตอบ วงรอบ Agent และการเรียกใช้ผ่าน Docker |
| f3 Perform analyses | ×1 | ผลเดิมครบและวิเคราะห์คำตอบ เวลา คำตอบผิด และ truncation |
| f4 Design solution | ×1 | ARCHITECTURE.md อธิบายส่วนประกอบ endpoint และวงรอบ Agent |
| f5 Develop conclusions | ×1 | README สรุปตามข้อมูลชุดเล็กและเปิดเผยข้อจำกัด |
| f6 Present analysis/conclusions | ×1 | มีแนวทางนำเสนอ ผู้จัดทำต้องนำเสนอและตอบคำถามด้วยตนเอง |
| f7 Organized README documentation | ×2 | มี README และลิงก์เอกสาร/ผล ต้องตรวจซ้ำหลังเพิ่มผลใหม่ |
| f8 Submit given GitHub repository | ×2 | ยังไม่ยืนยันส่ง repo ที่กำหนด ต้องตรวจ remote, add/commit/push และเปิด GitHub ตรวจ |
| f9 Run locally: Totally local Agentic | ×4 | Qwen+JSON ใช้โมเดล local ใน Docker ทำ demo ผ่าน 7 checks มี tool trace และไฟล์จริง |
| f10 Infrastructure as Code | ×3 | Compose config/build Agent/MCP ผ่าน และรัน container ตรวจงานจริงแล้ว ดู evidence/docker-verification-json.json และ mcp-probe.json |
| f11 Architecture | ×1 | มีแผนภาพบริการใน Docker การเชื่อมจาก client และ MCP ทางเลือก |
| f12 Multiple model test | ×2 | ผลเดิม Qwen/Llama 24 คำตอบ มีการประเมินและข้อจำกัด |
| f13 Connect from outside to Docker Agentic AI เช่น VS Code/Terminal/Web | ×4 | Terminal สั่ง Agent container และ Python Agent บน Mac → Docker ผ่านจริง; มี Continue Chat เดิม ส่วน Continue Agent UI ยังไม่ทดสอบ |
| f14 Model installed locally and inside Docker | ×4 | ตามขอบเขต Docker ที่ผู้สอนกำหนด มีหลักฐานโมเดลทั้งสองใน Docker พร้อม digest และผล inference ใน evidence/environment-docker.json |


## สิ่งที่จัดเตรียมแล้ว

- [x] อธิบายปัญหา วัตถุประสงค์ วิธีทดลอง การออกแบบ และข้อจำกัด
- [x] แก้จำนวนผลเดิมเป็น 12 รอบ/24 คำตอบ/8 prompt ไม่ซ้ำ
- [x] ทำสารบัญผลและ prompt ครบ โดยคงคำตอบและเวลาเดิม
- [x] ระบุ Qwen ถูกตัด 2 คำตอบ และ JSON ว่าง 1 ไฟล์โดยไม่แต่งผล
- [x] เพิ่มแผนภาพสถาปัตยกรรมและวงรอบ Agent
- [x] แยก endpoint ภายใน Docker `ollama:11434` กับ endpoint สำหรับ client `localhost:11434`
- [x] แยก Continue Chat ออกจากหลักฐาน Agent ที่เรียกเครื่องมือ
- [x] เพิ่มแนวทางนำเสนอและรายการหลักฐานที่ต้องจับคู่

## ต้องตรวจจากการรันจริง

- [x] Compose config ผ่านและตรวจคอนเทนเนอร์ Ollama ทำงานใน `evidence/environment-docker.json`
- [x] เก็บเวอร์ชัน Docker/Compose/Ollama, digest และรายชื่อโมเดลจาก Docker ใน `evidence/environment-docker.json`
- [x] รัน Agent จาก Terminal ใน container ชั่วคราวไปยัง Docker Ollama สำเร็จ: Qwen+JSON รอบ `20261019_190411_562205`
- [x] รัน Python Agent บน Mac ไปยัง Docker endpoint จริง รอบ `20261019_190955_157226` ผ่าน 7 checks
- [x] log รอบ Qwen+JSON เห็นโมเดลเลือกเครื่องมือ อ่านต้นฉบับก่อนเขียน และอ่านผลกลับหลังเขียน
- [x] `checklist.md` รอบผ่านมี 3 checkbox ตามข้อมูลเดิมและลำดับเดิม ตรวจครบ 7 checks
- [x] เก็บรายชื่อโมเดลทั้งสองและผลเรียกใช้ Ollama ภายใน Docker
- [x] MCP handshake, tools/list, tools/call เขียน/อ่านไฟล์จริง และปฏิเสธ path traversal ผ่านใน `evidence/mcp-probe.json`
- [x] เก็บ log native tool calling ของสองโมเดลและ Llama JSON ที่ยัง incomplete พร้อมอธิบายใน README

รายการที่ติ๊กมีหลักฐานจริงในโฟลเดอร์; รายการไม่ติ๊กยังต้องทำเพิ่ม การผ่าน unit tests หรือ syntax checks ช่วยตรวจโค้ด แต่ไม่แทนการรันโมเดลจริง

ผลอ้างอิง: [metadata Docker](../evidence/environment-docker.json), [Agent Qwen+JSON ผ่าน](../agent_results/20261019_190411_562205.json), [MCP ผ่าน](../evidence/mcp-probe.json) และ [ชุดตรวจ Docker](../evidence/docker-verification-json.json)

รุ่นสุดท้าย: [Qwen ใน container](../agent_results/20261019_190946_794703.json), [Qwen จาก Mac ไป Docker](../agent_results/20261019_190955_157226.json), [ทุก run](../evidence/AGENT-RUNS.md), [ไฟล์ผลจริง](../evidence/demo-success/checklist.md) และ [unit tests 21 ข้อ](../evidence/unit-tests.txt)

## หลักฐาน Agent ที่อ่านแล้วต้องตอบได้

1. ใช้โมเดลใด protocol ใด และ endpoint ใด
2. ป้าย `runtime_declared` มีหลักฐานโปรเซส/คอนเทนเนอร์รองรับหรือไม่
3. โมเดลเรียกเครื่องมืออะไร ด้วย arguments ใด และได้รับผลจริงอะไร
4. ไฟล์ก่อนทำและหลังทำอยู่ที่ใด เนื้อหาตรงโจทย์หรือไม่
5. สถานะ `passed`/`incomplete` มาจากการตรวจใด มีขั้นใดผิดพลาดหรือถูกตัด

## ก่อนส่ง GitHub

- [ ] ตรวจว่า repository เป็นปลายทางที่ผู้สอนกำหนด
- [ ] รัน `git status --short` และตรวจไฟล์ที่จะส่ง ไม่พึ่งเพียงว่าตั้ง remote แล้ว
- [ ] เพิ่มเฉพาะโค้ด เอกสาร ผลทดลอง และภาพที่ต้องใช้ ไม่เพิ่ม weights หรือ API key
- [ ] ตรวจว่าผลเดิมและผลใหม่ที่ใช้อ้างอิงถูก add/commit จริง
- [ ] push แล้วเปิด GitHub ตรวจ README, Mermaid, ลิงก์ผล และภาพ
- [ ] ตรวจคำสั่งติดตั้งจากเอกสารบนสภาพแวดล้อมที่ต้องใช้สาธิต

ต้องตรวจ Git จากโฟลเดอร์ที่จะส่งจริง การจัดไฟล์ใน working copy หรือการตั้ง remote ไม่ได้ยืนยันว่าไฟล์ถูกส่งขึ้น GitHub แล้ว

## แนวทางสาธิตสั้น ๆ

1. ปัญหาและเป้าหมาย: เหตุใดต้องตรวจทั้งคำตอบและการลงมือทำงาน
2. แผนภาพ: Terminal/VS Code → บริการใน Docker → โมเดลใน Docker volume
3. ผลเดิม: เปิดตัวอย่างถูก ตัวอย่างผิด และตัวอย่างถูกตัดโดยไม่แก้คำตอบเดิม
4. Agent: รับโจทย์ → เรียกเครื่องมือ → สร้างไฟล์ → อ่านตรวจกลับ พร้อม log
5. แสดงรายชื่อโมเดลใน Docker และไฟล์งานที่บันทึกผ่าน bind mount
6. สรุปสิ่งที่ทำได้ ข้อจำกัด และสิ่งที่ยังไม่ได้ทดสอบ

ไม่จำเป็นต้องเพิ่ม MCP, CrewAI หรือเว็บ To-do เพียงเพราะมีชื่ออยู่ในไฟล์ ควรยึดเกณฑ์ผู้สอนและหลักฐานของระบบที่เลือกนำเสนอ
