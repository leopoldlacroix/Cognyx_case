# What is missing, what to tighten, and what comes later

The tool already answers the client question: which sub-assemblies are reused or reusable, and where the lists disagree. This note is the honest list for the meeting. Say the first section if Thomas asks. The second section is work still on this product. The third section is a later product, not this pilot.

## Missing now

These are gaps against the case and against what the pages suggest. They are not bugs in the path you will demo.

**The purchasing id is not joined to the air controller.** Scenario B in the case is one physical part written four ways in engineering and once in purchasing: `CTRL-AIR-01`, `CTRL-AIR01`, `CTRL-AIR-O1`, `CTRL-HVAC-001`, and the ERP material `MAT-10001`. The program groups the four engineering spellings because they normalize to the same string. `MAT-10001` stays a separate source component. The engineering note that says they are equivalent is stored and labeled by language. It is not the evidence that creates the identity proposal. If Thomas asks, say: “The spelling family is proposed. The ERP material number is the next link, and it is not in this build.”

**There is no explanation page.** Phase 5, not built, is `evidence.html`: one plain sentence per reuse row, candidate, blocker, and data issue, naming the records compared, what matched, what conflicted, and the source file and row. Conflicts, languages, bad rows, and lifecycle splits are already visible on Compare and Preview · Reuse. They are not gathered as “why this result.” Notes cannot be searched by French, English, or German.

**A similarity row does not name the other part.** The waiting table prints `functional_similarity` and the buttons. The partner (`BAT-TEMP-01` with `CAPT-TEMP-01`, and so on) is stored and appears under “Similar, not merged” and on “Worth a look.”

**A similarity yes or no does not change the reuse list.** Accept stores “a person agreed they are close” and leaves the canonical id empty. Reject stores a no. Worth a look is built from every similarity proposal, whatever the status. Identity is the decision that changes the official list.

**The screen cannot create a match the program never proposed.** Redirect closes the current suggestion and opens a new one, still waiting, aimed at a source id you type. It does not merge, and it cannot introduce a pair the detectors missed.

**A quarantined row cannot be repaired in the tool.** Row 32, quantity “one”, is copied aside with the original text and the reason, and left out of the parts list. Nothing edits that cell and puts the line back.

**Two meeting pieces sit outside this repo.** The email to deon@cognyx.io and francois@cognyx.io, and the ten minutes on something you have already shipped, are still to prepare. The repo tour can use the commit history, `AGENTS.md`, and these notes.

## Worth tightening on this product

Same pipeline. Clearer for the person in the room.

- Print the other part number, and the similarity type, on each waiting similarity row.
- After the first air-controller accept, show the shared official id on the three siblings that are still waiting, so it is obvious they join the same part when accepted one by one.
- On each blocker and data issue, keep the one-sentence reason next to both values and the file row. That is most of the Phase 5 page, without a new product.
- Show the engineering note next to the identity cluster when the note names those references, so the “why” is a sentence a person wrote, not only an alias in config.
- Let a reviewer add an identity link the detectors missed, with a rationale, instead of only answering an existing suggestion.
- Give quarantine a correction step: edit the quantity, record who changed it, and insert the line. Until then, say the catch exists and the repair does not.
- Treat similarity as a score for a later design pass, and stop asking for a yes/no that the reuse list ignores.

## Later, after the pilot

The case will ask how this would run inside Alstom’s network. The shape stays `source → normalize → reconcile → human decision → canonical model → analysis`. What changes is the surroundings.

- **Where it runs.** Today it is a SQLite file and a local page server on the laptop. On site it would sit inside their network, with logins, roles, and no data leaving the site.
- **How data arrives.** Today it is six CSV files copied by hand. Later, connectors to PLM and ERP, a schedule, and a load that only picks up what changed.
- **Who reviews.** Today one person, three buttons. Later a queue, more than one reviewer, and a history of who decided what.
- **How matches are proposed.** Today the rules are deterministic: normalized spelling, a hyphen-family check, and a Nordic-only check. A model could suggest extra candidates. A person would still accept identity. The model would not overwrite the spreadsheet.
- **What “reusable” means in design.** A score between two parts while someone is conceiving a variant, using specs and qualification, not a stored yes/no. Nordic-only parts stay out of that list.
- **A recommendation per chapter.** For a new tender: this assembly can be copied, these parts are already shared, these are Nordic-only, these are blocked, these are still unresolved. That is the sentence an engineering director can take into a bid review.
- **Cost next to that recommendation.** ERP already carries a cost. A later pass can show the cost of reusing the chapter against the cost of designing it again. The pilot lists the parts. It does not price them.
- **Sentences in the notes become proposals.** When a note says two references are the same part, including a purchasing id, that statement becomes an identity proposal with the sentence attached. A person still accepts it. The alias file is no longer the only way two ids meet.
- **Decisions survive the next export.** A new CSV drop updates the rows and keeps prior accepts, rejects, and redirects. Accepted spellings are added to the alias list, so the next load proposes less of what a person already settled.
- **A snapshot for the tender.** The official list as it stood on the day of the bid, so a later data drop does not rewrite what was shown to the client.
- **A file they can forward.** The one-page briefing as something Bruno can send inside Alstom, not only a page on a laptop.
- **A private scorecard.** How often the proposals were right, checked against held-out truth. That number is for us. The truth file is never shown in the demo.
- **What stays out.** No chatbot over the spreadsheets, no PDF extraction, no graph database for this dataset, and no autonomous merge.

The sentence if they ask what is missing for production: the boundaries are already the ones you would keep. What is missing is access control, a connection to their systems, a review queue, and the cross-system identity link the purchasing id still does not have.
