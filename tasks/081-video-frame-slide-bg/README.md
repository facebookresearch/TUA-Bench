# 081-video-frame-slide-bg

- OSWorld example: `multi_apps/47f7c0ce-a5fb-4100-a5e6-65cd0e7429e5`
- Preserved: user intent and verifier semantics, but rewritten as a CLI-native `/app` contract.
- Input contract: `/app/landscape.mp4`, `/app/Robotic_Workshop_Infographics.pptx`
- Output contract: `/app/Robotic_Workshop_Infographics.pptx`
- Task intent: use the frame at `00:08` as the actual slide-2 background inside the saved presentation.
- Reward contract: the verifier extracts slide 2's saved background image from the output PPTX and compares it with the expected frame.
