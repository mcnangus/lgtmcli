# LGTM CLI Examples

## Basic Usage

### View Commands
```bash
# View all comments on a PR
./lgtm view -p 123

# View comments on a specific file
./lgtm view -p 123 -F src/main.py

# View comments on a specific line
./lgtm view -p 123 -F src/main.py -l 42

# View comments on a line range
./lgtm view -p 123 -F src/main.py -l 10-20

# Auto-detect PR from current branch
./lgtm view
```

### Comment Commands
```bash
# Add a PR-level comment
./lgtm comment -p 123 -c "test pr comment"

# Add a file-level comment
./lgtm comment -p 123 -F src/main.py -c "needs refactoring"

# Add a line-specific comment
./lgtm comment -p 123 -F src/main.py -l 15 -c "variable name unclear"

# Add a multi-line comment
./lgtm comment -p 123 -F src/main.py -l 10-15 -c "this block needs work"

# Open editor for comment (no -c flag)
./lgtm comment -p 123

# Open editor for file comment
./lgtm comment -p 123 -F src/main.py

# Auto-detect PR from current branch
./lgtm comment -c "looks good"
```

### Edit Commands
```bash
# Edit PR-level comment
./lgtm edit -p 123

# Edit file-level comment
./lgtm edit -p 123 -F src/main.py

# Edit line-specific comment
./lgtm edit -p 123 -F src/main.py -l 42

# Auto-detect PR from current branch
./lgtm edit
```

### Approve Commands
```bash
# Approve without comment
./lgtm approve -p 123

# Approve with comment
./lgtm approve -p 123 -c "LGTM! Great work!"

# Auto-detect PR from current branch
./lgtm approve -c "Looks good to me"
```

## Advanced Usage

### Thread Management
When adding comments to lines or files that already have comments, the tool will:
1. Show existing comments
2. Ask if you want to reply to the existing thread
3. If not, ask if you want to create a new thread

### Editor Integration
If you don't provide `-c` with the comment or edit commands, the tool will:
1. Open your default editor (set via `EDITOR` environment variable)
2. Let you write/edit the comment
3. Save the comment when you close the editor

Set your preferred editor:
```bash
export EDITOR=vim
export EDITOR=nano
export EDITOR=code  # VS Code
```

### Line Range Formats
You can specify line ranges in multiple formats:
- Single line: `-l 42`
- Range with dash: `-l 10-20`
- Range with colon: `-l 10:20`

## Help Commands
```bash
# Show all available commands
./lgtm --help

# Show help for specific command
./lgtm view --help
./lgtm comment --help
./lgtm edit --help
./lgtm approve --help

# Show version
./lgtm --version
```

## Tips

1. **PR Auto-detection**: If you're on a branch with an open PR, you can omit the `-p` flag
2. **Editor Comments**: For longer comments, omit the `-c` flag to use your editor
3. **File Paths**: Use relative paths from the repository root
4. **Thread Replies**: The tool will prompt you when replying to existing comments
5. **Empty Comments**: The tool won't allow you to save empty comments

## Common Workflows

### Code Review Workflow
```bash
# 1. View all comments
./lgtm view -p 123

# 2. Add specific line comments
./lgtm comment -p 123 -F src/api.py -l 45 -c "Consider error handling"
./lgtm comment -p 123 -F src/api.py -l 67 -c "Good refactoring!"

# 3. Approve the PR
./lgtm approve -p 123 -c "LGTM with minor suggestions"
```

### Quick Approval
```bash
# For PRs from your current branch
./lgtm approve -c "Looks good!"
```

### Detailed Review
```bash
# View the code, add comments, then approve
./lgtm view -p 123
./lgtm comment -p 123 -F src/main.py -l 100-110 -c "this needs optimization"
./lgtm comment -p 123 -c "Overall looks good, just one suggestion"
./lgtm approve -p 123
```
