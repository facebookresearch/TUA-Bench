# 072-save-speedtest-results

- OSWorld example: `multi_apps/26660ad1-6ebb-4f59-8cba-a8432dfe8d38`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Test/Speed/results.txt
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
