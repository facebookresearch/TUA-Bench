# 083-gemini-responses-docx

- OSWorld example: `multi_apps/5bc63fb9-276a-4439-a7c1-9dc76401737f`
- Preserved: user intent and verifier semantics, but rewritten as a CLI-native `/app` contract.
- Input contract: `/app/llm_answers.json`
- Output contract: `/app/gemini_results.docx`
- Task intent: copy every Gemini response value into the output DOCX, place each response in its own paragraph with a blank line between responses, and highlight every `Iliad` occurrence.
- Reward contract: the verifier reads only the durable artifacts defined above.
