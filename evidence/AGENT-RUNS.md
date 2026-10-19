# ผลทดสอบ Agent จริง

ผลทุกครั้งถูกรักษาไว้ รวมรอบที่ไม่ผ่าน ตารางนี้แยกจากผลเปรียบเทียบถาม–ตอบใน results/

| รอบ | โมเดล | Protocol | ผลตรวจ | Tool calls | วินาที |
|---|---|---|---|---:|---:|
| [20261019_190250_185723](../agent_results/20261019_190250_185723.json) | llama3.2:3b | native | incomplete | 3 | 14.78 |
| [20261019_190305_604987](../agent_results/20261019_190305_604987.json) | qwen2.5-coder:1.5b | native | incomplete | 0 | 6.394 |
| [20261019_190352_584807](../agent_results/20261019_190352_584807.json) | llama3.2:3b | json | incomplete | 5 | 18.645 |
| [20261019_190411_562205](../agent_results/20261019_190411_562205.json) | qwen2.5-coder:1.5b | json | passed | 3 | 9.116 |
| [20261019_190733_484809](../agent_results/20261019_190733_484809.json) | llama3.2:3b | json | incomplete | 6 | 15.31 |
| [20261019_190749_089298](../agent_results/20261019_190749_089298.json) | qwen2.5-coder:1.5b | json | incomplete | 3 | 9.058 |
| [20261019_190758_270216](../agent_results/20261019_190758_270216.json) | qwen2.5-coder:1.5b | json | incomplete | 3 | 7.563 |
| [20261019_190946_794703](../agent_results/20261019_190946_794703.json) | qwen2.5-coder:1.5b | json | passed | 3 | 8.249 |
| [20261019_190955_157226](../agent_results/20261019_190955_157226.json) | qwen2.5-coder:1.5b | json | passed | 3 | 7.035 |
| [20261019_192257_558909](../agent_results/20261019_192257_558909.json) | qwen2.5-coder:1.5b | json | passed | 3 | 10.783 |

`passed` หมายถึงผ่านตัวตรวจงานสาธิตในรอบนั้น ไม่ได้ยืนยันว่าจะสำเร็จทุกครั้ง

`native` ในคอลัมน์ Protocol หมายถึง Ollama tool_calls; ไม่ได้หมายถึงติดตั้ง Ollama นอก Docker

ไฟล์จริงจากรอบที่ผ่านล่าสุด: [โน้ตต้นฉบับ](demo-success/notes.txt), [checklist ที่ Agent สร้าง](demo-success/checklist.md), [ที่มาและ SHA-256](demo-success/provenance.json)
