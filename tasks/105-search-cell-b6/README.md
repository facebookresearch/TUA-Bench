# 105-search-cell-b6

- OSWorld example: `multi_apps/f8cfa149-d1c1-4215-8dac-4a0932bad3c2`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: active_tab_info
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
