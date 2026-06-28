# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import subprocess

COMMAND = (
    "USERNAME=\"charles\"; HOMEDIR=\"/home/test1\"; PASSWORD=\"Ex@mpleP@55w0rd!\"; "
    "bash /app/.osworld/check_password.sh \"$USERNAME\" \"$PASSWORD\" "
    "&& [ \"$(getent passwd \"$USERNAME\" | cut -d: -f6)\" = \"$HOMEDIR\" ] "
    "&& [ $(stat -c \"%A\" \"$HOMEDIR\" | cut -b 3) = \"w\" ] "
    "&& echo \"Password, home directory, and write permission check passed\" "
    "|| echo \"Check failed\""
)
SUCCESS_TOKEN = "Password, home directory, and write permission check passed"
FAILURE_MESSAGE = (
    "User account state does not satisfy the original OSWorld shell check"
)


def test_main():
    completed = subprocess.run(
        COMMAND,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    assert SUCCESS_TOKEN in completed.stdout, (
        f"{FAILURE_MESSAGE}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
