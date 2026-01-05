$env:HTTPS_PROXY = "http://127.0.0.1:6666"
$prompt = Get-Content "H:\Privacy\zapretgui\CLAUDE.md" -Raw -Encoding UTF8
claude --dangerously-skip-permissions --append-system-prompt $prompt
