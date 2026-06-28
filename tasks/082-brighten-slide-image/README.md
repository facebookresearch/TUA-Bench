# 082-brighten-slide-image

- OSWorld example: `multi_apps/4c26e3f3-3a14-4d86-b44a-d3cedebbb487`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: cloud_file
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
