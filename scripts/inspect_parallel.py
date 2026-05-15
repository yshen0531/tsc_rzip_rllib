#!/usr/bin/env python3
from __future__ import annotations

import subprocess

cmd = """
ps -eLo pid,ppid,tid,psr,pcpu,stat,comm,args \
  | grep -E 'gotsc|ray::|train_rllib_sac.py|python' \
  | grep -v grep \
  | head -200
""".strip()
print(cmd)
print("=" * 120)
subprocess.run(cmd, shell=True, check=False)
