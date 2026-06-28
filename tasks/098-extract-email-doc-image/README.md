# 098-extract-email-doc-image

- OSWorld example: `multi_apps/c2751594-0cd5-4088-be1b-b5f2f9ec97c4`
- Preserved: user intent and verifier semantics, but rewritten as a CLI-native `/app` contract.
- Input contract: `/app/.thunderbird`
- Output contract: `/app/background.png`, containing the first image extracted from the DOC attachment in the most recent `Notes` email
- Reward contract: the verifier reads only the durable artifacts defined above.
