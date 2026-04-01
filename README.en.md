# Cloud-code Cracked Version

English | [简体中文](./README.md)

## Source Code Study Docs
Welcome to try it: https://cloud-code-study.vercel.app/
- https://github.com/Janlaywss/cloud-code-study

## How to Use
- The source code in this repository has already been restored. See the `claude-code-source` directory.
- How to compile and run it locally? Please refer to `claude-code-source/README.md`.
  - My computer is a MacBook Pro with an Apple chip. So the Bun runtime architecture used there is adapted for Apple chips.
  - For other CPU chip architectures, please figure out the installation yourself, or let AI handle it directly.
- There is an `ai-cloud-xxxx.tgz` file in the root directory. This is the original npm package for 2188.

## Restoration Method Used in This Repository
```bash
# 1. Download the package from npm
npm pack @anthropic-ai/claude-code --registry https://registry.npmjs.org

# 2. Extract it
tar xzf anthropic-ai-claude-code-2.1.88.tgz

# 3. Parse cli.js.map and write sourcesContent back to the original paths
node -e "
const fs = require('fs');
const path = require('path');
const map = JSON.parse(fs.readFileSync('package/cli.js.map', 'utf8'));
const outDir = './claude-code-source';
for (let i = 0; i < map.sources.length; i++) {
  const content = map.sourcesContent[i];
  if (!content) continue;
  let relPath = map.sources[i];
  while (relPath.startsWith('../')) relPath = relPath.slice(3);
  const outPath = path.join(outDir, relPath);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, content);
}
"
```

The source map contains **4756** source files and their complete source code (`sourcesContent`), which can restore all original TypeScript/TSX code without loss.

## Directory Structure

```text
.
├── src/                  # Core source code (1902 files)
│   ├── main.tsx          # Application entry
│   ├── Tool.ts           # Tool base class
│   ├── Task.ts           # Task management
│   ├── QueryEngine.ts    # Query engine
│   ├── commands.ts       # Command registration
│   ├── tools.ts          # Tool registration
│   ├── assistant/        # Session history management
│   ├── bootstrap/        # Startup initialization
│   ├── bridge/           # Bridge layer (31 files)
│   ├── buddy/            # Sub-agent system (6)
│   ├── cli/              # CLI parameter parsing and entry (19)
│   ├── commands/         # Slash command implementation (207)
│   ├── components/       # Terminal UI components, based on Ink (389)
│   ├── constants/        # Shared constants (21)
│   ├── context/          # Context management (9)
│   ├── coordinator/      # Agent coordinator (1)
│   ├── entrypoints/      # Various entry points (8)
│   ├── hooks/            # Lifecycle hooks (104)
│   ├── ink/              # Custom Ink terminal rendering engine (96)
│   ├── keybindings/      # Shortcut key management (14)
│   ├── memdir/           # Memory directory system (8)
│   ├── migrations/       # Data migrations (11)
│   ├── moreright/        # Permission system (1)
│   ├── native-ts/        # Native TS tools (4)
│   ├── outputStyles/     # Output formatting (1)
│   ├── plugins/          # Plugin system (2)
│   ├── query/            # Query processing (4)
│   ├── remote/           # Remote execution (4)
│   ├── schemas/          # Data schema definitions (1)
│   ├── screens/          # Screen views (3)
│   ├── server/           # Server mode (3)
│   ├── services/         # Core services (130)
│   ├── skills/           # Skill system (20)
│   ├── state/            # State management (6)
│   ├── tasks/            # Task execution (12)
│   ├── tools/            # Tool implementation (184)
│   ├── types/            # TypeScript type definitions (11)
│   ├── upstreamproxy/    # Upstream proxy support (2)
│   ├── utils/            # Utility functions (564)
│   ├── vim/              # Vim mode (5)
│   └── voice/            # Voice input (1)
├── vendor/               # Internal vendor code (4 files)
│   ├── modifiers-napi-src/   # Native module for key modifiers
│   ├── url-handler-src/      # URL handling
│   ├── audio-capture-src/    # Audio capture
│   └── image-processor-src/  # Image processing
└── node_modules/         # Packaged third-party dependencies (2850 files)
```

## Core Module Description

| Module | File Count | Description |
|------|--------|------|
| `utils/` | 564 | Utility function set — file I/O, Git operations, permission checks, diff handling, etc. |
| `components/` | 389 | Terminal UI components, built based on Ink (the CLI version of React) |
| `commands/` | 207 | Slash command implementation, such as `/commit`, `/review`, etc. |
| `tools/` | 184 | Agent tool implementation — Read, Write, Edit, Bash, Glob, Grep, etc. |
| `services/` | 130 | Core services — API client, authentication, configuration, session management, etc. |
| `hooks/` | 104 | Lifecycle hooks — interception and permission control before and after tool execution |
| `ink/` | 96 | Self-developed Ink rendering engine, including layout, focus management, and rendering optimization |
| `bridge/` | 31 | Bridge layer — communication between IDE extensions and the CLI |
| `skills/` | 20 | Skill loading and execution system |
| `cli/` | 19 | CLI parameter parsing and startup logic |
| `keybindings/` | 14 | Keyboard shortcut binding and customization |
| `tasks/` | 12 | Background tasks and scheduled task management |

## Stats

| Metric | Value |
|------|------|
| Total source files | 4,756 |
| Core source code (`src/ + vendor/`) | 1,906 files |
| Third-party dependencies (`node_modules/`) | 2,850 files |
| Source map size | 57 MB |
| Package version | 2.1.88 |
