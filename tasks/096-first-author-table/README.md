# 096-first-author-table

- OSWorld example: `multi_apps/b5062e3e-641c-4e3a-907b-ac864d2e7652`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/authors.xlsx
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
