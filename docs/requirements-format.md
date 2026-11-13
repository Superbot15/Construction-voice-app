# Requirements file format

Spec requirements are TOML files with one `[[requirement]]` table per check.

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Your reference, usually the spec section and paragraph (`"03 30 00-2.2.A"`). |
| `applies_to` | no | `"product_data"` (default) checks data sheets; `"field_test"` checks daily log tests. |
| `property` | yes* | Normalized property name, e.g. `compressive_strength_28_day`, `slump`, `air_content`. Use `""` for a standard-only check. |
| `min` / `max` | no | Limits, inclusive. |
| `unit` | with limits | Unit of the limits. Converted automatically (`MPa` vs `psi`, `C` vs `F`, `mm` vs `in`). |
| `standard` | no | A standard the data sheet must reference, e.g. `"ASTM C494"`. |
| `description` | no | Free text. |

Property names come from the document's own label, lower-cased with punctuation turned into underscores.
`Compressive Strength (28 day)` becomes `compressive_strength_28_day`. Run `civil-ai parse` on a document to see the
names it produces.

Field test names are fixed: `slump`, `air_content`, `concrete_temperature`, `unit_weight`, `compaction`.

A finding is `pass`, `fail` (out of limits, wrong unit, or standard not referenced) or `missing` (the data sheet
doesn't state the property). `civil-ai check` exits with status 1 if any finding is not `pass`, so it can gate a CI job
or a scripted review.
