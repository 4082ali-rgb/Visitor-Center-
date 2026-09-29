# Visitor Centre — Daily Revenue Journal Entry Rules

**Outlet:** Manning Park Visitor Centre
**Source system:** Clover POS — "Sales Overview" report (PDF) + "Tax details" screen
**Target:** QuickBooks Online Advanced — journal entry CSV import
**Basis:** Entries JJ2936 (24 Jul 2026) through JJ3439 (31 Aug 2026), built and imported.

---

## 1. What the entry represents

One journal entry per calendar day. Money in (tenders) on the debit side, what was sold plus tax collected on the credit side.

```
DEBITS  = how it was paid    (card tenders + cash)
CREDITS = revenue categories + GST + PST
```

Both sides must equal **Amount Collected** from the Sales Overview.

---

## 2. Source data — which table to read

**Convert the report first.** Run every Clover Sales Overview PDF through MarkItDown (`convert_report.py`) and read the figures from the Markdown it produces.

The Clover report has several tables that don't always agree. Use these:

| What you need | Read it from | Not from |
|---|---|---|
| Revenue by category | **Revenue Classes** table, "Net Sales" column | — |
| GST / PST split | **Tax details** table ("Taxes collected" or "Net taxes") | the "Taxes & F…" column in Revenue Classes |
| Tenders | **Tender Types** and **Sales By Card Type** — see §5 | — |
| Cash | **Cash Deposits** table, "Cash Sales" | — |
| Control total | **Amount Collected** (Sales header) | — |

**Why the Tax details table:** the per-category "Taxes & Fees" column rounds differently. On 25 Aug the Revenue Classes total showed $8.12 while the header showed $8.13; the Tax details figures (GST $7.39 + PST $0.74) tied to the header exactly. Same pattern 26 Aug, 27 Aug, 30 Aug.

**If the header Gross/Net Sales fields are blank** (happened 10, 11, 12, 13 Aug): use the Revenue Classes total plus the Tax details total, and confirm they sum to Amount Collected.

---

## 3. GL account mapping

| Clover revenue class | QBO account | Class |
|---|---|---|
| Snacks | `3014 Revenue - Snacks` | 0051-VISITOR CENTER |
| Gifts | `3018 Revenue - Souvenir` | 0051-VISITOR CENTER |
| Non-Alcoholic | `3006 Revenue - Non-Alcoholic` | 0051-VISITOR CENTER |
| Unclassified | `3010 Visitor Centre Retail` | 0051-VISITOR CENTER |
| Parks Fees | `3001 Revenue` | **0050-MANNING PARKS** |

| Tender | QBO account | Class |
|---|---|---|
| Credit Card / Visa / MasterCard | `1007 Visa / Mstrcrd / Debit Receivable` | 0051-VISITOR CENTER |
| Debit Card / Interac | `1007 Visa / Mstrcrd / Debit Receivable` | 0051-VISITOR CENTER |
| Cash | `1002 Petty Cash in safe` | 0051-VISITOR CENTER |

| Tax | QBO account | Class |
|---|---|---|
| GST (5%) | `2029 GST Charged on Sales` | 0051-VISITOR CENTER |
| PST (7%) | `2035 PST 7% Charged on Sales` | 0051-VISITOR CENTER |

**Default class is `0051-VISITOR CENTER` on every line.** The single exception is the Parks Fees line, which goes to `0050-MANNING PARKS` — it's a park fee collected at the Visitor Centre, not Visitor Centre retail revenue.

**Omit any line with no activity that day.** No Parks Fees → no 3001 line. No PST collected → no 2035 line. No cash → no 1002 line. Don't write zero-value rows.

---

## 4. Memo and Description

**Memo (first row only):**
```
Visitor Centre Daily Revenue DD Month YYYY
```
Written out in full — `Visitor Centre Daily Revenue 31 August 2026`, not `31/08/26`.

**Description per line:** plain memo text by default. Add a prefix only in these cases:

