import sqlite3
import json
import re
from typing import Any

# ========== CONFIG ==========
DB_PATH = r"C:\My_pc\___File_Sasha___\Automatisation\автоматизація_Reword\reword_upruve_db\04.11.25reword_en.db"
TABLE = "word"
OUT_BAD_IDS = "removed_examples_ids.txt"
# ============================

# regex для очевидних російських літер
RU_CHARS = re.compile(r"[ёЁыЫъЪэЭ]")

def has_russian(text: str) -> bool:
    """Повертає True, якщо в тексті є явно російські символи."""
    if not isinstance(text, str):
        return False
    return bool(RU_CHARS.search(text))

def robust_json_load(value: Any):
    """
    Працює з кількома кривими варіантами EXAMPLES_UKR/EXAMPLES_RUS:
    - якщо це вже список, повертаємо
    - якщо валідний JSON рядок, повертаємо
    - пробуємо виправити подвоєні лапки, зайві обгортки, витягти частину між [ ... ]
    """
    if isinstance(value, list):
        return value
    if value is None:
        return None

    s = str(value).strip()

    if s == "" or s.upper() == "NULL":
        return None

    try:
        return json.loads(s)
    except Exception:
        pass

    try:
        fixed = s.replace('""', '"')
        return json.loads(fixed)
    except Exception:
        pass

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        inner = s[1:-1]
        try:
            return json.loads(inner)
        except Exception:
            try:
                return json.loads(inner.replace('""','"'))
            except Exception:
                pass

    try:
        a = s.find('[')
        b = s.rfind(']')
        if a != -1 and b != -1 and b > a:
            sub = s[a:b+1]
            sub_fixed = sub.replace('""', '"')
            return json.loads(sub_fixed)
    except Exception:
        pass

    return None

def clean_examples_in_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"SELECT ID, EXAMPLES_UKR FROM {TABLE} WHERE EXAMPLES_UKR IS NOT NULL AND TRIM(EXAMPLES_UKR) != ''")
    rows = cur.fetchall()

    removed_total = 0
    rows_touched = []
    failed_parse = []

    for idv, raw in rows:
        parsed = robust_json_load(raw)
        if parsed is None:
            failed_parse.append(idv)
            continue

        if not isinstance(parsed, list):
            failed_parse.append(idv)
            continue

        clean_list = []
        removed_here = 0

        for ex in parsed:

            if not isinstance(ex, dict):

                removed_here += 1
                continue

            uk = ex.get("t") or ex.get("uk") or ex.get("UK") or ""

            if uk and has_russian(uk):
                removed_here += 1
                continue

            if not uk or str(uk).strip() == "":
                removed_here += 1
                continue

            clean_list.append({
                "o": ex.get("o", ""),  
                "t": uk.strip()
            })

        if removed_here > 0:
            rows_touched.append((idv, removed_here))
            removed_total += removed_here

            if clean_list:
                j = json.dumps(clean_list, ensure_ascii=False, separators=(',',':'))
                cur.execute(f"UPDATE {TABLE} SET EXAMPLES_UKR=? WHERE ID=?", (j, idv))
            else:
                cur.execute(f"UPDATE {TABLE} SET EXAMPLES_UKR=NULL WHERE ID=?", (idv,))

    conn.commit()
    conn.close()

    with open(OUT_BAD_IDS, "w", encoding="utf-8") as f:
        for idv, removed in rows_touched:
            f.write(f"{idv}\tremoved_examples={removed}\n")
        if failed_parse:
            f.write("\n# failed_to_parse_json_ids\n")
            for idv in failed_parse:
                f.write(f"{idv}\n")

    print("✅ Done.")
    print(f"Rows touched: {len(rows_touched)}")
    print(f"Total removed examples: {removed_total}")
    if failed_parse:
        print(f"Warning: failed to parse EXAMPLES_UKR for {len(failed_parse)} rows. See {OUT_BAD_IDS} for details.")

if __name__ == "__main__":
    clean_examples_in_db()
