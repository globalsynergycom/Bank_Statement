#!/usr/bin/env python3
import argparse, re, sys
from pathlib import Path
import pandas as pd

CANON = ["date","amount","payer","inn","purpose","receiver"]

HEADER_PATTERNS = {
    "date":     re.compile(r"(дата|date|валютир|операц|күні)", re.I),
    "amount":   re.compile(r"(сумм|amount|итого)", re.I),
    "debit":    re.compile(r"(debet|debit|приход)", re.I),
    "credit":   re.compile(r"(credit|кредит|расход)", re.I),
    "payer":    re.compile(r"(плательщ|отправител|контрагент|sender|жөнелтуш)", re.I),
    "inn":      re.compile(r"\b(инн|бин|iin|tin)\b", re.I),
    "purpose":  re.compile(r"(назнач|purpose|описан|коммент|төлем)", re.I),
    "receiver": re.compile(r"(получател|receiver|beneficiar|наш.?счет)", re.I),
}

def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    return pd.read_excel(path, dtype=str, engine="openpyxl", keep_default_na=False)

def detect_header_row(df: pd.DataFrame) -> int:
    best_i, best_score = 0, -1
    for i in range(min(30, len(df))):
        row = [str(x or "") for x in df.iloc[i].tolist()]
        score = 0
        for cell in row:
            low = cell.lower()
            for pat in HEADER_PATTERNS.values():
                if pat.search(low):
                    score += 1
                    break
        if score > best_score:
            best_score, best_i = score, i
    return best_i

def map_columns(header: list[str]) -> dict:
    res = {k: -1 for k in ["date","amount","debit","credit","payer","inn","purpose","receiver"]}
    for idx, name in enumerate(header):
        low = str(name or "").lower().strip()
        for key, pat in HEADER_PATTERNS.items():
            if pat.search(low):
                res[key] = idx
    return res

def to_num(x: str):
    if x is None: return None
    s = str(x).strip().replace("\u00A0","").replace(" ","")
    if s.count(",")==1 and "." not in s: s = s.replace(",",".")
    s = re.sub(r"[^\d.\-+]", "", s)
    if s in ("",".","-","+"): return None
    try: return float(s)
    except: return None

def parse_date(x: str):
    if x is None or str(x).strip()=="":
        return ""
    s = str(x).strip()
    m = re.match(r"^(\d{2})[./](\d{2})[./](\d{4})$", s)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m: return s
    try:
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(d): return ""
        return d.strftime("%Y-%m-%d")
    except:
        return ""

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # преобразуем в «матрицу» чтобы искать хедер на первых строках
    matrix = pd.DataFrame(df.values)
    header_row = detect_header_row(matrix)
    header = [str(x or "") for x in matrix.iloc[header_row].tolist()]
    data = matrix.iloc[header_row+1:].reset_index(drop=True)
    mapping = map_columns(header)

    out_rows = []
    for _, row in data.iterrows():
        get = lambda idx: (str(row.iloc[idx]) if 0 <= idx < len(row) else "").strip()
        amount = to_num(get(mapping["amount"])) if mapping["amount"]>=0 else None
        if amount is None:
            debit = to_num(get(mapping["debit"]))
            credit = to_num(get(mapping["credit"]))
            amount = (debit or 0) - (credit or 0) if (debit is not None or credit is not None) else ""
        o = {
            "date":     parse_date(get(mapping["date"])),
            "amount":   amount if amount != "" else "",
            "payer":    get(mapping["payer"]),
            "inn":      re.sub(r"\D+","", get(mapping["inn"])),
            "purpose":  get(mapping["purpose"]),
            "receiver": get(mapping["receiver"]),
        }
        if o["date"] or o["purpose"] or o["amount"]!="":
            out_rows.append(o)
    out = pd.DataFrame(out_rows, columns=CANON)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to file in inbox/")
    ap.add_argument("--outdir", required=True, help="Folder to write normalized CSV (e.g., outbox)")
    args = ap.parse_args()

    src = Path(args.input)
    df = read_any(src)
    out = normalize_df(df)
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"normalized_{src.stem}.csv"
    out.to_csv(out_path, index=False)
    print(f"Wrote: {out_path}")

if __name__ == "__main__":
    sys.exit(main())