| Line | Description |
|---|---|
| 1007 (every card line, **including when it's the only one**) | `Visa - {memo}` / `MasterCard - {memo}` / `Debit - {memo}` / `Credit - {memo}` |
| 3010 Visitor Centre Retail | `Unclassified - {memo}` |
| 3001 Revenue (Parks Fees) | `Park Fee - {memo}` |
| everything else | plain memo |

**Card lines always carry the tender label**, even when there's only one 1007 line — the Description then tells you the tender type without opening the source report.

This was applied inconsistently before the rule was settled:

| Entry | Date | Tender | Description written | Status |
|---|---|---|---|---|
| JJ3298 | 11 Aug | Interac only | `Debit - Visitor Centre Daily Revenue 11 August 2026` | matches rule |
| JJ3305 | 18 Aug | Interac only | `Debit - Visitor Centre Daily Revenue 18 August 2026` | matches rule |
| JJ3306 | 19 Aug | MasterCard only | `Visitor Centre Daily Revenue 19 August 2026` | **needs `MasterCard -` prefix** |

Prefix format is `Label - memo` (space, dash, space). **No commas anywhere in Description.**

---

## 5. Card tender split — the reconciliation test

Run the test before writing any card lines.

**Test — compare the card grand totals:**
```
Interac + Visa + MasterCard   (Sales By Card Type)
    ==
Debit Card + Credit Card      (Tender Types)
```

**If the totals match → split by card brand from Sales By Card Type.** Separate 1007 lines: `Visa -`, `MasterCard -`, and `Debit -` for Interac. This applies **even when the Tender Types debit/credit split differs** from the brand split. Clover's Tender Types counts some brand cards (e.g. a MasterCard debit card) as "Debit Card", so the two tables often split differently while agreeing on the total. The brand table is the one used.

*Example, 2 Sep 2026 (JJ3703):* Tender Types Debit $32.60 / Credit $13.72; Sales By Card Type Interac $16.90 / MasterCard $15.70 / Visa $13.72. Both total $46.32 → lines are Debit $16.90, MasterCard $15.70, Visa $13.72.

**If the totals don't match → fall back to Tender Types only.** Two 1007 lines: `Debit -` for Debit Card, `Credit -` for Credit Card. Do not split by brand. Also fall back if Sales By Card Type shows a brand other than Interac, Visa or MasterCard.

Never mix sources — all card lines come from one table. Don't take Debit from Tender Types and Visa/MasterCard from Sales By Card Type. That's what broke JJ2938 (26 Aug): Debit came from Tender Types ($189.45) while Visa and MasterCard came from the card-type table ($105.33 + $41.29), double-counting part of the card sales. Debits summed to $399.23 against $392.56 credits and QBO rejected the import.

**Rule change, 2 Sep 2026:** before this date, a matching grand total with a differing debit/credit split was treated as a failed test and used the fallback. That applied on 8, 24 and 31 Aug, which were delivered with Tender Types lines. The rule above supersedes it.

---

## 6. CSV format

Columns, exact order:
```
*JournalNo,*JournalDate,Memo,*AccountName,Debits,Credits,Description,Name,Location,Class
```

- `*JournalNo`, `*JournalDate` and `Memo` repeat on **every** row.
- Line endings are **CRLF** (`\r\n`).
- Date format `DD-MM-YYYY` (e.g. `31-08-2026`).
- Amounts: two decimals, no `$`, no thousands separators.
- Each row has a value in `Debits` **or** `Credits`, never both.
- `Name` and `Location` always empty.
- No commas in any field.

Filename: `{JournalNo}_VisitorCentre_{DMonYYYY}.csv` — e.g. `JJ3439_VisitorCentre_31Aug2026.csv`.

### Change from the delivered files

This matches the project-wide convention used for the other outlets. The 39 files delivered for 24 Jul – 31 Aug differed from it in two ways: JournalDate and Memo appeared on row 1 only, and line endings were LF. Those files are not being reissued; the only import failure seen (JJ2938) was a balance error, not a format error. All new files use the format above.

---|---|
| JournalNo, JournalDate and Memo repeat on **every** row | JournalNo on every row; **JournalDate and Memo on row 1 only** |
| Line endings must be **CRLF** (`\r\n`) | All 39 files were written with **LF** endings |

Only JJ2938's rejection was ever seen, and that was a balance error, not a format error — so LF and the row-1-only date/memo apparently import fine. But "no error was reported back to me" is weaker evidence than "confirmed imported," and I never saw confirmation for the other 38. If you want to match the documented convention, switching to CRLF and repeating all three fields costs nothing and removes the question.

---

## 7. Balance check — before delivering anything

```
sum(Debits) == sum(Credits) == Amount Collected
```

Compare **in cents, as integers**. Float comparison shows `392.55999999999995 != 392.56` and tells you nothing.

Verify against the report, not against your own arithmetic — recompute the debit side from the tender figures you actually wrote into the CSV, not from the figures you intended to write. The JJ2938 failure passed a hand check that used the wrong debit number, then failed in QBO.

If it doesn't balance: **stop**. Don't plug, don't round, don't deliver. Find the mismatched source table.

---

## 8. Journal numbers

**Always confirm with me. Never auto-increment.**

Visitor Centre draws from a shared QBO sequence with every other outlet, so gaps are large and unpredictable. Actual sequence over this period:

```
Jul 24–28    JJ2936 JJ2937 JJ2938 JJ2939 JJ2940
Jul 29–31    JJ3097 JJ3098 JJ3099          ← jumped +157
Aug 1–26     JJ3288 … JJ3313                ← jumped +189
Aug 27–28    JJ3376 JJ3377                  ← jumped +63
Aug 29–31    JJ3437 JJ3438 JJ3439           ← jumped +60
```

Sequential increments are fine *within* a run once I've given a starting number. A new day after a gap, or the first entry of a session, needs confirmation.

---

## 9. Flags section — required on every entry

End every entry with a short list covering, at minimum:

- Which card path was taken (brand split vs. Tender Types fallback) and the figures that decided it
- Any category absent that day whose line was omitted
- Any journal number proposed rather than confirmed
- Cent-level differences between report tables and which figure was used
- Any category not in the mapping table above

Proceed with a best guess and flag it — don't block. The exceptions that *do* block: an unbalanced entry, and an unmapped revenue category.

---

## 10. Open item

**"Gifts" → 3018 Revenue - Souvenir** was flagged for confirmation on 24 Jul and used consistently since, but never explicitly confirmed. The Clover category reads "Gifts"; the QBO account reads "Souvenir". Worth confirming with Beverly or checking a QBO export before treating this as settled.
