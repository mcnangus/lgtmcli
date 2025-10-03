# LGTM CLI

A command-line tool for viewing, editing, and managing GitHub pull request comments and approvals. This tool provides a streamlined interface for PR review workflows, allowing you to comment on specific files and lines, approve pull requests, and manage comment threads.

## Features

- **View Comments**: Browse existing PR comments at different levels (PR-level, file-level, line-specific)
- **Add Comments**: Add comments to pull requests, specific files, or specific lines with multiline support
- **Edit Comments**: Modify existing comments using your preferred editor (vim/nano/etc.)
- **Approve PRs**: Approve pull requests with optional comments
- **Thread Management**: Continue existing comment threads or create new ones
- **Auto-detection**: Automatically detects GitHub repository and PR from git configuration
- **Multiline Comments**: Support for commenting on line ranges (e.g., lines 5-10)
- **Editor Integration**: Opens your preferred editor for writing/editing comments

## Prerequisites

- Python 3.x
- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated
- Git repository with GitHub remote origin configured

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd lgtmcli
   ```

2. Make the script executable:
   ```bash
   chmod +x lgtm
   ```

3. Optionally, add to your PATH for global usage:
   ```bash
   sudo cp lgtm /usr/local/bin/
   sudo cp lgtm.py /usr/local/bin/
   ```

## Usage

### Command Structure

The tool uses a command-based interface with Click:

```bash
./lgtm <command> [options]
```

Available commands:
- `view` - View comments on a pull request, file, or specific line(s)
- `comment` - Add a comment to a pull request, file, or specific line(s)
- `edit` - Edit an existing comment on a pull request, file, or specific line(s)
- `approve` - Approve a pull request with an optional comment

### Migration from Old CLI

If you were using the old argparse-based CLI, here's how to migrate:

| Old Command | New Command |
|-------------|-------------|
| `lgtm -p 123 --view` | `lgtm view -p 123` |
| `lgtm -p 123 --comment "text"` | `lgtm comment -p 123 -c "text"` |
| `lgtm -p 123 --edit` | `lgtm edit -p 123` |
| `lgtm -p 123 --approve` | `lgtm approve -p 123` |
| `lgtm -p 123 --approve --comment "text"` | `lgtm approve -p 123 -c "text"` |

### Common Options

- `-p, --pr <number>`: The pull request number (auto-detects from branch if not provided)
- `-F, --file <path>`: Target a specific file (e.g., `src/main.py`)
- `-l, --line <number|range>`: Target a specific line or range (e.g., `42`, `5-10`, `5:10`)
- `-c, --comment-text <text>`: Comment text (if not provided for comment/edit commands, opens editor)

### Examples

#### Approve a Pull Request
```bash
# Simple approval
./lgtm approve -p 123

# Approve with comment
./lgtm approve -p 123 -c "LGTM! Great work on the implementation."

# Auto-detect PR from current branch
./lgtm approve
```

#### View Comments
```bash
# View all comments on a PR
./lgtm view -p 123

# View comments on a specific file
./lgtm view -p 123 -F src/main.py

# View comments on a specific line
./lgtm view -p 123 -F src/main.py -l 42

# Auto-detect PR from current branch
./lgtm view
```

#### Add Comments
```bash
# Add PR-level comment (opens editor if -c not provided)
./lgtm comment -p 123 -c "Overall this looks good, just a few minor suggestions."

# Add file-level comment
./lgtm comment -p 123 -c "Consider adding error handling here" -F src/utils.py

# Add line-specific comment
./lgtm comment -p 123 -c "This variable name could be more descriptive" -F src/main.py -l 15

# Add multiline comment (lines 10-15)
./lgtm comment -p 123 -c "This entire function needs refactoring" -F src/main.py -l 10-15

# Open editor for new comment (when -c not provided)
./lgtm comment -p 123 -F src/main.py -l 20

# Auto-detect PR from current branch
./lgtm comment -c "test pr comment"
```

#### Edit Comments
```bash
# Edit existing PR comment (opens editor)
./lgtm edit -p 123

# Edit existing file-level comment  
./lgtm edit -p 123 -F src/main.py

# Edit existing line-specific comment
./lgtm edit -p 123 -F src/main.py -l 15

# Auto-detect PR from current branch
./lgtm edit
```

## Comment Levels

The tool supports three levels of commenting:

1. **PR-level**: Comments that apply to the entire pull request
2. **File-level**: Comments that apply to a specific file
3. **Line-level**: Comments that apply to a specific line or range of lines in a file

### Auto-Detection

The tool can automatically detect the PR number from your current git branch:

```bash
# If your current branch has an open PR, it will be auto-detected
./lgtm view    # No need to specify -p if PR can be detected
./lgtm approve # Works with any command
./lgtm comment -c "test comment"
```

### Multiline Comments

You can comment on ranges of lines using different formats:

```bash
# Comment on lines 5 through 10
./lgtm comment -p 123 -F src/main.py -l 5-10 -c "This block needs optimization"

# Alternative syntax
./lgtm comment -p 123 -F src/main.py -l 5:10 -c "Consider extracting this logic"
```

## Editor Integration

The tool integrates with your preferred text editor for writing and editing comments:

- Respects the `EDITOR` environment variable (falls back to `nano`)
- Opens a temporary file for editing
- Supports rich text/markdown formatting
- Validates that comments are not empty before submission

Set your preferred editor:
```bash
export EDITOR=vim    # or code, emacs, etc.
```

## Thread Management

When adding comments to files or lines that already have existing comments, the tool will:

1. Display existing comments and any reply threads
2. Ask if you want to continue the existing thread
3. If not, ask if you want to create a new thread
4. Handle the comment creation accordingly

## How It Works

The tool uses the GitHub CLI (`gh`) and GitHub REST API to:

1. Auto-detect the repository from your git remote configuration
2. Validate that the specified PR exists
3. Fetch existing comments using the GitHub API
4. Create, update, or display comments as requested
5. Handle PR approvals through the GitHub CLI

## Limitations

- ~~Edit mode for file and line-level comments is not yet implemented~~ ✅ **RESOLVED**
- ~~Multiline comment ranges are planned but not implemented~~ ✅ **RESOLVED** 
- ~~Interactive editor integration is planned but not implemented~~ ✅ **RESOLVED**

## Error Handling

The tool includes validation for:
- Missing or invalid PR numbers (with auto-detection fallback)
- Conflicting operation modes
- Missing required arguments
- Empty comments
- Unchanged edits
- Invalid line range formats

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! The major TODOs have been resolved, but areas for further improvement include:

- ~~Complete edit mode implementation for all comment types~~ ✅ **COMPLETED**
- ~~Add interactive editor support (vim/nano)~~ ✅ **COMPLETED**
- ~~Implement multiline comment ranges~~ ✅ **COMPLETED**
- Add fuzzy finding for comment selection
- Improve error messages and user experience
- Add configuration file support
- Add batch operations for multiple PRs

## Author

Angus McNamara
