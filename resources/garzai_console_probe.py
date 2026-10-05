"""Gz Console Probe -- how much output does the CRT Test Agent actually see, and on which channel?

The Test Agent reads CONSOLE output only (`logger.console()`, `Log ... console=True`), never a
plain `Log` message (2026-10-05 probe). This keyword prints a numbered, checksummed block of a
chosen size so a person can ask the agent "what is the LAST line you can read?" and know exactly
where any cut happened -- the question behind `Gz Read Page`'s page size (W2.14).

    channel=console   print the block to the console; return only the END marker
    channel=return    print nothing; return the whole block (the agent must surface it)
    channel=both      both

Import in a live session (the job root is /home/services/suite):
    Import Library    /home/services/suite/resources/garzai_console_probe.py
    Gz Console Probe    8    channel=console
"""
import hashlib

from robot.api import logger
from robot.api.deco import keyword

_LINE = 100


@keyword("Gz Console Probe")
def gz_console_probe(size_kb="2", channel="console"):
    total = max(_LINE, int(float(size_kb) * 1024))
    n = max(1, total // _LINE)
    lines = []
    for i in range(1, n + 1):
        head = "GZPROBE %05d/%05d " % (i, n)
        lines.append(head + ("<%05d>" % i * 20)[: _LINE - len(head) - 1])
    block = "\n".join(lines)
    sha = hashlib.sha256(block.encode()).hexdigest()[:12]
    start = "GZPROBE START size_kb=%s lines=%d bytes=%d sha=%s" % (size_kb, n, len(block), sha)
    end = "GZPROBE END lines=%d bytes=%d sha=%s -- if you can read this line, nothing was cut" % (n, len(block), sha)
    full = "\n".join([start, block, end])
    if channel in ("console", "both"):
        logger.console(full)
    return full if channel in ("return", "both") else end
