# Halcyon Bank AG - CSV export ("Kontoauszug")

Requested by finance-ops (FIN-2290): several of our German entities bank with
Halcyon and their statements are currently keyed in by hand.

Example: `samples/halcyon_2026-10.csv`.

* Encoding UTF-8 **with a byte-order mark**; `;` delimited; fields containing
  `;` are double-quoted.
* The file starts with a **preamble** of `key;value` lines (`Kontoauszug;Halcyon Bank AG`,
  `Konto;...`, `Zeitraum;...`) and possibly empty `;` lines. The column header
  is the first line starting with `Buchungstag;`. Detect the export by its first
  line starting with `Kontoauszug;Halcyon Bank`.
* Columns: `Buchungstag;Valuta;Verwendungszweck;Soll;Haben;Saldo`
  * date = `Buchungstag` (booking date), format `dd.mm.yyyy`. Ignore `Valuta`.
  * description = `Verwendungszweck` (whitespace collapsed, like every bank)
  * amount: `Soll` is money out, `Haben` is money in; both are unsigned German
    numbers (`1.250,00`). Exactly one of them is filled on a transaction row:
    amount = `Haben`, or `-Soll`. A row with both or neither filled is an error.
  * balance = `Saldo` (German number, may be negative: `-120,50`)
* Empty `;` lines anywhere are ignored.
* The file ends with a closing-balance line `;;Endsaldo;;;<balance>` that is
  **not** a transaction.
* `source_line` is the physical line number of the row in the file (1-based,
  counting the preamble).
* `--bank halcyon` must work as well as detection.
