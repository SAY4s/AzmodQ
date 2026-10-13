#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مبدل بانک سوال آزمود
=====================
فایل‌های متنی سوال (فرمت زیر) را به sardaftari.json تبدیل می‌کند که سایت آزمود می‌خواند.

فرمت هر بلوک (بین بلوک‌ها یک خط خالی):
    متن سوال
    گزینه اول
    گزینه دوم
    گزینه سوم
    گزینه چهارم
    شماره گزینه صحیح     (۱ تا ۴ یا 1 تا 4 یا الف/ب/ج/د یا a/b/c/d)

خطوط اختیاری (قبل از بلوک‌ها):
    @year 1401           سال آزمون (اگر نباشد از اسم فایل خوانده می‌شود)
    @section حقوق مدنی   درس؛ تا خط @section بعدی برای همه‌ی سوال‌ها معتبر است

خروجی: [{"q":"..","o":[4 گزینه],"a":0..3,"y":1401,"s":"حقوق مدنی"}, ...]

اجرا:
    python convert_sardaftari.py                     (با رابط گرافیکی؛ اگر tkinter نبود، پوشه‌ی data را تبدیل می‌کند)
    python convert_sardaftari.py data/*.txt -o sardaftari.json
    python convert_sardaftari.py --cli               (بدون رابط گرافیکی)
"""
import argparse
import glob
import json
import os
import re
import sys

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
LETTERS = {"الف": 1, "ا": 1, "ب": 2, "ج": 3, "د": 4, "a": 1, "b": 2, "c": 3, "d": 4}

# درس‌های هم‌خانواده در یک نام ادغام می‌شوند تا فیلتر درس در سایت یکدست باشد
MERGE = {
    "حقوق ثبت اسناد": "حقوق ثبت",
    "حقوق ثبت املاک": "حقوق ثبت",
    "حقوق ثبت اسناد و املاک": "حقوق ثبت",
}


def parse_answer(tok):
    """برمی‌گرداند: (شماره ۱..۴ یا None, توضیح خطا)"""
    t = tok.strip().translate(DIGITS).lower().rstrip(".)")
    if t in ("", "؟", "?", "-", "—"):
        return None, "بدون پاسخ"
    if t in LETTERS:
        return LETTERS[t], ""
    if re.fullmatch(r"[1-4]", t):
        return int(t), ""
    return None, "پاسخ نامعتبر یا چندگانه: " + tok.strip()


def parse_file(path, default_year=None, log=print):
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read().replace("\r\n", "\n").replace("\r", "\n")
    year = default_year
    m = re.search(r"(1[34]\d\d)", os.path.basename(path))
    if m:
        year = int(m.group(1))
    section = ""
    items, skipped = [], []
    block = []
    qno = 0

    def flush():
        nonlocal block, qno
        if not block:
            return
        qno += 1
        if len(block) != 6:
            skipped.append((qno, "تعداد خطوط بلوک %d است (باید ۶ باشد)" % len(block)))
        else:
            a, why = parse_answer(block[5])
            if a is None:
                skipped.append((qno, why))
            elif not all(x.strip() for x in block[:5]):
                skipped.append((qno, "سوال یا گزینه خالی"))
            else:
                it = {"q": block[0].strip(), "o": [x.strip() for x in block[1:5]], "a": a - 1}
                if year:
                    it["y"] = year
                if section:
                    it["s"] = MERGE.get(section, section)
                items.append(it)
        block = []

    for line in raw.split("\n"):
        s = line.strip()
        if s.startswith("@year"):
            flush()
            mm = re.search(r"\d{4}", s.translate(DIGITS))
            if mm:
                year = int(mm.group(0))
            continue
        if s.startswith("@section"):
            flush()
            section = s[len("@section"):].strip()
            continue
        if s == "":
            flush()
        else:
            block.append(s)
    flush()
    log("%s: %d سوال معتبر، %d ردشده" % (os.path.basename(path), len(items), len(skipped)))
    for n, why in skipped:
        log("   - سوال %d ردشد: %s" % (n, why))
    return items


def convert(paths, out, log=print):
    allq = []
    for p in sorted(paths):
        allq += parse_file(p, log=log)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(allq, f, ensure_ascii=False, separators=(",", ":"))
    years = sorted({q.get("y") for q in allq if q.get("y")})
    secs = sorted({q.get("s") for q in allq if q.get("s")})
    log("")
    log("جمع: %d سوال | سال‌ها: %s | درس‌ها: %d" % (len(allq), "، ".join(map(str, years)), len(secs)))
    log("ذخیره شد: " + os.path.abspath(out))
    return allq


def gui():
    import tkinter as tk
    from tkinter import filedialog, scrolledtext, messagebox

    root = tk.Tk()
    root.title("مبدل بانک سوال آزمود")
    root.geometry("720x520")
    files = []
    here = os.path.dirname(os.path.abspath(__file__))
    lbl = tk.Label(root, text="هنوز فایلی انتخاب نشده", anchor="e")
    lbl.pack(fill="x", padx=10, pady=(10, 0))
    box = scrolledtext.ScrolledText(root, height=22, font=("Tahoma", 10))
    box.pack(fill="both", expand=True, padx=10, pady=10)

    def log(s):
        box.insert("end", s + "\n")
        box.see("end")
        root.update_idletasks()

    def pick():
        sel = filedialog.askopenfilenames(title="فایل‌های متنی سوال", initialdir=os.path.join(here, "data"),
                                          filetypes=[("متن", "*.txt"), ("همه", "*.*")])
        if sel:
            files[:] = list(sel)
            lbl.config(text="%d فایل انتخاب شد" % len(files))

    def run():
        if not files:
            messagebox.showwarning("آزمود", "اول فایل‌ها را انتخاب کن")
            return
        out = filedialog.asksaveasfilename(title="ذخیره‌ی JSON", defaultextension=".json",
                                           initialfile="sardaftari.json", filetypes=[("JSON", "*.json")])
        if not out:
            return
        box.delete("1.0", "end")
        convert(files, out, log)
        messagebox.showinfo("آزمود", "تبدیل تمام شد. فایل را کنار index.html روی هاست بگذار.")

    bar = tk.Frame(root)
    bar.pack(pady=(0, 10))
    tk.Button(bar, text="۱) انتخاب فایل‌ها", width=20, command=pick).pack(side="right", padx=6)
    tk.Button(bar, text="۲) تبدیل و ذخیره", width=20, command=run).pack(side="right", padx=6)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="تبدیل سوال‌های متنی به JSON سایت آزمود")
    ap.add_argument("files", nargs="*", help="فایل‌های txt (اگر نباشد، پوشه‌ی data)")
    ap.add_argument("-o", "--out", default="sardaftari.json")
    ap.add_argument("--cli", action="store_true", help="بدون رابط گرافیکی")
    a = ap.parse_args()
    if not a.files and not a.cli:
        try:
            gui()
            return
        except Exception as e:  # tkinter موجود نیست یا نمایشگر ندارد
            print("رابط گرافیکی در دسترس نیست (%s)؛ حالت خط فرمان." % e)
    files = a.files or glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "*.txt"))
    if not files:
        sys.exit("هیچ فایل txt پیدا نشد.")
    convert(files, a.out)


if __name__ == "__main__":
    main()
