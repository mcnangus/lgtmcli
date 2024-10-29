#!/usr/bin/env python3

import argparse
import json
import subprocess

GITHUB_HEADERS=['-H', "Accept: application/vnd.github+json", '-H', "X-GitHub-Api-Version: 2022-11-28"]

def gh_api(path: str, *args):
    return subprocess.check_output([
        'gh', 'api', *GITHUB_HEADERS,
        path,
        *args,
    ]).decode('utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description='Open a pull request for editing comments')
    parser.add_argument('--pr', type=int, help='The number of the pull request to open')
    parser.add_argument('--file', type=str, help='(optional) The file path to edit (e.g., path/to/file.md)')
    parser.add_argument('--line', type=str, help='(optional) The starting line that you wish to leave the comment on')
    parser.add_argument('--comment', type=str, help='Rich text comment')
    parser.add_argument('--view', default=False, help='View only mode', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    if args.pr == None:
        # TODO use branch to get any available prs
        raise Exception("Error: No pr number provided.")

    if args.view:
        if args.comment != None:
            raise Exception('Cannot set both view and comment.')
        print('Entered view only mode...')
    elif args.comment == None:
        raise Exception("Error: No comment provided.")

    # TODO load in bash script???
    remote=subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode('utf-8').strip()
    baseurl=subprocess.check_output(['dirname', remote]).decode('utf-8').strip()
    org=subprocess.check_output(['basename', baseurl]).decode('utf-8').strip()
    repo=subprocess.check_output(['basename', '-s', '.git', remote]).decode('utf-8').strip()
    head=subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()

    # pull request level comments (no threads)
    if args.file == None:
        if args.line != None:
            raise Exception("Error: No file path provided but line number provided.")

        # TODO handle selecting from existing pr level comments and then editing (stretch), fzf???
        pr_comments = json.loads(gh_api(f'/repos/{org}/{repo}/pulls/{args.pr}/comments'))

        pr_comments = [comment for comment in pr_comments if 'in_reply_to_id' not in comment]

        for comment in pr_comments:
            print(comment['body'])

        latest_comment=pr_comments[-1]
        latest_comment_id = latest_comment.get('id', None)

        if pr_comments:
            print("Existing comment found for this pull request.")
            old_body = latest_comment.get('body', None)
            print(old_body)
            if not args.view:
                if input("Do you wish to edit the existing comment? (Y/n): ") in ['Y', 'y']:
                    new_body = input("Press Enter when you're done editing... ")
                    if new_body == '':
                        raise Exception("Empty comment, exiting...")

                    if old_body == new_body:
                        raise Exception("No changes to comment, exiting...")

                    gh_api(
                        f'/repos/{org}/{repo}/pulls/comments/{latest_comment_id}',
                        '--method', 'PATCH',
                        '-f', f"body={new_body}",
                    )
                    return
            else:
                return

        if not args.view:
            print("No comments found for this pull request, using comment from input...")
            subprocess.check_output(['gh', 'pr', 'comment', str(args.pr), '--body', args.comment]).decode('utf-8').strip()
        return

    # TODO resolve file / file and line level comments???

    if args.line == None:
        # pull request file level comments
        pr_file_comments = json.loads(gh_api(f'/repos/{org}/{repo}/pulls/{args.pr}/comments'))

        pr_file_comments = [comment for comment in pr_file_comments if comment['path'] == args.file]

        latest_comment = None
        for comment in pr_file_comments:
            if 'in_reply_to_id' not in comment:
                latest_comment = comment

        if latest_comment == None:
            print('No comments on file', args.file)
        else:
            latest_comment_id = latest_comment.get('id', None)
            lastest_comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]

            print(latest_comment['body'])
            for thread_comment in lastest_comment_thread:
                print('>', thread_comment['body'])

            if args.view:
                return

            if input("Continue the existing thread? (Y/n): ") in ['Y', 'y']:
                gh_api(
                    f'/repos/{org}/{repo}/pulls/{args.pr}/comments/{latest_comment['id']}/replies',
                    '--method', 'POST',
                    '-f', f"body={args.comment}",
                )
                return

            if input("Create new thread? (Y/n): ") not in ['Y', 'y']:
                return

        if not args.view:
            gh_api(
                f'/repos/{org}/{repo}/pulls/{args.pr}/comments',
                '--method', 'POST',
                '-f', f"body={args.comment}",
                '-f', f"commit_id={head}",
                '-f', f"path={args.file}",
                '-f', "side=RIGHT",
                '-f', "subject_type=file",
            )
        return

        # TODO edit existing comment

    # TODO multiline, eg. --multiline 5-12 OR --multiline 5:12
    # '-F', "start_line=1", '-f', "start_side=RIGHT"

    else:
        # pull request file AND line level comments
        if not args.view:
            gh_api(
                f'/repos/{org}/{repo}/pulls/{args.pr}/comments',
                '--method', 'POST',
                '-f', f"body={args.comment}",
                '-f', f"commit_id={head}",
                '-f', f"path={args.file}",
                '-F', f"line={args.line}",
                '-f', "side=RIGHT",
            )
        return
        # TODO handle editing existing file/line combo level comments (stretch)
        # TODO handle replying to thread of file/line combo level comments


    # TODO interactive editor for commenting

    # TODO review changes
    # Wait for the user to save and exit the

    # TODO handle response, eg. success, error, etc.

if __name__ == '__main__':
    main()
