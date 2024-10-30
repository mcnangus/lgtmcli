#!/usr/bin/env python3

import argparse
import json
import subprocess


class GHApi:
    headers=['-H', "Accept: application/vnd.github+json", '-H', "X-GitHub-Api-Version: 2022-11-28"]

    def __init__(self):
        # TODO load in bash script???
        remote=subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode('utf-8').strip()
        if 'git@github.com' in remote:
            parts=remote.split(':')[1].split('/')
            self.org=parts[0]
            self.repo=parts[1].split('.')[0]
        elif 'https://github.com' in remote:
            parts=remote.split('/')
            self.org=parts[3]
            self.repo=parts[4].split('.')[0]
        else:
            raise Exception('Cannot parse `git config --get remote.origin.url`')

    def gh_api(self, path: str, method='GET', *args):
        return subprocess.check_output([
            'gh', 'api',
            '--method', method,
            *self.headers,
            f'/repos/{self.org}/{self.repo}/'+path,
            *args,
        ]).decode('utf-8').strip()


def main():
    # parse the arguments
    parser = argparse.ArgumentParser(description='Tool for viewing/editing/creating pull request comments and approving')
    parser.add_argument('-p', '--pr', type=int, help='The number of the pull request to open')
    parser.add_argument('-F', '--file', type=str, help='(optional) The path to a specific file for action (e.g., path/to/file.md)')
    parser.add_argument('-l', '--line', type=str, help='(optional) Starting line of file for action')

    # TODO convert these flags into operations???
    parser.add_argument('-c', '--comment', type=str, help='Action: Rich text comment')
    parser.add_argument('-v', '--view', default=False, help='Action: View only mode', action=argparse.BooleanOptionalAction)
    parser.add_argument('-e', '--edit', default=False, help='Action: Edit mode', action=argparse.BooleanOptionalAction)
    parser.add_argument('-a', '--approve', default=False, help='Action: Approve mode', action=argparse.BooleanOptionalAction)

    args = parser.parse_args()


    # make sure pr is set
    if args.pr == None:
        # TODO use branch to get any available prs
        raise Exception("Error: No pr number provided.")
    else:
        try:
            subprocess.check_output(['gh', 'pr', 'view', str(args.pr)])
        except:
            return


    # ensure one of view, edit, approve, approve and comment, or comment is set
    if args.view:
        if args.comment != None:
            raise Exception('Cannot set both view and comment.')
        if args.edit:
            raise Exception('Cannot set both view and edit modes.')
        if args.approve:
            raise Exception('Cannot set both view and approve modes.')
        print('Entered view only mode...')
    elif args.edit:
        if args.comment != None:
            raise Exception('Cannot set both edit and comment.')
        if args.approve:
            raise Exception('Cannot set both edit and approve modes.')
        print('Entered edit mode...')
    elif args.approve:
        if args.comment == None:
            try:
                subprocess.check_output(['gh', 'pr', 'review', str(args.pr), '--approve'])
            except:
                return
        else:
            try:
                subprocess.check_output(['gh', 'pr', 'review', str(args.pr), '--approve', '--body', args.comment])
            except:
                return
        return
    elif args.comment == None:
        raise Exception("Error: No mode (view/edit/approve/comment) provided.")


    # load the org and repo for gh api calls
    api = GHApi()


    if args.file == None:
        # pull request level comments (no threads here)
        if args.line != None:
            raise Exception("No file path provided but line number provided, exiting...")

        # TODO handle selecting from existing pr level comments and then editing (stretch), fzf???
        pr_comments = json.loads(api.gh_api(f'pulls/{args.pr}/comments'))

        # TODO filter out non-pr level comments, eg. comments on a specific file
        pr_comments = [comment for comment in pr_comments if 'in_reply_to_id' not in comment]

        if args.view:
            for comment in pr_comments:
                print(comment['body'])
            return

        if pr_comments:
            latest_comment=pr_comments[-1]
            latest_comment_id = latest_comment.get('id', None)
            print("Existing comment found for this pull request.")
            old_body = latest_comment.get('body', None)
            print(old_body)

            if args.edit:
                # TODO make this editable using vim, nano, or other
                new_body = input("Press Enter when you're done editing... ")
                if new_body == '':
                    raise Exception("Empty comment, exiting...")

                if old_body == new_body:
                    raise Exception("No changes, exiting...")

                api.gh_api(f'pulls/comments/{latest_comment_id}', 'PATCH', '-f', f"body={new_body}")
                return
        else:
            if args.edit:
                raise Exception('No comment to edit, exiting...')

        print("Using comment from input...")
        subprocess.check_output(['gh', 'pr', 'comment', str(args.pr), '--body', args.comment]).decode('utf-8').strip()
        return


    # TODO resolve file / file and line level review comments???


    pr_file_comments = json.loads(api.gh_api(f'pulls/{args.pr}/comments'))
    pr_file_comments = [comment for comment in pr_file_comments if comment['path'] == args.file]
    if args.line == None:
        # pull request file level comments
        latest_comment = None
        for comment in pr_file_comments:
            if 'in_reply_to_id' not in comment:
                latest_comment = comment
                if args.view:
                    print(comment['body'])
                    comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]
                    for thread_comment in comment_thread:
                        print('>', thread_comment['body'])


        if args.view:
            if latest_comment == None:
                print('No comments on file', args.file)
            return

        if args.edit:
            # TODO implement edit
            raise Exception('Not implemented yet, exiting.')

        if latest_comment != None:
            latest_comment_id = latest_comment.get('id', None)
            lastest_comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]

            print(latest_comment['body'])
            for thread_comment in lastest_comment_thread:
                print('>', thread_comment['body'])

            if input("Continue the existing thread? (Y/n): ") in ['Y', 'y']:
                api.gh_api(
                    f'pulls/{args.pr}/comments/{latest_comment['id']}/replies',
                    'POST',
                    '-f' f"body={args.comment}"
                )
                return

            if input("Create new thread? (Y/n): ") not in ['Y', 'y']:
                return

        head=json.loads(api.gh_api(f'pulls/{args.pr}'))['head']['sha']
        api.gh_api(
            f'pulls/{args.pr}/comments',
            'POST',
            '-f', f"body={args.comment}",
            '-f', f"commit_id={head}",
            '-f', f"path={args.file}",
            '-f', "side=RIGHT",
            '-f', "subject_type=file",
        )
        return
    else:
        # TODO multiline, eg. --multiline 5-12 OR --multiline 5:12
            # '-F', "start_line=1", '-f', "start_side=RIGHT"
        # pull request file AND line level comments
        pr_file_and_line_comments = [comment for comment in pr_file_comments if 'line' in comment and str(comment['line']) == args.line]

        latest_comment = None
        for comment in pr_file_and_line_comments:
            if 'in_reply_to_id' not in comment:
                latest_comment = comment
                if args.view:
                    print(comment['body'])
                    comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]
                    for thread_comment in comment_thread:
                        print('>', thread_comment['body'])

        if args.view:
            if latest_comment == None:
                print('No comments on line', args.line, 'in file', args.file)
            return

        if args.edit:
            # TODO implement edit
            raise Exception('Not implemented yet, exiting.')

        if latest_comment != None:
            latest_comment_id = latest_comment.get('id', None)
            lastest_comment_thread = [comment for comment in pr_file_comments if 'in_reply_to_id' in comment and comment['in_reply_to_id'] == latest_comment['id']]

            print(latest_comment['body'])
            for thread_comment in lastest_comment_thread:
                print('>', thread_comment['body'])

            if input("Continue the existing thread? (Y/n): ") in ['Y', 'y']:
                api.gh_api(
                    f'pulls/{args.pr}/comments/{latest_comment['id']}/replies',
                    'POST',
                    '-f' f"body={args.comment}"
                )
                return

            if input("Create new thread? (Y/n): ") not in ['Y', 'y']:
                return

        head=json.loads(api.gh_api(f'pulls/{args.pr}'))['head']['sha']
        api.gh_api(
            f'pulls/{args.pr}/comments',
            'POST',
            '-f', f"body={args.comment}",
            '-f', f"commit_id={head}",
            '-f', f"path={args.file}",
            '-F', f"line={args.line}",
            '-f', "side=RIGHT",
        )
        return


    # TODO interactive editor for commenting

    # TODO review changes
        # Wait for the user to save and exit the

    # TODO handle response, eg. success, error, etc.

if __name__ == '__main__':
    main()
