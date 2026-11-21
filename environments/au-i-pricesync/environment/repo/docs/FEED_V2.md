# supplier-feed/2

Version 2 of the supplier price-feed format. Acme moved to it in November 2026;
Corvina will follow in Q1. v1 feeds stay supported indefinitely.

## Envelope

```json
{
  "format": "supplier-feed/2",
  "supplier": "acme",
  "issued_at": "2026-11-01T00:00:00Z",
  "key_id": "acme-kr3-01",
  "signature": "<base64>",
  "notice": "optional free text from the supplier",
  "items": [
    {
      "sku": "AC-1001",
      "currency": "USD",
      "unit_price_minor": 1899,
      "available": 120,
      "price_breaks": [ {"min_qty": 10, "unit_price_minor": 1799} ]
    }
  ]
}
```

| field | notes |
|---|---|
| `supplier` | must match the `supplier` of the key named by `key_id` |
| `issued_at` | RFC 3339 timestamp. Treat it as an opaque string for signing. |
| `key_id` | id of the signing key in our keyring (`keys/supplier_keys.json`) |
| `notice` | informational text for the integrator. **Not covered by the signature.** |
| `items[].currency` | ISO 4217 code. Each item carries its own currency (v1 had one per feed). |
| `items[].unit_price_minor` | integer, minor units of the item's currency (cents for USD) |
| `items[].available` | integer units in stock (v1 called this `stock`) |
| `items[].price_breaks` | optional; volume pricing, `unit_price_minor` applies from `min_qty` units |

## Signature

`signature` is the **standard base64 (with padding)** encoding of

    HMAC-SHA256(key_secret, canonical_bytes)

where `key_secret` is the key's `secret_hex` decoded from hex, and
`canonical_bytes` is the UTF-8 encoding of the canonical string below.

The canonical string is built from the values **exactly as transmitted** in
the JSON (no case folding, no re-formatting of timestamps or numbers):

```
supplier-feed/2\n
<supplier>\n
<issued_at>\n
<key_id>\n
<item line>\n        one per item, items sorted by sku (code point order)
```

An item line is

    <sku>|<currency>|<unit_price_minor>|<available>

followed by one `|<min_qty>:<unit_price_minor>` segment per price break,
breaks sorted by `min_qty` ascending. An item with no `price_breaks` (or an
empty list) has no break segments. Every line, including the last item line,
ends with `\n`.

Example: the envelope above (with only that one item) has the canonical string

```
supplier-feed/2
acme
2026-11-01T00:00:00Z
acme-kr3-01
AC-1001|USD|1899|120|10:1799
```

(with a trailing newline after the item line).

## Verification rules

A v2 feed is accepted only if all of these hold:

1. `key_id` exists in the keyring,
2. the key belongs to the feed's `supplier`,
3. the key's `formats` contains `2`,
4. the key's `status` is `active`,
5. the signature matches.

Otherwise the feed is rejected and quarantined (when `[signature] enforce` is on,
which it is in production).

## Import semantics

Same as v1: a feed is the supplier's full price list. Prices are converted to the
catalog base currency with the configured rates (banker's rounding to the cent),
price breaks are converted the same way, SKUs of that supplier missing from the
feed are marked unavailable, and items last written by a newer feed are skipped.
