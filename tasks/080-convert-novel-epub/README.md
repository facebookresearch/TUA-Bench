# 080-convert-novel-epub

- OSWorld example: `multi_apps/42d25c08-fb87-4927-8b65-93631280a26f`
- Preserved: user intent, intended application constraints, output contract, and evaluator behavior.
- Local simplifications: GUI launch and save choreography were reduced when only the final artifact or saved app state mattered; Google Drive outputs use the local mirror at `/home/user/Drive`.
- Output contract: /home/user/Documents/Novels/Pass Through/Pass Through.epub, /home/user/Documents/Novels/Pass Through/Pass_Through.epub, /home/user/Documents/Novels/Pass Through/pass_through.epub
- Reward contract: the verifier returns the exact OSWorld metric score for this translated task.
