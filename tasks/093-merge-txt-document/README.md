# 093-merge-txt-document

- OSWorld example: `multi_apps/98e8e339-5f91-4ed2-b2b2-12647cb134f4`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/concat.docx
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
