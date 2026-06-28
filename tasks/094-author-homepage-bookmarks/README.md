# 094-author-homepage-bookmarks

- OSWorld example: `multi_apps/a82b78bb-7fde-4cb3-94a4-035baf10bcf0`
- Preserved: user intent, bookmark-folder semantics, and evaluator behavior.
- Local transfer: this task keeps the paper input under `/app` but scores the saved browser state directly instead of requiring a live browser/PDF-viewer startup flow.
- Output contract: Chrome bookmarks JSON state under the default profile
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
