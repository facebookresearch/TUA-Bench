# 102-daily-email-report

- OSWorld example: `multi_apps/d9b7c649-c975-4f53-88f5-940b29c47247`
- Preserved: user intent and verifier semantics, but rewritten as a CLI-native `/app` contract.
- Input contract: `/app/.thunderbird`
- Output contract: `/app/report.xlsx` containing the latest five `daily` emails in chronological order with columns `sender_name`, `sender_address`, `subject`, `CC`, and `number_of_attachments`
- Reward contract: the verifier reads only the durable artifacts defined above.
