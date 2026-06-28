# 079-fix-mp3-metadata

- OSWorld example: `multi_apps/3f05f3b9-29ba-4b6b-95aa-2204697ffc06`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Music/Cheng Xiang - Missing You.mp3, /home/user/Music/Han Baoyi - Tears of Dancing Girl.mp3, /home/user/Music/Huang An - I Know Missing is Painful.mp3, /home/user/Music/Chen Shaohua - Red Daughter.mp3, /home/user/Music/Zhou Xuan - Nights in Shanghai.mp3
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
