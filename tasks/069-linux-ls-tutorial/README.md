# 069-linux-ls-tutorial

- OSWorld example: `multi_apps/02ce9a50-7af2-47ed-8596-af0c230501f8`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/ls.png, /home/user/Desktop/ls.png, /home/user/Desktop/ls.png
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
