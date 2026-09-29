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
| 1007, when **more than one** 1007 line exists | `Visa - {memo}` / `MasterCard - {memo}` / `Debit - {memo}` / `Credit - {memo}` |
| 1007, when it's the **only** 1007 line | **see note below — was applied inconsistently** |
| 3010 Visitor Centre Retail | `Unclassified - {memo}` |
| 3001 Revenue (Parks Fees) | `Park Fee - {memo}` |
| everything else | plain memo |

**Unresolved — the single-1007 case was handled two different ways.** Three entries had only one 1007 line:

| Entry | Date | Tender | Description written |
|---|---|---|---|
| JJ3298 | 11 Aug | Interac only | `Debit - Visitor Centre Daily Revenue 11 August 2026` |
| JJ3305 | 18 Aug | Interac only | `Debit - Visitor Centre Daily Revenue 18 August 2026` |
| JJ3306 | 19 Aug | MasterCard only | `Visitor Centre Daily Revenue 19 August 2026` |

On 19 Aug the prefix was stripped on the reasoning that prefixes exist to disambiguate lines sharing an account, and with one line there's nothing to disambiguate. That reasoning was not applied back to 11 and 18 Aug, which were already delivered.

**Decide which you want and make it the rule.** Keeping the tender prefix always is arguably more useful — the Description then tells you the tender type without opening the source report. Dropping it on single lines is more internally consistent with the disambiguation logic. Either is defensible; the current state is neither.

Prefix format is `Label - memo` (space, dash, space). **No commas anywhere in Description.**

---

## 5. Card tender split — the reconciliation test

This is the rule that changes most often day to day. Run the test before writing any card lines.

**Test:**
```
Interac                    ==  Debit Card      (Tender Types)
Visa + MasterCard          ==  Credit Card     (Tender Types)
```

**If both match exactly → split by card brand.** Separate 1007 lines with `Visa -`, `MasterCard -`, `Debit -` prefixes.

**If either side doesn't match → fall back to Tender Types only.** Two 1007 lines: `Debit -` for Debit Card, `Credit -` for Credit Card. Do not split the credit side by brand.

Never mix sources — don't take Debit from Tender Types and Visa/MasterCard from Sales By Card Type. That's what broke JJ2938 (26 Aug): Debit came from Tender Types ($189.45) while Visa and MasterCard came from the card-type table ($105.33 + $41.29), double-counting part of the card sales. Debits summed to $399.23 against $392.56 credits and QBO rejected the import.

**Note the grand totals can match while the individual splits don't.** On 8 Aug, 24 Aug and 31 Aug both tables totalled the same figure but the debit/credit split differed between them — that's still a failed test, use the fallback.

Frequency over the period: the test failed on 26, 29 Jul and 3, 4, 5, 7, 8, 9, 16, 24, 26, 31 Aug. It's a normal branch, not an error condition.

---

## 6. CSV format

Columns, exact order:
```
*JournalNo,*JournalDate,Memo,*AccountName,Debits,Credits,Description,Name,Location,Class
```

- `*JournalNo` repeats on **every** row.
- `*JournalDate` and `Memo` on the **first row only**, blank thereafter.
- Date format `DD-MM-YYYY` (e.g. `31-08-2026`).
- Amounts: two decimals, no `$`, no thousands separators.
- Each row has a value in `Debits` **or** `Credits`, never both.
- `Name` and `Location` always empty.
- No commas in any field.

Filename: `{JournalNo}_VisitorCentre_{DMonYYYY}.csv` — e.g. `JJ3439_VisitorCentre_31Aug2026.csv`.

### Two deviations from the project-wide convention

These are what the 39 delivered files actually do. Both differ from the general rules recorded for other outlets:

| Project-wide rule | What the VC files do |
|---|---|
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
