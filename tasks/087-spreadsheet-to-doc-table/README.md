# 087-spreadsheet-to-doc-table

- OSWorld example: `multi_apps/81c425f5-78f3-4771-afd6-3d2973825947`
- Preserved: user intent and verifier semantics, but rewritten as a CLI-native `/app` contract.
- Input contract: `/app/OSP_Envelope_Price-List_2023_5000.xlsx`
- Output contract: `/app/price.docx`
- Task intent: copy the current sheet into a Writer table while preserving the spreadsheet table's original formatting as closely as possible.
- Reward contract: the verifier reads only the durable artifacts defined above.
