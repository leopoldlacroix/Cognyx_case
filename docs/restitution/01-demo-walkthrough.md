# Demo walkthrough

How to open the six pages and what to say on each one. This is the spoken tour. The technical note next to it explains how the programs connect. The third note lists what is missing, what to tighten, and what belongs after the pilot.

Start the site from the project folder, then use the address. Double-clicking an HTML file shows the pages, and the Accept / Reject / Redirect buttons do not save.

```bash
python3 -m app.backend.cli serve
```

Open http://127.0.0.1:8765/workflow.html and follow the pills at the top, left to right.

## What the data is, before any page

Five versions of one regional train:

| Code | Train |
|---|---|
| `REGIO-STD` | Regional Standard |
| `REGIO-COMFORT` | Regional Comfort |
| `REGIO-NORDIC` | Regional Nordic, the cold-weather version |
| `REGIO-HC` | Regional High Capacity |
| `REGIO-EXPORT` | Regional Export |

Each train has a parts list, a bill of materials. One line says: this train, this assembly, this part, this quantity. An assembly is a chapter of that list, such as the battery module `BAT-M06`. A component is one part inside a chapter.

The lists come from six spreadsheets in three places:

- **PLM** is the engineering system: parts lists, assemblies, and the five train versions.
- **ERP** is the purchasing system: material numbers, suppliers, units, and whether a material is obsolete.
- **Engineering notes** are sentences written by people. A note can say two part numbers are the same, or that a sensor is only for the Nordic train.

The spreadsheets disagree. The same air-conditioning controller is written `CTRL-AIR-01`, `CTRL-AIR01`, `CTRL-AIR-O1`, and `CTRL-HVAC-001`. One quantity is the word “one”. A note can state both 24 V and 48 V.

The tool reads those files and lines them up. It keeps the original text. There are 137 parts-list lines. One line is set aside.

Three kinds of relationship stay in three separate boxes:

1. **Identity.** Different spellings of one real part.
2. **Similarity.** Two different parts that look close. They stay two parts. The list is a question for an engineer, not a declaration that one can replace the other.
3. **Nordic-only.** A part that exists on purpose for the cold-weather train.

## 1. Workflow

This page is the map. It does not show parts. It shows ten steps.

1. **Ingest.** Six spreadsheets are copied in. 137 parts-list lines. Original words are kept.
2. **Validate.** One row was too broken to use. Other rows carry soft warnings and stay in the list.
3. **Normalize.** Spelling, units, and supplier names are cleaned beside the original.
4. **Source entities.** Rows become things you can name: 133 components, 37 assemblies, 24 suppliers.
5. **Proposals.** 57 suggestions are waiting. Nobody has said yes or no.
6. **Human decision.** The buttons on the Proposals page. They save only while `serve` is running. The spreadsheet row stays as it was.
7. **Canonical model.** The official names the reports may trust. 85 official parts exist. Most of them were spelled only one way, so they did not need a human yes. The air controller is the exception.
8. **Reuse snapshot.** The last pill, Preview · Reuse.
9. **Compare.** Two trains side by side.
10. **Later.** Extra filters. Skip this in the demo.

Say: “The lists come from engineering, purchasing, and notes, and they spell the same part in different ways. The program proposes. A person decides. The original row is kept.”

## 2. Normalize

Raw value on the left, cleaned value on the right.

**Reference aliases.** Part numbers folded to one spelling.

- `CTRL-AIR01` becomes `CTRL-AIR-01`.
- `CTRL-AIR-O1` becomes `CTRL-AIR-01`. The letter O was typed instead of zero.
- `CTRL-HVAC-001` becomes `CTRL-AIR-01`.
- `FAN-AIR01` becomes `FAN-AIR-01`.

**Units.** `pcs` and `units` both become `EA`, meaning one piece.

**Supplier names.** `Siemens` and `Siemens Mobility GmbH` both become `SIEMENS MOBILITY`. `Faiveley` and the longer Faiveley name both become `FAIVELEY TRANSPORT`.

**Quarantine.** Spreadsheet row 32. The quantity is the word “one”. That line is copied to a side list with the reason, and it is left out of the parts list. The rest of the file continues. There is no screen to change “one” into 1 and put the line back. Say: “We catch the broken row and keep the original text. Correcting it inside the tool would be a later module.”

Softer problems stay on the list. A missing description or an empty supplier is counted as a warning, not removed.

**Note languages.** The engineers’ sentences. One English note says `CTRL-HVAC-001` is equivalent to `CTRL-AIR-01`. Another says the Nordic temperature sensor is required below −20 °C. The original sentence is kept. Language is only a label.

## 3. Proposals

A proposal is the program saying “I think these records are related. Please decide.” All 57 rows start as **PENDING**.

The first table is the one with the buttons. It has every waiting row:

