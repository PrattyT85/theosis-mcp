# Manuscript witness research

## Decision

**Proceed after importer hardening; do not import yet.** The SWORD modules are small and have usable provenance, but the current importer is unsafe for the live database and does not currently populate `manuscript_witnesses`.

## Sources

| Module | Source | Licence | Size/version |
|---|---|---|---|
| SBLGNTApp | [CrossWire module info](https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=SBLGNTApp) / [download](https://crosswire.org/sword/servlet/SwordMod.Verify?modName=SBLGNTApp&pkgType=raw) | Copyrighted; free non-commercial distribution; Logos Bible Software/SBL | ~288 KB, v1.3 (2011-03-22) |
| VarApp | [CrossWire module info](https://www.crosswire.org/sword/modules/ModInfo.jsp?modName=VarApp) / [download](https://crosswire.org/sword/servlet/SwordMod.Verify?modName=VarApp&pkgType=raw) | CC0 | ~972 KB, v1.0 (2012-07-10) |
| Converter | [Debian `mod2imp` manpage](https://manpages.debian.org/testing/libsword-utils/mod2imp.1) | GPL, SWORD utilities | `libsword-utils` / `/usr/bin/mod2imp` is present on CT125 |

## Existing importer risks

`scripts/import_variants.py` currently:

1. Truncates `textual_variants` and `manuscript_witnesses` before import, which would destroy the existing 6,840 variant rows.
2. Inserts textual variants but does not insert rows into `manuscript_witnesses`.
3. Requires the SWORD modules to be staged; the modules are not currently installed on CT125.

These must be fixed before any live import. The importer should default to preserving existing data and require an explicit destructive flag for a rebuild.

## Proposed schema mapping

- `textual_variants.book`, `chapter`, `verse`, `reference`: parsed from SWORD `$$$Book Chapter:Verse` markers.
- `mt_reading`: base reading before `]`.
- `variant_source`: module/source name.
- `variant_reading`: reading after `]`.
- `variant_significance`: base witness/sigla.
- `scholarly_consensus`: variant witness/sigla.
- `manuscript_witnesses.variant_id`: inserted textual-variant id.
- `manuscript_witnesses.manuscript`: each parsed siglum, such as `WH`, `NIV`, `RP`, or `Treg`.
- `manuscript_witnesses.reading_support`: `base` or `variant`.

Existing optional textual-variant analysis fields must remain untouched when importing these modules.

## Validation reference

The importer documents this SBLGNT apparatus sample:

```text
$$$Matthew 1:5
<item>Βόες … Βόες WH NIV ] Βοὸς … Βοὸς Treg</item>
```

Expected parsed values:

- reference: `Mat 1:5`
- base reading: `Βόες … Βόες`
- variant reading: `Βοὸς … Βοὸς`
- base sigla: `WH`, `NIV`
- variant siglum: `Treg`

## Safe implementation gate

Before writing to the live database:

1. Download both modules to a temporary directory.
2. Convert to IMP and run a parser-only dry run.
3. Verify the Matthew 1:5 fixture and count the expected entries.
4. Run the importer against a disposable UTF-8 restore.
5. Confirm existing Heiser variant rows remain and witness rows link to newly inserted variants.
6. Only then take a fresh backup and import into production.

Do not redistribute SBLGNTApp data. Keep it on the private research host and retain its licence notice.
