#!/usr/bin/env python3

import click
import json
import subprocess
import tempfile
import os
import sys


class FileNotInPRError(Exception):
    """Raised when trying to comment on a file not in the PR"""
    pass


class ValidationError(Exception):
    """Raised when GitHub API validation fails"""
    pass


class GHApi:
    headers=['-H', "Accept: application/vnd.github+json", '-H', "X-GitHub-Api-Version: 2022-11-28"]

    def __init__(self):
        """Initialize GitHub API client by parsing git remote URL"""
        remote = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode('utf-8').strip()
        if 'git@github.com' in remote:
            parts = remote.split(':')[1].split('/')
            self.org = parts[0]
            self.repo = parts[1].split('.')[0]
        elif 'https://github.com' in remote:
            parts = remote.split('/')
            self.org = parts[3]
            self.repo = parts[4].split('.')[0]
        else:
            raise Exception('Cannot parse `git config --get remote.origin.url`')

    def gh_api(self, path: str, method='GET', *args):
        try:
            return subprocess.check_output([
                'gh', 'api',
                '--method', method,
                *self.headers,
                f'/repos/{self.org}/{self.repo}/'+path,
                *args,
            ]).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            # Try to parse GitHub API error response
            if e.stderr:
                error_output = e.stderr.decode('utf-8')
            elif e.stdout:
                error_output = e.stdout.decode('utf-8')
            else:
                error_output = str(e)

            # Check for specific GitHub API error patterns
            if 'could not be resolved' in error_output and 'path' in error_output:
                # Extract file path from args if present
                file_path = "specified file"
                for i, arg in enumerate(args):
                    if arg == '-f' and i + 1 < len(args):
                        if args[i + 1].startswith('path='):
                            file_path = args[i + 1][5:]  # Remove 'path=' prefix
                        break

                raise FileNotInPRError(f"The file '{file_path}' is not part of this pull request's changes.\n"
                                     f"GitHub only allows comments on files that were modified in the PR.\n"
                                     f"Consider:\n"
                                     f"  • Adding a PR-level comment instead (omit --file option)\n"
                                     f"  • Checking if the file path is correct\n"
                                     f"  • Making sure the file was actually changed in this PR")
            elif 'Validation Failed' in error_output:
                raise ValidationError(f"GitHub API validation failed: {error_output}")
            else:
                # Re-raise the original error for other cases
                raise


def get_pr_from_branch():
    """Try to get PR number from current branch using GitHub CLI"""
    try:
        current_branch = subprocess.check_output(['git', 'branch', '--show-current']).decode('utf-8').strip()
        # Try to find PR for current branch
        pr_list = subprocess.check_output(['gh', 'pr', 'list', '--head', current_branch, '--json', 'number']).decode('utf-8').strip()
        prs = json.loads(pr_list)
        if prs:
            return prs[0]['number']
    except:
        pass
    return None


def open_editor(content="", suffix=".md"):
    """Open content in user's preferred editor and return the edited content"""
    editor = os.environ.get('EDITOR', 'nano')

    with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False) as f:
        f.write(content)
        temp_file = f.name

    try:
        subprocess.run([editor, temp_file], check=True)

        with open(temp_file, 'r') as f:
            edited_content = f.read().strip()

        return edited_content
    finally:
        os.unlink(temp_file)


def parse_line_range(line_str):
    """Parse line range string like '5', '5-10', or '5:10' into start and end line numbers"""
    if '-' in line_str:
        start, end = line_str.split('-', 1)
        return int(start), int(end)
    elif ':' in line_str:
        start, end = line_str.split(':', 1)
        return int(start), int(end)
    else:
        line_num = int(line_str)
        return line_num, line_num


