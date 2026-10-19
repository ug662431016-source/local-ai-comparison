#!/usr/bin/env python3
"""ทดสอบคำถามข้อความกับ Ollama: python3 chat_input.py
ใช้ Python 3 และไลบรารีมาตรฐานเท่านั้น เปิด Docker/Ollama ก่อนรัน
ผลจริงจะบันทึกในโฟลเดอร์ results ข้างไฟล์นี้ ไม่มีประวัติสนทนาข้ามคำถาม
"""
import json
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


import os

BASE_URL = os.environ.get(
    'OLLAMA_URL',
    'http://localhost:11434'
).rstrip('/')
MODELS = ['qwen2.5-coder:1.5b', 'llama3.2:3b']
OPTIONS = {'temperature': 0, 'seed': 42, 'num_ctx': 4096, 'num_predict': 768}
SYSTEM = 'ตอบคำถามเป็นภาษาไทยอย่างชัดเจน กระชับ และถูกต้อง หากไม่ทราบให้บอกว่าไม่ทราบ'
SAMPLES = [
    '10 + 10 เท่ากับเท่าไร ตอบเฉพาะตัวเลข',
    'อธิบายว่า CPU และ RAM ต่างกันอย่างไร สำหรับผู้เริ่มต้น ไม่เกิน 5 ประโยค',
    'HTML, CSS และ JavaScript ทำหน้าที่ต่างกันอย่างไร ตอบเป็น 3 ข้อ',
    'สรุปข้อความนี้เป็น 2 ข้อ: มาลีมีเรียนตอนเช้า จึงเตรียมกระเป๋าตั้งแต่กลางคืน เธอตรวจตารางเรียนและใส่หนังสือให้ครบ ก่อนตั้งนาฬิกาปลุกสำหรับวันรุ่งขึ้น',
    'มีแอปเปิล 12 ลูก ให้เพื่อน 5 ลูก แล้วซื้อเพิ่ม 3 ลูก เหลือกี่ลูก อธิบายสั้น ๆ',
]
# ใช้ local connection โดยไม่ส่งผ่าน proxy ของระบบ
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request_json(path, data=None):
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE_URL + path, data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        with HTTP.open(req, timeout=600) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError('Ollama HTTP %s: %s' % (exc.code, detail)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError('ติดต่อ Ollama ไม่สำเร็จหรือหมดเวลา ตรวจว่า Docker และ container ollama เปิดอยู่: %s' % exc) from exc
    if 'error' in result:
        raise RuntimeError(str(result['error']))
    return result


def ask(model, prompt):
    start = time.perf_counter()
    result = request_json('/api/generate', {
        'model': model, 'prompt': prompt, 'system': SYSTEM,
        'stream': False, 'keep_alive': 0, 'options': OPTIONS,
    })
    if not result.get('done') or not result.get('response', '').strip():
        raise RuntimeError('ไม่ได้รับคำตอบที่สมบูรณ์จาก Ollama')
    return {
        'model': model, 'answer': result['response'],
        'elapsed_seconds': round(time.perf_counter() - start, 3),
        'load_seconds': round(result.get('load_duration', 0) / 1e9, 3),
        'total_seconds_ollama': round(result.get('total_duration', 0) / 1e9, 3),
        'output_tokens': result.get('eval_count'),
        'done_reason': result.get('done_reason'),
        'truncated': result.get('done_reason') == 'length',
    }


def display_text(text):
    """Keep valid Unicode readable and expose malformed surrogate code points."""
    return text.encode('utf-8', errors='backslashreplace').decode('utf-8')


def write_utf8_atomic(path, text):
    """Encode before opening a file and preserve the previous result on failure."""
    payload = text.encode('utf-8', errors='backslashreplace')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.chat-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save(record):
    folder = Path(__file__).resolve().parent / 'results'
    folder.mkdir(exist_ok=True)
    stem = folder / record['run_id']
    json_text = json.dumps(record, ensure_ascii=False, indent=2)
    lines = ['ทดสอบตอบคำถามทั่วไป', 'คำถาม: ' + record['prompt'],
             'เวลารวมเป็นเวลารอจริง รวมการโหลดโมเดลถ้ามี ไม่ใช่ความเร็วสร้างคำตอบล้วน',
             'แต่ละคำถามเริ่มใหม่ ไม่มีประวัติสนทนา', '']
    for row in record['results']:
        lines.append('โมเดล: ' + row['model'])
        if 'error' in row:
            lines.append('ข้อผิดพลาด: ' + row['error'])
        else:
            lines.extend(['เวลารวม: %s วินาที' % row['elapsed_seconds'],
                          'เวลาโหลดโมเดล: %s วินาที' % row['load_seconds'], row['answer']])
            if row['truncated']:
                lines.append('คำเตือน: คำตอบถึงขีดจำกัดโทเคน อาจยังไม่จบ')
        lines.append('')
    # Render both outputs before writing; malformed code points remain visible as escapes.
    text_output = '\n'.join(lines)
    write_utf8_atomic(stem.with_suffix('.json'), json_text)
    write_utf8_atomic(stem.with_suffix('.txt'), text_output)
    return stem.with_suffix('.txt')


def main():
    print('ทดสอบ AI รับ input เป็นข้อความ | พิมพ์ exit เพื่อออก')
    print('พิมพ์ /examples เพื่อดูชุดคำถามตัวอย่าง')
    print('โปรแกรมส่งคำถามเดียวกันให้ Qwen และ Llama ทีละตัว และบันทึกผลอัตโนมัติ')
    try:
        tags = request_json('/api/tags')
        installed = {m.get('name') for m in tags.get('models', [])}
        missing = [m for m in MODELS if m not in installed]
        if missing:
            print('ยังไม่มีโมเดลเหล่านี้ กรุณารันคำสั่งใน Terminal ก่อน:')
            for model in missing:
                print('docker exec -it ollama ollama pull ' + model)
            return
    except (RuntimeError, ValueError) as exc:
        print(display_text(str(exc)))
        return
    while True:
        prompt = input('\nคำถามของคุณ: ').strip()
        try:
            prompt.encode('utf-8')
        except UnicodeEncodeError:
            print('ข้อความมีอักขระที่เข้ารหัส UTF-8 ไม่ได้ กรุณาพิมพ์ใหม่ หรือพิมพ์ exit เพื่อออก')
            continue
        if prompt.lower() in ('exit', '/bye', 'quit'):
            break
        if not prompt:
            continue
        if prompt == '/examples':
            for i, question in enumerate(SAMPLES, 1):
                print('%d. %s' % (i, question))
            print('คัดลอกคำถามที่ต้องการมาวางที่ช่องคำถาม')
            continue
        record = {'run_id': datetime.now().strftime('%Y%m%d_%H%M%S_%f'),
                  'prompt': prompt, 'system': SYSTEM, 'options': OPTIONS,
                  'timing_note': 'Wall-clock time includes model loading when needed; no warm-up; models unloaded after each answer.',
                  'results': []}
        for model in MODELS:
            print('\nกำลังรอ %s ... (อาจใช้เวลาหลายนาที)' % model, flush=True)
            try:
                row = ask(model, prompt)
                print(display_text(row['answer']))
                print('เวลารวม: %.3f วินาที | เวลาโหลด: %.3f วินาที' % (row['elapsed_seconds'], row['load_seconds']))
                if row['truncated']:
                    print('คำตอบอาจยังไม่จบ เพราะถึงขีดจำกัดโทเคน')
            except (RuntimeError, ValueError) as exc:
                row = {'model': model, 'error': str(exc)}
                print('ข้อผิดพลาด:', display_text(str(exc)))
            record['results'].append(row)
            path = save(record)  # เก็บผลแต่ละตัวทันที แม้ตัวถัดไปเกิดปัญหา
        print('\nบันทึกผลแล้ว:', path)
        print('ตรวจความถูกต้องของคำตอบด้วยตนเองก่อนสรุปว่าโมเดลไหนดีกว่า')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nจบการทดสอบ')
