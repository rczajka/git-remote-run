"""Defines the Remote class for running commands on a git remote."""
from getpass import getpass
from io import BytesIO
from shlex import quote
import subprocess
import tarfile


class Remote:
    """Allows running arbitrary bash scripts on a git remote."""

    def __init__(self, name):
        self.name = name

    def run(self, script):
        """
        Runs a (bash) script on the remote by (ab)using git-archive.

        The `git archive` command allows downloading a git repository
        archive from a remote, and does it by running a separate program
        on the remote machine: `git-upload-archive`. There is an option
        for pointing to a custom location of this program, which we
        can use to run basically anything we want.

        The original `git-upload-archive` takes one argument, which is
        the path to the repository for which the archive is created. We
        use that by saving our custom script to a temporary file which
        reads the repository location from the argument and stores it
        in $REPO_DIR env var.

        There's a custom protocol between `git-archive` and
        `git-upload-archive`, so we can run any script, but any output
        which isn't conformant with the protocol will cause an error
        in `git-archive` and be lost. But since we still want to
        transmit the exit code, stdout and stderr from our script back
        to the user, we do that by complying with the protocol. To that
        end, we create a tiny temporary git repository, in which we
        store the values we want to transmit, and call the original
        `git-upload-archive` on that temporary repository. This sends
        back a valid tar archive, which we can just receive and unpack
        to recover all the return values.
        """
        # First, compose a command which will serve as a replacement
        # for git-upload-archive.
        # This command saves
        archive_exec = '''
            export VDEPLOY_SCRIPT="`mktemp --tmpdir git-remote-run-XXX.sh`"
            cat > "$VDEPLOY_SCRIPT" << 'EOF'
export REPO_DIR="$1"

cwd="`pwd`"

# Create a temp repository for storing output from
# the custom script.
tempdir="`mktemp  --tmpdir -d git-remote-run-XXX`"
git init "$tempdir" > /dev/null

# Run the custom script.
(
    {}
) > "$tempdir"/stdout 2> "$tempdir"/stderr
echo -n "$?" > "$tempdir"/exitcode

# Create a git archive from the temp repository
# and send it back to the user.
cd "$tempdir"
git add .
git commit -m init > /dev/null
git-upload-archive .

# Clean up.
rm -rf "$tempdir"
rm $VDEPLOY_SCRIPT
EOF
            bash $VDEPLOY_SCRIPT'''.format(script)

        result = subprocess.run(
            [
                'git', 'archive', '--remote', self.name, 'HEAD',
                '--exec', archive_exec
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        assert result.returncode == 0, result.stderr.decode('utf-8')
        assert result.stderr == b''

        inner_result = {
            'cmd': script,
        }
        # Read the script output from the received archive.
        with tarfile.open(fileobj=BytesIO(result.stdout)) as tar:
            for name in tar.getnames():
                value = tar.extractfile(name).read()
                if name == 'exitcode':
                    value = int(value)
                inner_result[name] = value

        return inner_result

    def sudo(self, script, shell=True, user=None):
        """
        Runs a script with sudo.

        Sudo may or may not require a password. If it does, we want to
        know it. We could use `sudo -n`, but then we'd need to
        differentiate `sudo` failing because of missing password from
        the actual script failing with the same exit code.

        So we use `sudo --askpass` instead, in a slightly hackish way,
        to make sure we need sudo password. The --askpass option causes
        the program specified by $SUDO_ASKPASS to be called, with
        a password prompt as only argument. So we set SUDO_ASKPASS and
        SUDO_PROMPT to set a flag signaling the need for password.
        """
        if shell:
            script = "bash -c {}".format(quote(script))
        if user:
            script = "-u {} {}".format(user, script)

        # Attempt sudo without a password.
        invocation = \
            'SUDO_PROMPT="$tempdir/sudo-needs-password" ' \
            'SUDO_ASKPASS="/usr/bin/touch" ' \
            'sudo --preserve-env --askpass ' + script

        result = self.run(invocation)
        if 'sudo-needs-password' in result:
            # Ask the local user for the remote password.
            password = getpass(
                'Enter your password for running `sudo {}` on {}:'
                .format(script, self.name))
            invocation = 'echo {} | sudo --preserve-env --stdin {}' \
                .format(quote(password), script)
            result = self.run(invocation)
        return result

    def run_or_sudo(self, script, shell=True):
        """
        Try to run the script as the default user first,
        and only add sudo if it fails.
        """
        result = self.run(script)
        if result['exitcode']:
            result = self.sudo(script, shell=shell)
        return result