def format_comment_header(file_path=None, line_start=None, line_end=None, author=None):
    """Format a nice header for comment display showing file, line info, and author"""
    if not file_path and line_start is None:
        header = "┌─ Pull Request Comment"
    else:
        header = "┌─"
        if file_path:
            header += f" {file_path}"
            if line_start is not None:
                if line_start == line_end:
                    header += f" (line {line_start})"
                else:
                    header += f" (lines {line_start}-{line_end})"

    # Add author information if available
    if author:
        header += f" • @{author}"

    return header


def format_comment_body(body, is_thread_reply=False, reply_author=None):
    """Format comment body with proper indentation and styling"""
    if is_thread_reply:
        prefix = "│ > "
        if reply_author:
            # Add author info to the first line of thread replies
            lines = body.split('\n')
            if lines:
                lines[0] = f"@{reply_author}: {lines[0]}"
                return '\n'.join(prefix + line if line.strip() else "│" for line in lines)
        return '\n'.join(prefix + line if line.strip() else "│" for line in body.split('\n'))
    else:
        prefix = "│ "
        return '\n'.join(prefix + line if line.strip() else "│" for line in body.split('\n'))


def format_comment_footer():
    """Format the footer for comment display"""
    return "└─"


def validate_pr(pr_number):
    """Validate that PR exists and is accessible"""
    if pr_number is None:
        # Try to detect PR from current branch
        detected_pr = get_pr_from_branch()
        if detected_pr:
            click.echo(f"Auto-detected PR #{detected_pr} from current branch")
            return detected_pr
        else:
            raise click.ClickException("No PR number provided and could not detect from current branch.")
    else:
        try:
            subprocess.check_output(['gh', 'pr', 'view', str(pr_number)], stderr=subprocess.DEVNULL)
        except:
            raise click.ClickException(f"PR #{pr_number} not found or accessible.")
    return pr_number


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Tool for viewing/editing/creating pull request comments and approving"""
    pass


@cli.command()
@click.option('-p', '--pr', type=int, help='The number of the pull request')
@click.option('-F', '--file', type=str, help='Path to a specific file (e.g., path/to/file.md)')
@click.option('-l', '--line', type=str, help='Line number or range (e.g., "5", "5-10", "5:10")')
def view(pr, file, line):
    """View comments on a pull request, file, or specific line(s)"""
    pr = validate_pr(pr)
    
    # load the org and repo for gh api calls
    api = GHApi()

    if file is None:
        # View pull request level comments
        if line is not None:
            raise click.ClickException("No file path provided but line number provided")

        # Get PR-level comments (these are issue comments, not review comments)
        try:
            pr_comments_raw = subprocess.check_output(['gh', 'api', f'/repos/{api.org}/{api.repo}/issues/{pr}/comments']).decode('utf-8').strip()
            pr_comments = json.loads(pr_comments_raw) if pr_comments_raw else []
        except:
            pr_comments = []

        # Display PR-level comments first
        comments_found = False

        if pr_comments:
            comments_found = True
            click.echo("═══ Pull Request Comments ═══")
            for i, comment in enumerate(pr_comments):
                if i > 0:
                    click.echo()  # Add blank line between comments
                author = comment.get('user', {}).get('login', 'unknown')
                click.echo(format_comment_header(author=author))
                click.echo(format_comment_body(comment['body']))
                click.echo(format_comment_footer())

        # Also get and display all file/line review comments
        try:
            pr_file_comments_raw = api.gh_api(f'pulls/{pr}/comments')
            all_file_comments = json.loads(pr_file_comments_raw) if pr_file_comments_raw else []
        except:
            all_file_comments = []

        if all_file_comments:
            if comments_found:
                click.echo("\n" + "═"*50)
            comments_found = True
            click.echo("═══ File & Line Comments ═══")

            # Group comments by file
            comments_by_file = {}
            for comment in all_file_comments:
                if 'in_reply_to_id' not in comment:  # Only top-level comments
                    file_path = comment.get('path', 'Unknown file')
                    if file_path not in comments_by_file:
                        comments_by_file[file_path] = []
                    comments_by_file[file_path].append(comment)

            # Display comments grouped by file
            for file_path, comments in sorted(comments_by_file.items()):
                click.echo(f"\n── {file_path} ──")

                for comment in comments:
                    click.echo()
                    line_num = comment.get('line')
                    start_line = comment.get('start_line')
                    author = comment.get('user', {}).get('login', 'unknown')

                    if start_line and line_num and start_line != line_num:
                        # Multi-line comment
                        click.echo(format_comment_header(file_path, start_line, line_num, author))
                    elif line_num:
                        # Single line comment
                        click.echo(format_comment_header(file_path, line_num, line_num, author))
                    else:
                        # File-level comment
                        click.echo(format_comment_header(file_path, author=author))

                    click.echo(format_comment_body(comment['body']))

                    # Show thread replies
                    thread_replies = [c for c in all_file_comments if 'in_reply_to_id' in c and c['in_reply_to_id'] == comment['id']]
                    for reply in thread_replies:
                        reply_author = reply.get('user', {}).get('login', 'unknown')
                        click.echo(format_comment_body(reply['body'], is_thread_reply=True, reply_author=reply_author))

                    click.echo(format_comment_footer())

        if not comments_found:
            click.echo("No comments found on this pull request")
        return

    # Handle file and line level review comments
    pr_file_comments = json.loads(api.gh_api(f'pulls/{pr}/comments'))
    pr_file_comments = [comment for comment in pr_file_comments if comment['path'] == file]

    # Parse line range if provided
    start_line = end_line = None
    if line is not None:
        try:
            start_line, end_line = parse_line_range(line)
        except ValueError:
            raise click.ClickException(f"Invalid line range format: {line}. Use formats like '5', '5-10', or '5:10'")

    if line is None:
        # View file level comments
        displayed_comments = []
        for comment in pr_file_comments:
            if 'in_reply_to_id' not in comment:
                displayed_comments.append(comment)

        for i, comment in enumerate(displayed_comments):
            if i > 0:
                click.echo()  # Add blank line between comments

            # Extract line information and author from the comment
            comment_line = comment.get('line')
            comment_start_line = comment.get('start_line')
            author = comment.get('user', {}).get('login', 'unknown')

            # Determine how to display line information
            if comment_start_line and comment_line and comment_start_line != comment_line:
                # Multi-line comment
                click.echo(format_comment_header(file, comment_start_line, comment_line, author))
            elif comment_line:
                # Single line comment
                click.echo(format_comment_header(file, comment_line, comment_line, author))
            else:
                # File-level comment (no specific line)
                click.echo(format_comment_header(file, author=author))

            click.echo(format_comment_body(comment['body']))

            comment_thread = [c for c in pr_file_comments if 'in_reply_to_id' in c and c['in_reply_to_id'] == comment['id']]
            for thread_comment in comment_thread:
                thread_author = thread_comment.get("user", {}).get("login", "unknown")
                click.echo(format_comment_body(thread_comment["body"], is_thread_reply=True, reply_author=thread_author))

            click.echo(format_comment_footer())

        if not displayed_comments:
            click.echo(f'No comments on file {file}')
        return

    # View line-specific comments
    # Filter comments by line range
    if start_line == end_line:
        # Single line comment
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and comment['line'] == start_line]
    else:
        # Multi-line comment - check if comment falls within range
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and start_line <= comment['line'] <= end_line]

    displayed_comments = []
    for comment in pr_file_and_line_comments:
        if 'in_reply_to_id' not in comment:
            displayed_comments.append(comment)

    for i, comment in enumerate(displayed_comments):
        if i > 0:
            click.echo()  # Add blank line between comments

        comment_line = comment.get('line', start_line)  # Fallback to start_line if 'line' not present
        author = comment.get('user', {}).get('login', 'unknown')
        click.echo(format_comment_header(file, comment_line, comment_line, author))
        click.echo(format_comment_body(comment['body']))

        comment_thread = [c for c in pr_file_comments if 'in_reply_to_id' in c and c['in_reply_to_id'] == comment['id']]
        for thread_comment in comment_thread:
            thread_author = thread_comment.get("user", {}).get("login", "unknown")
            click.echo(format_comment_body(thread_comment["body"], is_thread_reply=True, reply_author=thread_author))

        click.echo(format_comment_footer())

    if not displayed_comments:
        if start_line == end_line:
            click.echo(f'No comments on line {start_line} in file {file}')
        else:
            click.echo(f'No comments on lines {start_line}-{end_line} in file {file}')


@cli.command()
@click.option('-p', '--pr', type=int, help='The number of the pull request')
@click.option('-c', '--comment-text', type=str, help='Comment text (if not provided, opens editor)')
@click.option('-F', '--file', type=str, help='Path to a specific file (e.g., path/to/file.md)')
@click.option('-l', '--line', type=str, help='Line number or range (e.g., "5", "5-10", "5:10")')
def comment(pr, comment_text, file, line):
    """Add a comment to a pull request, file, or specific line(s)"""
    pr = validate_pr(pr)
    
    # load the org and repo for gh api calls
    api = GHApi()

    if file is None:
        # Pull request level comments
        if line is not None:
            raise click.ClickException("No file path provided but line number provided")

        # Get existing PR-level comments
        try:
            pr_comments_raw = subprocess.check_output(['gh', 'api', f'/repos/{api.org}/{api.repo}/issues/{pr}/comments']).decode('utf-8').strip()
            pr_comments = json.loads(pr_comments_raw) if pr_comments_raw else []
        except:
            pr_comments = []

        # Handle comment creation
        if comment_text:
            text = comment_text
        else:
            # Open editor for new comment
            click.echo("Opening editor for new comment...")
            text = open_editor()
            if text == '':
                click.echo("Empty comment, exiting...")
                return

        click.echo("Creating new PR comment...")
        subprocess.check_output(['gh', 'pr', 'comment', str(pr), '--body', text])
        click.echo("Comment added successfully!")
        return

    # Handle file and line level review comments
    pr_file_comments = json.loads(api.gh_api(f'pulls/{pr}/comments'))
    pr_file_comments = [comment for comment in pr_file_comments if comment['path'] == file]

    # Parse line range if provided
    start_line = end_line = None
    if line is not None:
        try:
            start_line, end_line = parse_line_range(line)
        except ValueError:
            raise click.ClickException(f"Invalid line range format: {line}. Use formats like '5', '5-10', or '5:10'")

    if line is None:
        # File level comments
        # Find latest comment for potential thread continuation
        latest_comment = None
        for comment in pr_file_comments:
            if 'in_reply_to_id' not in comment:
                latest_comment = comment

        # Handle comment creation for file-level
        if comment_text:
            text = comment_text
        else:
            # Open editor for new comment
            click.echo("Opening editor for new file comment...")
            text = open_editor()
            if text == '':
                click.echo("Empty comment, exiting...")
                return

        if latest_comment is not None:
            latest_comment_id = latest_comment.get('id', None)
            latest_comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]

            click.echo(latest_comment['body'])
            for thread_comment in latest_comment_thread:
                click.echo('>', thread_comment['body'])

            if click.confirm("Continue the existing thread?", default=True):
                api.gh_api(
                    f'pulls/{pr}/comments/{latest_comment["id"]}/replies',
                    'POST',
                    '-f', f"body={text}"
                )
                click.echo("Reply added successfully!")
                return

            if not click.confirm("Create new thread?", default=True):
                return

        head = json.loads(api.gh_api(f'pulls/{pr}'))['head']['sha']
        try:
            api.gh_api(
                f'pulls/{pr}/comments',
                'POST',
                '-f', f"body={text}",
                '-f', f"commit_id={head}",
                '-f', f"path={file}",
                '-f', "side=RIGHT",
                '-f', "subject_type=file",
            )
            click.echo("Comment added successfully!")
        except FileNotInPRError as e:
            click.echo(f"❌ Error: {e}", err=True)
        except ValidationError as e:
            click.echo(f"❌ {e}", err=True)
        except Exception as e:
            click.echo(f"❌ Failed to create comment: {e}", err=True)
        return

    # Handle line-specific comments
    # Filter comments by line range
    if start_line == end_line:
        # Single line comment
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and comment['line'] == start_line]
    else:
        # Multi-line comment - check if comment falls within range
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and start_line <= comment['line'] <= end_line]

    # Find latest comment for potential thread continuation
    latest_comment = None
    for comment in pr_file_and_line_comments:
        if 'in_reply_to_id' not in comment:
            latest_comment = comment

    # Handle comment creation for line-level
    if comment_text:
        text = comment_text
    else:
        # Open editor for new comment
        if start_line == end_line:
            click.echo(f"Opening editor for new comment on line {start_line}...")
        else:
            click.echo(f"Opening editor for new comment on lines {start_line}-{end_line}...")
        text = open_editor()
        if text == '':
            click.echo("Empty comment, exiting...")
            return

    if latest_comment is not None:
        latest_comment_id = latest_comment.get('id', None)
        latest_comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]

        click.echo(latest_comment['body'])
        for thread_comment in latest_comment_thread:
            click.echo('>', thread_comment['body'])

        if click.confirm("Continue the existing thread?", default=True):
            api.gh_api(
                f'pulls/{pr}/comments/{latest_comment["id"]}/replies',
                'POST',
                '-f', f"body={text}"
            )
            click.echo("Reply added successfully!")
            return

        if not click.confirm("Create new thread?", default=True):
            return

    head = json.loads(api.gh_api(f'pulls/{pr}'))['head']['sha']

    # Build API call parameters
    api_params = [
        f'pulls/{pr}/comments',
        'POST',
        '-f', f"body={text}",
        '-f', f"commit_id={head}",
        '-f', f"path={file}",
        '-F', f"line={end_line}",  # GitHub API uses the end line for multiline comments
        '-f', "side=RIGHT",
    ]

    # Add multiline support if needed
    if start_line != end_line:
        api_params.extend(['-F', f"start_line={start_line}", '-f', "start_side=RIGHT"])

    try:
        api.gh_api(*api_params)
        click.echo("Comment added successfully!")
    except FileNotInPRError as e:
        click.echo(f"❌ Error: {e}", err=True)
    except ValidationError as e:
        click.echo(f"❌ {e}", err=True)
    except Exception as e:
        click.echo(f"❌ Failed to create comment: {e}", err=True)


@cli.command()
@click.option('-p', '--pr', type=int, help='The number of the pull request')
@click.option('-F', '--file', type=str, help='Path to a specific file (e.g., path/to/file.md)')
@click.option('-l', '--line', type=str, help='Line number or range (e.g., "5", "5-10", "5:10")')
def edit(pr, file, line):
    """Edit an existing comment on a pull request, file, or specific line(s)"""
    pr = validate_pr(pr)
    
    # load the org and repo for gh api calls
    api = GHApi()

    if file is None:
        # Edit pull request level comment
        if line is not None:
            raise click.ClickException("No file path provided but line number provided")

        # Get PR-level comments
        try:
            pr_comments_raw = subprocess.check_output(['gh', 'api', f'/repos/{api.org}/{api.repo}/issues/{pr}/comments']).decode('utf-8').strip()
            pr_comments = json.loads(pr_comments_raw) if pr_comments_raw else []
        except:
            pr_comments = []

        if not pr_comments:
            raise click.ClickException('No comment to edit')

        latest_comment = pr_comments[-1]
        latest_comment_id = latest_comment.get('id', None)
        click.echo("Existing comment found for this pull request.")
        old_body = latest_comment.get('body', None)
        click.echo(old_body)

        # Open editor for editing the comment
        click.echo("Opening editor to edit comment...")
        new_body = open_editor(old_body)

        if new_body == '':
            raise click.ClickException("Empty comment")

        if old_body == new_body:
            click.echo("No changes made, exiting...")
            return

        # Update the comment using GitHub API
        try:
            subprocess.check_output(['gh', 'api', '--method', 'PATCH', f'/repos/{api.org}/{api.repo}/issues/comments/{latest_comment_id}', '-f', f'body={new_body}'])
            click.echo("Comment updated successfully!")
        except Exception as e:
            raise click.ClickException(f"Failed to update comment: {e}")
        return

    # Handle file and line level review comments
    pr_file_comments = json.loads(api.gh_api(f'pulls/{pr}/comments'))
    pr_file_comments = [comment for comment in pr_file_comments if comment['path'] == file]

    # Parse line range if provided
    start_line = end_line = None
    if line is not None:
        try:
            start_line, end_line = parse_line_range(line)
        except ValueError:
            raise click.ClickException(f"Invalid line range format: {line}. Use formats like '5', '5-10', or '5:10'")

    if line is None:
        # Edit file level comment
        # Find latest comment
        latest_comment = None
        for comment in pr_file_comments:
            if 'in_reply_to_id' not in comment:
                latest_comment = comment

        if latest_comment is None:
            raise click.ClickException('No comment to edit')

        # Edit the latest file-level comment
        click.echo("Opening editor to edit file comment...")
        old_body = latest_comment['body']
        new_body = open_editor(old_body)

        if new_body == '':
            raise click.ClickException("Empty comment")

        if old_body == new_body:
            click.echo("No changes made, exiting...")
            return

        # Update the comment
        api.gh_api(f'pulls/comments/{latest_comment["id"]}', 'PATCH', '-f', f"body={new_body}")
        click.echo("Comment updated successfully!")
        return

    # Edit line-specific comment
    # Filter comments by line range
    if start_line == end_line:
        # Single line comment
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and comment['line'] == start_line]
    else:
        # Multi-line comment - check if comment falls within range
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and start_line <= comment['line'] <= end_line]

    # Find latest comment
    latest_comment = None
    for comment in pr_file_and_line_comments:
        if 'in_reply_to_id' not in comment:
            latest_comment = comment

    if latest_comment is None:
        raise click.ClickException('No comment to edit')

    # Edit the latest line-specific comment
    click.echo("Opening editor to edit line comment...")
    old_body = latest_comment['body']
    new_body = open_editor(old_body)

    if new_body == '':
        raise click.ClickException("Empty comment")

    if old_body == new_body:
        click.echo("No changes made, exiting...")
        return

    # Update the comment
    api.gh_api(f'pulls/comments/{latest_comment["id"]}', 'PATCH', '-f', f"body={new_body}")
    click.echo("Comment updated successfully!")


@cli.command()
@click.option('-p', '--pr', type=int, help='The number of the pull request')
@click.option('-c', '--comment-text', type=str, help='Optional comment text to include with approval')
def approve(pr, comment_text):
    """Approve a pull request with an optional comment"""
    pr = validate_pr(pr)
    
    if comment_text is None:
        try:
            subprocess.check_output(['gh', 'pr', 'review', str(pr), '--approve'])
            click.echo(f"✓ PR #{pr} approved successfully!")
        except subprocess.CalledProcessError as e:
            raise click.ClickException(f"Failed to approve PR: {e}")
    else:
        try:
            subprocess.check_output(['gh', 'pr', 'review', str(pr), '--approve', '--body', comment_text])
            click.echo(f"✓ PR #{pr} approved successfully with comment!")
        except subprocess.CalledProcessError as e:
            raise click.ClickException(f"Failed to approve PR: {e}")


if __name__ == '__main__':
    cli()
