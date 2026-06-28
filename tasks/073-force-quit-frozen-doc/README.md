# 073-force-quit-frozen-doc

- OSWorld example: `multi_apps/2b9493d7-49b8-493a-a71b-56cd1f4d6908`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: vm_command_line
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
