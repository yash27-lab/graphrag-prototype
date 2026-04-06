# Supply Chain Benchmark

**Paragraph 1 (The Mine & Supplier):**
The Salar de Atacama Lithium Mine has recently announced an indefinite strike due to labor disputes, completely halting operations. This facility is the sole provider of high-grade lithium carbonate to ElectroChem Industries, a major battery manufacturer based in Nevada.

**Paragraph 2 (The Manufacturer & The Product):**
ElectroChem Industries holds an exclusive contract to supply next-generation solid-state battery packs to Apex Motors. Apex Motors is currently ramping up production for their highly anticipated flagship vehicle, the "Apex Nova EV", which relies entirely on these specific solid-state battery packs.

**Query to Test:**
"How does a strike at the Lithium mine affect the production of the new EV model?"

**Expected Traversal:**
Salar de Atacama Lithium Mine -> (supplies) -> ElectroChem Industries -> (supplies) -> Apex Nova EV

---

# Corporate Mergers Benchmark

**Paragraph 1 (The Product & Acquisition):**
WhatsApp, the ubiquitous messaging application known for its end-to-end encryption, was founded by Jan Koum and Brian Acton. In 2014, the messaging platform was acquired by Facebook Inc. in a landmark deal worth $19 billion.

**Paragraph 2 (The Rebrand & Leadership):**
Years after a series of high-profile acquisitions, Facebook Inc. underwent a massive corporate restructuring and rebranded itself as Meta Platforms Inc. to reflect its new focus on the metaverse. Mark Zuckerberg, who originally founded the social network, remains the CEO of Meta Platforms Inc.

**Query to Test:**
"Who is the CEO of the parent company of WhatsApp?"

**Expected Traversal:**
WhatsApp -> (acquired by) -> Facebook Inc. -> (rebranded to) -> Meta Platforms Inc. -> (CEO is) -> Mark Zuckerberg

---

# Medical Research Benchmark

**Paragraph 1 (The Disease & The Drug):**
Neuro-Degenerative Syndrome X (NDS-X) is a rare genetic disorder characterized by the rapid breakdown of motor neurons. Recent clinical trials have shown that the experimental drug "Lumira-200" is highly effective in treating the symptoms of NDS-X and slowing its progression.

**Paragraph 2 (The Drug Mechanism & The Pathway):**
Pharmacological studies reveal that "Lumira-200" functions primarily by acting as a potent inhibitor of the enzyme Kinase-Delta. Biochemical mapping further demonstrates that Kinase-Delta is a critical regulatory component within the broader Apoptosis-Alpha protein pathway.

**Query to Test:**
"What protein pathway is targeted by the drug treating Disease X?"

**Expected Traversal:**
NDS-X -> (treated by) -> Lumira-200 -> (inhibits) -> Kinase-Delta -> (part of) -> Apoptosis-Alpha protein pathway
