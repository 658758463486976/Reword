import sqlite3, time, requests, re, json
from bs4 import BeautifulSoup
import translators as ts

# ========================= CONFIG =========================
DB_PATH = r"C:\My_pc\___File_Sasha___\Automatisation\автоматизація_Reword\reword_upruve_db\reword_en_final.db"
TABLE_NAME = "word"
BATCH_SIZE = 200
DELAY = 0.81

# Пропуск слів
SKIP_WORDS = {
    "tiny", "itsy-bitsy", "miniature", "huge", "giant",
    "charming", "stunning", "graceful", "delighted", "joyful", "cheerful",
    "satisfied", "pleased", "contented", "pleasing", "pleasure",
    "delightful", "elegant", "beautiful", "gorgeous", "attractive", "pretty", "lovely"
}

# ===================== CACHE =========================
cache_en_uk = {}
cache_ru_uk = {}

# ===================== UTILS =========================
def fix_hash_tags(txt):
    if not txt: return txt
    txt = re.sub(r"#\s*(.*?)\s*#", r"#\1#", txt)
    txt = re.sub(r"(?<=[А-Яа-яA-Za-z])#", r" #", txt)
    txt = re.sub(r"#(?=[А-Яа-яA-Za-z])", r"# ", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    return txt.strip()

def fix_delimiter(text: str):
    if not text: return text
    text = text.replace(";", ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return ", ".join(dict.fromkeys(parts))

# ===================== TRANSLATE EN→UK =================
def translate_en_uk(text):
    if not text or not text.strip(): return None
    key = f"en_uk_{text}"
    if key in cache_en_uk: return cache_en_uk[key]
    time.sleep(DELAY)
    try:
        r = ts.translate_text(text, from_language='en', to_language='uk', translator='mymemory')
        if r and not re.search(r"[ёыэъ]", r.lower()):
            result = fix_hash_tags(r)
            cache_en_uk[key] = result
            return result
    except: pass
    try:
        r = ts.translate_text(text, from_language='en', to_language='uk', translator='bing')
        if r and not re.search(r"[ёыэъ]", r.lower()):
            result = fix_hash_tags(r)
            cache_en_uk[key] = result
            return result
    except: pass
    cache_en_uk[key] = None
    return None

# ===================== TRANSLATE RU→UK =================
def translate_ru_uk(text):
    if not text or not text.strip(): return None
    key = f"ru_uk_{text}"
    if key in cache_ru_uk: return cache_ru_uk[key]
    time.sleep(DELAY)
    try:
        r = ts.translate_text(text, from_language='ru', to_language='uk', translator='mymemory')
        if r and not re.search(r"[ёыэъ]", r.lower()):
            result = fix_hash_tags(r)
            cache_ru_uk[key] = result
            return result
    except: pass
    try:
        r = ts.translate_text(text, from_language='ru', to_language='uk', translator='bing')
        if r and not re.search(r"[ёыэъ]", r.lower()):
            result = fix_hash_tags(r)
            cache_ru_uk[key] = result
            return result
    except: pass
    cache_ru_uk[key] = None
    return None

# ===================== CAMBRIDGE =====================
HEADERS = {"User-Agent": "Mozilla/5.0"}
def get_cambridge(word):
    url = f"https://dictionary.cambridge.org/dictionary/english-ukrainian/{word.lower().replace(' ', '-')}"
    try:
        time.sleep(DELAY)
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200: return None
        soup = BeautifulSoup(r.text, 'html.parser')
        trans = soup.select_one("span.trans") or soup.select_one(".def-body span.trans")
        if trans:
            return fix_delimiter(fix_hash_tags(trans.get_text(strip=True)))
    except: pass
    return None

# ===================== DB ============================
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE UKR IS NOT NULL AND UKR!='' AND UKR!='NULL'")
    done = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE UKR IS NULL OR UKR='' OR UKR='NULL'")
    remain = cur.fetchone()[0]
    conn.close()
    return total, done, remain

def get_batch(offset=0):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    placeholders = ','.join('?' for _ in SKIP_WORDS)
    sql = f"""
        SELECT ID, word, transcription, rus, UKR, EXAMPLES_UKR
        FROM {TABLE_NAME}
        WHERE (UKR IS NULL OR UKR = '' OR UKR = 'NULL')
          AND lower(word) NOT IN ({placeholders})
        ORDER BY ID
        LIMIT {BATCH_SIZE} OFFSET ?
    """
    c.execute(sql, (*[w.lower() for w in SKIP_WORDS], offset))
    rows = c.fetchall()
    conn.close()
    return rows

def save_ukr(id_val, ukr):
    if not ukr or ukr in ["?", "—", "Переклад не знайдено"]: return False
    ukr = fix_delimiter(fix_hash_tags(ukr))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE {TABLE_NAME} SET UKR=? WHERE ID=?", (ukr, id_val))
    conn.commit()
    conn.close()
    return True

# ===================== EXAMPLE GEN ===================
def generate_example(word, ukr):
    if not word or not ukr: return None, None
    word = word.lower()
    if "satisfied" in word:
        return "He was #satisfied# with the result.", "Він був #задоволений# результатом."
    if "delighted" in word:
        return "She was #delighted# to hear the news.", "Вона була #захоплена# цією новиною."
    if "cheerful" in word:
        return "The room was #cheerful# and bright.", "Кімната була #весела# і світла."
    if "tiny" in word:
        return "She has a #tiny# house.", "У неї #крихітний# будинок."
    if "nose" in word:
        return "He has a #hooked nose#.", "У нього #гачкуватий ніс#."
    if "keep fit" in word:
        return "I try #to keep fit# every day.", "Я намагаюся #тримати себе у формі# щодня."
    if "lip" in word:
        return "She bit her #lower lip#.", "Вона прикусила #нижню губу#."
    return f"This is a #beautiful# {word}.", f"Це #гарний# {ukr}."

# ===================== MAIN =========================
def main():
    print("Reword: пакетний переклад + ПРІОРИТЕТ: Cambridge → RU→UK → EN→UK\n")
    total, done, remain = get_stats()
    print(f"Всього: {total} | Перекладено: {done} | Залишилось: {remain}\n")

    offset = 0
    updated_total = 0
    csv_lines = []

    while True:
        rows = get_batch(offset)
        if not rows:
            print("Усі слова оброблено!")
            break

        batch_data = []
        for row in rows:
            en = row['word'].strip()
            rus = row['rus'] or ""
            transcription = row['transcription'] or ""
            examples_ukr = row['EXAMPLES_UKR']

            cam = get_cambridge(en)
            en_uk = translate_en_uk(en) if not cam else None
            ru_uk = translate_ru_uk(rus) if rus else None

            if cam:
                final = cam
                source = "Cambridge"
            elif ru_uk:
                final = ru_uk
                source = "RU→UK"
            elif en_uk:
                final = en_uk
                source = "EN→UK"
            else:
                final = "?"
                source = "—"

            ex_en1, ex_uk1 = generate_example(en, final)
            ex_en2 = ex_uk2 = None
            if examples_ukr and examples_ukr.strip() and examples_ukr != "[]":
                try:
                    ex_list = json.loads(examples_ukr.replace("'", '"'))
                    if ex_list:
                        ex_en2 = ex_list[0].get('o', '').replace('#', f'#{en}#')
                        ex_uk2 = ex_list[0].get('t', '').replace('#', f'#{final}#')
                except: pass

            batch_data.append({
                'id': row['ID'], 'en': en, 'rus': rus, 'transcription': transcription,
                'cam': cam or "—", 'en_uk': en_uk or "—", 'ru_uk': ru_uk or "—",
                'final': final, 'source': source, 'status': 'pending',
                'ex_en1': ex_en1, 'ex_uk1': ex_uk1, 'ex_en2': ex_en2, 'ex_uk2': ex_uk2
            })

        # === СОРТУВАННЯ: спочатку без Cambridge, потім з Cambridge ===
        batch_data.sort(key=lambda x: (x['cam'] == "—", x['en'].lower()))

        # === ДИНАМІЧНА ШИРИНА ===
        cols = ['№', 'en', 'rus', 'cam', 'en_uk', 'ru_uk', 'final', 'source', 'status']
        data_for_width = []
        for i, d in enumerate(batch_data, 1):
            st = {'pending':'', 'saved':'Збережено', 'skipped':'Пропущено'}[d['status']]
            data_for_width.append([str(i), d['en'],  d['cam'], d['en_uk'], d['ru_uk'], str(i), d['final'], d['source'], st])
        data_for_width.append(["№", "ENG", "Cambridge", "EN→UK", "RU→UK", "Вибрано", "№", "Джерело", "Статус"])

        widths = [max(len(str(row[i])) for row in data_for_width) for i in range(len(cols))]
        row_format = "  ".join(f"{{:<{w}}}" for w in widths)
        separator = "─" * (sum(widths) + 2 * (len(widths) - 1))

        print(f"\n{separator}")
        print(f"ПАКЕТ {offset//BATCH_SIZE + 1} | 1-10 = редагувати | s = зберегти | n = пропустити | q = вихід")
        print(f"{separator}")
        print(row_format.format("№", "ENG", "Cambridge", "EN→UK", "RU→UK", "№", "Вибрано", "Джерело", "Статус"))
        print(f"{separator}")
        for i, d in enumerate(batch_data, 1):
            st = {'pending':'', 'saved':'Збережено', 'skipped':'Пропущено'}[d['status']]
            print(row_format.format(i, d['en'],  d['cam'], d['en_uk'], d['ru_uk'], i, d['final'], d['source'], st))
        print(f"{separator}")

        # === РЕЖИМ ===
        while True:
            choice = input("\nВибір: ").strip().lower()

            if choice == 'q':
                print(f"\nЗбережено: {updated_total} | Вихід.")
                break

            if choice == 's':
                saved = 0
                for d in batch_data:
                    if d['status'] == 'pending' and d['final'] not in ["?", "—"]:
                        if save_ukr(d['id'], d['final']):
                            d['status'] = 'saved'
                            saved += 1
                            line = f'"{d["en"]}";"{d["transcription"]}";"{d["final"]}";"{d["ex_en1"]}";"{d["ex_uk1"]}"'
                            if d["ex_en2"]: line += f';"{d["ex_en2"]}";"{d["ex_uk2"]}"'
                            csv_lines.append(line)
                updated_total += saved
                print(f"Збережено {saved} слів.")
                break

            if choice == 'n':
                for d in batch_data:
                    if d['status'] == 'pending': d['status'] = 'skipped'
                print(f"Пропущено {len([d for d in batch_data if d['status']=='skipped'])} слів.")
                break

            if choice.isdigit() and 1 <= int(choice) <= len(batch_data):
                idx = int(choice) - 1
                d = batch_data[idx]
                if d['status'] != 'pending':
                    print(f"Вже {'збережено' if d['status']=='saved' else 'пропущено'}.")
                    continue

                print(f"\nРедагування: {d['en']} (ID: {d['id']})")
                print(f"  C  = Cambridge : {d['cam']}")
                print(f"  E  = EN→UK     : {d['en_uk']}")
                print(f"  R  = RU→UK     : {d['ru_uk']}")
                print(f"  Поточний       : {d['final']} ← {d['source']}")

                while True:
                    sub = input("Вибір (C/E/R/Enter=зберегти/n=пропустити): ").strip().lower()
                    if sub == 'n':
                        d['status'] = 'skipped'
                        print("Пропущено.")
                        break
                    elif sub == '':
                        if d['final'] in ["?", "—"]:
                            print("Немає перекладу → пропущено.")
                            d['status'] = 'skipped'
                        else:
                            if save_ukr(d['id'], d['final']):
                                d['status'] = 'saved'
                                updated_total += 1
                                line = f'"{d["en"]}";"{d["transcription"]}";"{d["final"]}";"{d["ex_en1"]}";"{d["ex_uk1"]}"'
                                if d["ex_en2"]: line += f';"{d["ex_en2"]}";"{d["ex_uk2"]}"'
                                csv_lines.append(line)
                                print(f"Збережено: {d['final']}")
                        break
                    elif sub == 'c' and d['cam'] != "—":
                        d['final'] = d['cam']
                        d['source'] = "Cambridge"
                        print(f"Вибрано: {d['final']}")
                    elif sub == 'e' and d['en_uk'] != "—":
                        d['final'] = d['en_uk']
                        d['source'] = "EN→UK"
                        print(f"Вибрано: {d['final']}")
                    elif sub == 'r' and d['ru_uk'] != "—":
                        d['final'] = d['ru_uk']
                        d['source'] = "RU→UK"
                        print(f"Вибрано: {d['final']}")
                    else:
                        print("Неправильний вибір. C, E, R, Enter, n")

                print("\nОновлено:")
                print(row_format.format("№", "ENG", "Cambridge", "EN→UK", "RU→UK", "№", "Вибрано", "Джерело", "Статус"))
                print(f"{separator}")
                for i, dd in enumerate(batch_data, 1):
                    st = {'pending':'', 'saved':'Збережено', 'skipped':'Пропущено'}[dd['status']]
                    print(row_format.format(i, dd['en'], dd['cam'], dd['en_uk'], dd['ru_uk'], i, dd['final'], dd['source'], st))
                print(f"{separator}")
            else:
                print("1-10, s, n, q")

        if choice == 'q': break
        offset += BATCH_SIZE

    # === CSV ===
    if csv_lines:
        with open("reword_import.csv", "w", encoding="utf-8") as f:
            f.write("\n".join(csv_lines))
        print(f"\nCSV збережено: reword_import.csv ({len(csv_lines)} рядків)")
        print("Імпортуй у Reword: слова синхронізуються як вивчені.")

if __name__ == "__main__":
    main()