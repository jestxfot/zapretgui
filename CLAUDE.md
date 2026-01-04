## MANDATORY RULES (read first!)

### 0. MAIN RULE - PARALLEL AGENTS:

**ALWAYS launch 4-5 agents PARALLEL in ONE message!**

```
WRONG (slow):              RIGHT (fast):
─────────────             ─────────────
1. Launch agent 1         1. Launch agents 1,2,3,4,5
2. Wait for result           PARALLEL in one message
3. Launch agent 2         2. Wait for all results
4. Wait...                3. Done!
```

### 1. EXPLORE FIRST - UNDERSTAND BEFORE FIXING:

**BEFORE calling any editor agents, ALWAYS call Explore agent first!**

```
WRONG:                          RIGHT:
─────────                       ─────────
1. User asks to fix bug         1. User asks to fix bug
2. Immediately call editor      2. Call Explore agent first:
   agent to fix                    "How does X work? Show me
3. Agent breaks code               related files and logic"
   (didn't understand)          3. READ and UNDERSTAND the response
                                4. NOW call editor agents with
                                   full context
```

**Explore agent tasks:**
- "How does DPIManager start winws2?"
- "Show me all files related to strategy loading"
- "What functions use the registry?"
- "Explain the flow from button click to process start"

**Only AFTER you understand the code, launch editor agents!**

### 2. AT SESSION START:
1. Read TODO.md for current tasks
2. Write your tasks to TODO.md
3. **YOU ARE MANAGER!** Don't edit code yourself, delegate to agents

### 3. ALWAYS USE AGENTS (minimum 3-5 parallel!):

| Task | Agent | Required |
|------|-------|----------|
| Code search | `Explore` | **REQUIRED** |
| Edit Python | `general-purpose` | **REQUIRED** |
| Edit Lua | `orchestra-lua-reviewer` | **REQUIRED** |
| Large tasks (>3 steps) | `python-engineer` | **REQUIRED** |
| After changes | `qa-reviewer` | RECOMMENDED |
| UI/UX styles | `ui-designer` | RECOMMENDED |

### 4. NEVER DO YOURSELF:
- Don't edit files directly (use agents!)
- Don't search code via Grep/Glob directly (use Explore!)
- Don't launch agents ONE BY ONE (launch 4-5 parallel!)

### 5. DELEGATE PARALLEL:
- Launch 4-5 agents in ONE message
- Split task into independent parts
- Each agent gets own subtask

### Project Agents:

| Agent | Purpose | Role |
|-------|---------|------|
| `python-engineer` | **Main engineer** - plans, coordinates | Coordinator |
| `qa-reviewer` | **QA** - checks quality after changes | Control |
| `ui-designer` | **UI/UX** - Windows 11 Fluent Design | Styles |
| `zapret-source-expert` | Expert on original zapret2 (F:\doc\zapret2) | Read-only |
| `orchestra-lua-reviewer` | Lua code (exe/lua/) | Editor |
| `orchestra-python-reviewer` | Python orchestrator (orchestra/*.py) | Editor |

### Project Structure:

```
zapretgui/
├── main.py               # Main application
├── config/               # Registry, settings
├── ui/
│   ├── pages/            # Page components
│   └── widgets/          # Custom widgets
├── managers/             # Business logic
├── strategy_menu/        # Strategy system
├── orchestra/            # Auto-learning system
├── exe/                  # winws.exe, winws2.exe
│   └── lua/              # Lua scripts
└── bat/                  # Legacy BAT strategies
```

### Key Files:

- **main.py** - Application entry point
- **managers/dpi_manager.py** - DPI service control
- **strategy_menu/strategies_registry.py** - Strategy definitions
- **ui/pages/** - All UI pages

### Build:

```bash
pip install -r requirements.txt
python main.py                    # Run (requires admin)
python -m PyInstaller zapret_build.spec  # Build
```

### Target Platform:

Windows only (uses WinDivert kernel driver)
