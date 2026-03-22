Ask GPT-5.4 a technical question via opencode CLI.

Usage: /ask-gpt <question>

Run the following command with the user's question:

```bash
cd "G:/Privacy/zapretgui" && opencode run -m openai/gpt-5.4 "$ARGUMENTS"
```

Important:
- Use timeout of 180000ms (3 minutes)
- If the question is complex and you have other work to do, run in background
- After getting the response, summarize the key findings for the user in Russian
- If opencode is not available, inform the user to install it: `npm install -g opencode`
