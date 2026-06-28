# 092-fix-tetris-bug

- OSWorld example: `multi_apps/9219480b-3aed-47fc-8bac-d2cffc5849f7`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Desktop/tetris/block.py, /home/user/Desktop/tetris/main.py, /home/user/Desktop/tetris/settings.py, /home/user/Desktop/tetris/tetris.py
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
