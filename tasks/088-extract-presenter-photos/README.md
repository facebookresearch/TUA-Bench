# 088-extract-presenter-photos

- OSWorld example: `multi_apps/82e3c869-49f6-4305-a7ce-f3e64a0618e7`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Shell start: `/home/user/Desktop`
- Seeded input folder: `/home/user/Desktop/IDS LLM seminar/`
- Output contract: `/home/user/Desktop/presenter.zip`, which must unzip on the Desktop to recreate `/home/user/Desktop/presenter/DSC00657.jpg`, `/home/user/Desktop/presenter/DSC00574.jpg`, `/home/user/Desktop/presenter/DSC00554.jpg`, and `/home/user/Desktop/presenter/DSC00495.jpg`
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
