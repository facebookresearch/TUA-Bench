From `/app/llm_answers.json`, Copy each Gemini response exactly as it appears in the JSON file's source text (i.e., the escaped form). Do NOT JSON-decode the strings. \n stays as \n, \" stays as \". The .docx should look identical to what you'd see opening the JSON in a text editor. 
Specifically look at the sentences in the responses that contain `Iliad`.
Put each response in its own paragraph with a blank line between responses, and highlight every occurrence of `Iliad` word.
Input: `/app/llm_answers.json`.
Output: `/app/gemini_results.docx`.
Use command-line tools and save only the durable output artifacts described above.
