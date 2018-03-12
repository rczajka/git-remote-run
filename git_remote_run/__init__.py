"""Defines the command-line interface of the git-remote-run command."""
import argparse
from base64 import b64encode
from shlex import quote
import os
import sys
from git_remote_run.remote import Remote


__version__ = '1.1'


def upload_command(source_path, target_path):
    """Create a command to upload a file."""
    with open(source_path, 'rb') as f:
        content = f.read()
    command = '''echo {} | base64 --decode > {}'''.format(
        b64encode(content).decode('latin1'),
        target_path
    )
    return command


class UploadAction(argparse._AppendAction):
    """Helper class for the --upload option."""
    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(
            argparse._ensure_value(namespace, self.dest, []))
        items.append(upload_command(*values))
        setattr(namespace, self.dest, items)


def run():
    """git-remote-run command starts here."""
    parser = argparse.ArgumentParser(
        description='Run commands on a git remote.')

    action_args = parser.add_argument_group(
        title='Actions',
        description='Specify actions to perform on each of the git remotes.'
    )

    action_args.add_argument(
        '-c', '--command',
        action='append',
        dest='actions',
        metavar='COMMAND',
        help='Specify a command to run.'
    )
    action_args.add_argument(
        '-f', '--file',
        action='append',
        dest='actions',
        type=lambda script_path: open(script_path).read(),
        metavar='SCRIPT_PATH',
        help='Run commands from the given file.'
    )
    action_args.add_argument(
        '-u', '--upload',
        action=UploadAction,
        dest='actions',
        nargs=2,
        metavar=('LOCAL_PATH', 'REMOTE_PATH'),
        help='Upload a file to a given destination.'
    )

    sudo_args = parser.add_argument_group(
        title="Sudo",
    )
    sudo = sudo_args.add_mutually_exclusive_group()

    sudo.add_argument(
        '-S', '--sudo',
        action='store_true',
        default=False,
        help="Run the commands with sudo.",
    )
    sudo.add_argument(
        '-I', '--sudo-if-needed',
        action='store_true',
        default=False,
        help='Try to run the commands normally, and if they fail, '
             'try again with sudo.'
    )

    sudo_args.add_argument(
        '-U', '--sudo-user',
        dest='sudo_user',
        metavar='USER',
        help='Run commands as this user.'
    )

    sudo_args.add_argument(
        '-N', '--no-sudo-shell',
        action='store_false',
        default=True,
        dest='sudo_shell',
        help='Normally sudo commands are run in a subshell. You can '
             'disable it to comply with your sudoers configuration.'
    )

    parser.add_argument(
        'remote',
        type=Remote,
        help='Specifies git remote to use.'
    )

    args = parser.parse_args()

    if not args.sudo and not args.sudo_if_needed:
        if not args.sudo_shell:
            parser.error('--no-sudo-shell only makes sense with '
                         '--sudo or --sudo-if-needed.')
            return -1
        if args.sudo_user:
            parser.error('--sudo-user only makes sense with '
                         '--sudo or --sudo-if-needed.')
            return 1

    if not args.actions:
        parser.error('Some action is required: --command, --file, --upload.')
        return 1

    cmd = "\n\n".join(args.actions)
    if args.sudo:
        result = args.remote.sudo(
            cmd, shell=args.sudo_shell, user=args.sudo_user)
    elif args.sudo_if_needed:
        result = args.remote.sudo_if_needed(
            cmd, shell=args.sudo_shell, user=args.sudo_user)
    else:
        result = args.remote.run(cmd)

    if result['stderr']:
        sys.stderr.buffer.write(result['stderr'])
    if result['stdout']:
        sys.stdout.buffer.write(result['stdout'])
    return result['exitcode']


def setup():
    """git-remote-setup command starts here."""
    parser = argparse.ArgumentParser(
        description='Set up bare repo on a git remote.'
    )

    parser.add_argument(
        '-H', '--hooks',
        metavar='PATH',
        help='Specify directory with hooks to install.'
    )

    parser.add_argument(
        'remote',
        type=Remote,
        help='Specifies git remote to use.'
    )

    args = parser.parse_args()

    # Find first directory which needs to be created.
    result = args.remote.run("""
        [ -d "$REPO_DIR" ] || (
            cur="`realpath -m "$REPO_DIR"`"
            par="`dirname "$cur"`"
            while [ ! -d "$par" ]; do
                cur="$par"
                par="`dirname "$cur"`"
            done
            echo "$cur"
            echo "`whoami`:`id -gn`"
        )""")
    if result['stdout']:
        first_dir, usergroup = result['stdout'].decode('utf-8').strip().rsplit('\n', 2)
        args.remote.run_or_sudo('mkdir {d}; chown {u} {d}'.format(
            d=first_dir, u=usergroup))
    cmd = ["""
        mkdir -p "$REPO_DIR"
        git init --bare "$REPO_DIR"
    """]
    if args.hooks:
        for hook_name in os.listdir(args.hooks):
            remote_path = '"$REPO_DIR"/hooks/' + quote(hook_name)
            cmd.append(upload_command(
                os.path.join(args.hooks, hook_name),
                remote_path))
            cmd.append("chmod " + remote_path)
    cmd = "\n\n".join(cmd)
    args.remote.run(cmd)


if __name__ == '__main__':
    run()
