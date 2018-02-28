"""Defines the command-line interface of the git-remote-run command."""
import argparse
from base64 import b64encode
import sys
from git_remote_run.remote import Remote


__version__ = '1.0'


class UploadAction(argparse._AppendAction):
    """Helper class for the --upload option."""
    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(
            argparse._ensure_value(namespace, self.dest, []))

        source_path, target_path = values
        with open(source_path, 'rb') as f:
            content = f.read()
        command = '''echo {} | base64 --decode > {}'''.format(
            b64encode(content).decode('latin1'),
            target_path
        )

        items.append(command)
        setattr(namespace, self.dest, items)


def run():
    """The actual command starts here."""
    parser = argparse.ArgumentParser()

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


if __name__ == '__main__':
    run()
