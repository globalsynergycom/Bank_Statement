#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
normalize.py — нормализация банковской выписки к единому формату.

Вход:  --input path/to/file.xlsx|csv
Выход: --outdir outbox/  -> outbox/normalized_<basename>.csv

Столбцы результата: date, amount, payer, inn, purpose, receiver
"""

from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


CANON = ["date", "amount", "payer", "inn", "purpose", "receiver"]

# Регэкспы для распознавания заголовков на разных языках/вариантах
HEADER_PATTERNS: Dict[str, re.Pattern] = {
    "date":     re.compile(r"(дата|date|валютир|операц|күні|к?үні)", re.I),
    "amount":   re.compile(r"(сумм|amount|итого|total)", re.I),
    "debit":    re.compile(r"(дебет|приход|debet|debit|incoming)", re.I),
    "credit":   re.compile(r"(кредит|расход|credit|outgoing)", re.I),
    "payer":    re.compile(r"(плательщ|отправител|контрагент|sender|жөнелтуш|payer)", re.I),
    "inn":      re.compile(r"\b(инн|бин|iin|tin|vat|tax)\b", re.I),
    "purpose":  re.compile(r"(назнач|purpose|описан|comment|коммент|төлем|details|reference)", re.I),
    "receiver": re.compile(r"(получател|receiver|beneficiar|наш.?счет|account name)", re.I),
}


def read_any(path: Path) -> pd.DataFrame:
    """Читает CSV/XLSX в pandas.DataFrame в виде строк."""
    if path.suffix.lower() == ".csv":
        # Попытка автоматически подобрать кодировку
        for enc in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
            except Exception:
                continue
        # fallback без указания кодировки
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    # XLSX/XLS
    return pd.read_excel(path, dtype=str, engine="openpyxl", keep_default_na=False)


def detect_header_row(df: pd.DataFrame, max_rows: int = 30) -> int:
    """
    Эвристика: ищем строку, где больше всего ячеек похоже на заголовки.
    Возвращает индекс строки заголовка (по умолчанию 0, если не нашли лучше).
    """
    best_i, best_score = 0, -1
    limit = min(max_rows, len(df))
    for i in range(limit):
        row = [str(x or "") for x in df.iloc[i].tolist()]
        score = 0
        for cell in row:
            low = cell.lower().strip()
            for pat in HEADER_PATTERNS.values():
                if pat.search(low):
                    score += 1
                    break
        if score > best_score:
            best_score, best_i = score, i
    return best_i


def map_columns(header: List[str]) -> Dict[str, int]:
    """Сопоставляет имена столбцов с каноническими ключами, возвращает индексы."""
    res = {k: -1 for k in ["date", "amount", "debit", "credit", "payer", "inn", "purpose", "receiver"]}
    for idx, name in enumerate(header):
        low = str(name or "").lower().strip()
        for key, pat in HEADER_PATTERNS.items():
            if pat.search(low):
                # Берем первый найденный матч (если дубликаты — можно усложнить логику)
                if res.get(key, -1) == -1:
                    res[key] = idx
    return res


def to_num(x: Optional[str]) -> Optional[float]:
    """Пытается конвертировать строку в число (учитывает запятую как разделитель)."""
    if x is None:
        return None
    s = str(x).strip().replace("\u00A0", "").replace(" ", "")
    # Если десятичный разделитель — запятая
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    s = re.sub(r"[^0-9.\-+]", "", s)
    if s in ("", ".", "-", "+"):
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_date(x: Optional[str]) -> str:
    """Пытается распарсить дату, вернёт YYYY-MM-DD или пустую строку."""
    if not x or str(x).strip() == "":
        return ""
    try:
        d = pd.to_datetime(x, dayfirst=True, errors="coerce")
        if pd.isna(d):
            return ""
        return d.strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Делает:
    - Поиск заголовка
    - Отрезание служебных верхних строк
    - Мэппинг колонок
    - Подсчёт amount из debit/credit, если amount нет
    """
    # Преобразуем в "матрицу" без индексов/названий колонок
    matrix = pd.DataFrame(df.values)
    header_row = detect_header_row(matrix)
    header = [str(x or "") for x in matrix.iloc[header_row].tolist()]
    data = matrix.iloc[header_row + 1:].reset_index(drop=True)

    mapping = map_columns(header)

    out_rows = []
    for _, row in data.iterrows():
        def get(idx: int) -> str:
            return (str(row.iloc[idx]) if 0 <= idx < len(row) else "").strip()

        # Сумма: напрямую или как дебет-кредит
        amount = to_num(get(mapping["amount"])) if mapping["amount"] >= 0 else None
        if amount is None:
            debit = to_num(get(mapping["debit"]))
            credit = to_num(get(mapping["credit"]))
            if debit is not None or credit is not None:
                amount = (debit or 0.0) - (credit or 0.0)

        rec = {
            "date":     parse_date(get(mapping["date"])),
            "amount":   ("" if amount is None else amount),
            "payer":    get(mapping["payer"]),
            "inn":      re.sub(r"\D+", "", get(mapping["inn"])),
            "purpose":  get(mapping["purpose"]),
            "receiver": get(mapping["receiver"]),
        }

        # Отсекаем явно пустые строки
        if any(str(rec[k]) for k in rec):
            out_rows.append(rec)

    return pd.DataFrame(out_rows, columns=CANON)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Путь к исходному файлу (.xlsx/.xls/.csv)")
    ap.add_argument("--outdir", required=True, help="Папка для результата (например, outbox)")
    args = ap.parse_args()

    src = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = read_any(src)
    out = normalize_df(df)

    # Имя результата
    stem = src.stem
    out_path = outdir / f"normalized_{stem}.csv"
    out.to_csv(out_path, index=False)

    print(f"[normalize.py] OK: {src} → {out_path}")


if __name__ == "__main__":
    main()
