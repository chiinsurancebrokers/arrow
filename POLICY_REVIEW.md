# Policy source review - CGT P804302600

HAL v3 was grounded against the original 39-page Group Travel Insurance certificate supplied by CHI.

## Verified anchors

- PDF page 3: Certificate CGT P804302600; Arrow Shipping Hellas S.A.; period 1 Sep 2026 to 31 Aug 2027.
- PDF page 4: Schedule of Benefits and headline sums insured.
- PDF page 11: External Journey, Insured Journey and Internal Journey definitions.
- PDF page 15: How to Make a Claim; Crawford online form and telephone registration.
- PDF page 17: Healix 24/7 medical assistance and Constellis kidnap/security contacts.
- PDF page 23: Travel Delay Inconvenience Benefit - €50 after the first completed 8-hour delay on the outward journey, then €50 for each subsequent completed hour, max €500 per claim; subsequent outward journeys max €150 per claim.
- PDF page 24: Section 3 Delayed Baggage - baggage lost for more than 12 hours on outward/onward journeys; reimbursement up to €1,000 for emergency replacement items.

## Wording discrepancy to preserve, not silently resolve

The General Definitions on PDF page 10 define "Delayed Baggage" by reference to personal property being delayed for at least 4 hours. The specific Section 3 benefit on PDF page 24 says reimbursement applies when baggage is lost for more than 12 hours.

HAL is instructed to quote the specific Section 3 payment trigger for benefit guidance and, when relevant, disclose that the general definition uses 4 hours. HAL must not make a legal interpretation that resolves the discrepancy. A live claim should be referred to CHI/Crawford.

## Source handling

`data/policy/arrow_2026_full.txt` is a page-marked text extraction of the supplied PDF so HAL can retrieve definitions and conditions with exact PDF-page provenance.

The original binary PDF is **not included in the GitHub overlay**, because `chiinsurancebrokers/arrow` is currently a public repository. The source SHA-256 is recorded in `data/policy/arrow_2026_source.json` so the extraction can be tied back to the exact supplied document.
