# 095-save-apple-searching-page

- OSWorld example: `multi_apps/aad10cd7-9337-4b62-b704-a857848cedf2`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/notes.docx
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
