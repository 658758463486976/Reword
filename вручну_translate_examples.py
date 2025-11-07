import sqlite3
import json
import time
import os
import translators as ts

# === НАЛАШТУВАННЯ ===
DB_PATH = r"C:\My_pc\___File_Sasha___\Automatisation\автоматизація_Reword\reword_upruve_db\04.11.25reword_en.db"
TABLE_NAME = "word"
LIMIT = 200
DELAY = 1.2 

# === ВИПРАВЛЕННЯ РОЗДІЛЮВАЧІВ ===
def fix_delimiter(text):
    if not text:
        return text
    text = text.replace(";", ",")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return ", ".join(parts)

# === ЗАМІНА #word# НА #укр# ДО ПЕРЕКЛАДУ ===
def prepare_ru_for_translation(ru_sent, en_word, ukr_word):
    if not ru_sent or not en_word or not ukr_word:
        return ru_sent
    return ru_sent.replace(f"#{en_word}#", f"#{ukr_word}#")

# === ПЕРЕКЛАД RU → UKR через translators ===
def translate_ru_to_uk(ru_sent, en_word, ukr_word):
    if not ru_sent:
        return None
    try:
        ru_prepared = prepare_ru_for_translation(ru_sent, en_word, ukr_word)
        time.sleep(DELAY)
        uk_sent = ts.translate_text(
            ru_prepared,
            from_language='ru',
            to_language='uk',
            translator='bing'
        )
        return uk_sent.strip()
    except Exception as e:
        print(f"Помилка translators: {e}")
        return None

# === БАЗА ДАНИХ ===
def get_examples_to_translate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT ID, word, UKR, EXAMPLES_RUS 
        FROM {TABLE_NAME} 
        WHERE EXAMPLES_RUS IS NOT NULL 
          AND EXAMPLES_RUS != 'NULL' 
          AND (EXAMPLES_UKR IS NULL OR EXAMPLES_UKR = '' OR EXAMPLES_UKR = 'NULL')
        ORDER BY ID
        LIMIT {LIMIT}
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_examples_ukr(id_val, examples_ukr_list):
    if not examples_ukr_list:
        return False
    examples_json = json.dumps(examples_ukr_list, ensure_ascii=False, separators=(',', ':'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE {TABLE_NAME} SET EXAMPLES_UKR = ? WHERE ID = ?", (examples_json, id_val))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Помилка збереження: {e}")
        conn.close()
        return False

# === ГОЛОВНЕ ===
def main():
    print("Переклад прикладів RU → UKR через translators (безкоштовно)\n")
    rows = get_examples_to_translate()
    if not rows:
        print("Усі приклади вже перекладено!")
        return

    updated = 0
    for row in rows:
        id_val = row['ID']
        word_en = row['word']
        ukr_raw = row['UKR'] or word_en
        ukr = fix_delimiter(ukr_raw)
        examples_rus_str = row['EXAMPLES_RUS']

        try:
            examples_rus = json.loads(examples_rus_str)
        except Exception as e:
            print(f"Помилка JSON для ID {id_val}: {e}")
            continue

        print("="*80)
        print(f"{word_en} → {ukr}")

        # Переклад
        examples_ukr = []
        for ex in examples_rus:
            ru_sent = ex['t']
            uk_sent = translate_ru_to_uk(ru_sent, word_en, ukr)
            examples_ukr.append({
                "o": ex['o'],
                "ru": ex['t'],
                "t": uk_sent or ru_sent
            })

        # Редагування
        while True:
            print("-"*80)
            print("ПЕРЕКЛАД:")
            for i, ex in enumerate(examples_ukr):
                print("-"*20)
                print(f"  [{i+1}] EN: {ex['o']}")
                print(f"      RU: {ex['ru']}")
                print(f"      UK: {ex['t']}")
            print("-"*80)

            choice = input("Дія? (y=зберегти/e=редагувати/n=пропустити/q=вихід): ").strip().lower()
            if choice == 'y':
                save_list = [{"o": ex["o"], "t": ex["t"]} for ex in examples_ukr]
                if save_examples_ukr(id_val, save_list):
                    print("Збережено.\n")
                    updated += 1
                else:
                    print("Помилка збереження.\n")
                break
            elif choice == 'e':
                try:
                    idx = int(input("   Номер речення для редагування (1,2,...): ")) - 1
                    if 0 <= idx < len(examples_ukr):
                        old = examples_ukr[idx]['t']
                        new = input(f"   Новий УКР (було: {old}): ").strip()
                        if new:
                            examples_ukr[idx]['t'] = new
                            print("   → Оновлено.")
                        else:
                            print("   Пропущено.")
                    else:
                        print("   Некоректний номер.")
                except:
                    print("   Введіть число.")
                continue
            elif choice == 'n':
                print("Пропущено.\n")
                break
            elif choice == 'q':
                print("Вихід.")
                break
            else:
                print("Введіть: y, e, n, q")

        if choice == 'q':
            break

    print(f"Готово! Перекладено прикладів: {updated} слів.")

if __name__ == "__main__":
    main()
