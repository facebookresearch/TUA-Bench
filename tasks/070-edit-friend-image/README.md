# 070-edit-friend-image

- OSWorld example: `multi_apps/09a37c51-e625-49f4-a514-20a773797a8a`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/pic.jpg
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