- **4 identity** rows, all the air controller: `CTRL-AIR-01`, `CTRL-AIR01`, `CTRL-HVAC-001`, `CTRL-AIR-O1`.
- **46 similarity** rows. The Kind column says `functional_similarity` and does not print the other part number. The other number is stored. Scroll to **Similar, not merged**, or read **Worth a look** on the Reuse page, to see the pair (`BAT-TEMP-01` with `CAPT-TEMP-01`, `BATT-MON-01` with `BATT-MON-EXP`).
- **7 Nordic-only** rows, kind `variant_specific`.

**Accept on an identity row.** The first accept creates one official part named `CTRL-AIR-01`. Each of the four suggestions already lists the other spellings. Accepting the next spelling reuses that same official id. A spelling you have not accepted yet stays off the official list. Accepting the first row does not silently accept the other three.

**Reject on an identity row.** Stores “a person said no”, plus the reason you typed. That spelling stays off the official list.

**Accept on a similarity row.** Stores “a person agreed they are close.” It does not give them one official id and does not rename one to the other. The Worth a look list is built from the pairs themselves and does not wait for this yes or no. The button is a note. The meeting list does not depend on it.

**Reject on a similarity row.** Stores “a person said this pair is not a match.” Same limit: the current Worth a look list does not drop the pair because of that click.

**Redirect.** Closes the current suggestion and adds a new one, still waiting, aimed at the source id you typed. That new row still has to be accepted. Redirect alone does not merge two parts.

The short table “Same part, different ids” shows only the identity kind, so it looks like only the air controller exists. The other 53 rows are in the long table above it.

If the program missed two parts that should have been the same, this screen cannot create that link. You can only answer suggestions the program already made. A later screen could let a person create the missing identity link.

## 4. Canonical

“Canonical” means the official name the reports are allowed to use.

**0 accepted identity clusters** is expected before anyone presses Accept. The air-controller family does not yet share one official id.

**130 canonical BOM rows** are parts-list lines that were safe to place on the official list. A part spelled only one way goes on that list without a human click. That is why 85 official parts can exist while zero identity clusters have been accepted.

**7 unresolved lines** are the air-controller lines still waiting, on Standard, Comfort, Nordic, High Capacity, and Export. The reason is `identity_pending`. Those lines stay in the spreadsheets. They are held out of the official list until a person accepts or rejects them.

## 5. Compare

The dropdown is “which two trains?” It opens on Standard versus Nordic.

Each block is one assembly, one chapter. The numbers:

- **shared** — the part is on both trains
- **left-only** — only on the left train, Standard in the default pair
- **right-only** — only on the right train, Nordic in the default pair
- **overlap 1.0** — every agreed part in that chapter is on both trains
- **overlap 0.0** — nothing in that chapter is shared
- A highlighted row means the overlap is at least half

**BAT-M06** is the clean example: overlap 1.0, shared 3. The battery module is the same chapter on Standard and Nordic, and all three agreed parts are on both. Say: “We already use this battery module on both trains.”

**HVAC-M01** and **HVAC-N01** are two chapter codes. The Nordic HVAC chapter is not merged with the Standard one because the names sound alike. Parts tagged `variant_specific`, such as `BRAKE-CTRL-ND`, are the cold-weather choice.

Switch the dropdown to **REGIO-EXPORT versus REGIO-STD**. Find a part tagged **blocked**. Both words **Prototype** and **Released** stay visible, with a file name and a row number. The page does not pick a winner.

Every part line names the file and the row, such as `bom_export.csv row 19`.

## 6. Preview · Reuse

The one-page briefing. Five trains, 137 parts-list lines, 1 quarantined row, 33 shared parts, 24 candidates.

**Already reused.** The same official part or assembly appears on more than one train. `BAT-M06` is on Comfort, Nordic, and Standard. The page shows 8 of 33.

**Worth a look.** Pairs that resemble each other and stay two parts. This is the similarity list with both names visible. Nothing here designs a new assembly. A later module could score parts against each other while someone is conceiving a variant. That score does not need a yes/no stored in advance.

**Intentional differences.** Nordic-only parts, such as `APC-750-24-ND` and `BRAKE-CTRL-ND`.

**Blocked.** The evidence disagrees, so nothing was overwritten. Both **24 V DC** and **48 V DC** stay on parts such as `CTRL-AIR-01`. **Prototype** and **Released** stay on `PAX-COUNT-MOD-E`. An ERP material marked **OBSOLETE** is listed on its own.

**Data issues.** Bad or duplicate rows, separate from “is this the same part?” The quantity “one” is `bom_export.csv` row 32. Some parts-list keys appear twice. `pcs` and `units` becoming `EA` is information, not a conflict. Hundreds of missing descriptions and empty suppliers are one summary, so they do not become hundreds of defect cards.

## Closing sentence

“We did not build a system that silently merges parts. It reads the exports, keeps the original row, and proposes matches with a reason. A person accepts or rejects identity. Similar parts stay two parts and are only listed for review. Conflicts stay visible with both values.”
