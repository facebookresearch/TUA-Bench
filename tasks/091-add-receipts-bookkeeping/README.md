# 091-add-receipts-bookkeeping

- OSWorld example: `multi_apps/8e116af7-7db7-4e35-a68b-b0939c066c78`
- Preserved: the bookkeeping workbook, receipt set, and exact OSWorld `compare_table` metric rules.
- Local adjustments: the task now uses an explicit CLI-native file contract under `/app`, and the environment is trimmed to the terminal, OCR, PDF, and spreadsheet dependencies the task actually needs.
- Input contract: `/app/my_bookkeeping.xlsx`, `/app/receipt_0.jpeg`, `/app/receipt_1.jpg`, `/app/receipt_2.jpg`, `/app/receipt_3.pdf`, `/app/receipt_4.jpg`
- Output contract: `/app/my_bookkeeping.xlsx`
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
