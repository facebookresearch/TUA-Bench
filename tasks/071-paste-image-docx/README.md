# 071-paste-image-docx

- OSWorld example: `multi_apps/227d2f97-562b-4ccb-ae47-a5ec9e142fbb`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/image.docx
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
