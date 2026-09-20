"""garzai_data_tally -- the Robot library listener that TALLIES every FakerLibrary value a pane
generates, with no extra pane line (build n10, 2026-09-20: FakerLibrary generates; the run stamp
left the value).

WHY A LISTENER. The composed line is FakerLibrary's own keyword --
`${lead_first_name}=    FakerLibrary.First Name` -- exactly as the user asked; nothing of ours runs
on that line, so nothing of ours could log it. A Robot LIBRARY LISTENER sees every keyword end
(`end_keyword`, listener API v3) and, when the keyword belongs to FakerLibrary and assigned a
variable, reads that variable back and keeps it. Measured under Robot 7.3.2 (2026-09-20): the
assignment is visible in `end_keyword` (`${a}` -> 'Denise' read back, `Random Int` -> 28).

`Gz Generated Tally` in garzai_data.robot prints this list at the end of a run -- the traceability
that used to be the run stamp inside every value. `Gz Pick` reports through `Gz Note Generated`
so the tally is ONE list. `print()` is invisible in CRT Live Testing (CLAUDE.md), so every line
goes through Robot's console logger.

`tools/recorder/crt_override/gz_data_py.py` is the walk's Python twin (no Robot there): it logs
and tallies the same way from its own FakerLibrary shim.
"""
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

FAKER_LIB = 'FakerLibrary'


class garzai_data_tally:
    ROBOT_LISTENER_API_VERSION = 3
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self
        self._generated = []

    # ------------------------------------------------------------------ the listener half
    def end_keyword(self, data, result):
        if getattr(result, 'owner', None) != FAKER_LIB or result.status != 'PASS':
            return
        assign = list(getattr(result, 'assign', None) or [])
        if not assign:
            return
        for name in assign:
            var = name.rstrip('=').strip()
            value = BuiltIn().get_variable_value(var, None)
            self._note('%s.%s' % (FAKER_LIB, result.name), value, var)

    # ------------------------------------------------------------------ the keyword half
    def _note(self, keyword, value, var=None):
        where = ' (%s)' % var if var else ''
        logger.console("GarzAI data: %s -> '%s'%s" % (keyword, value, where))
        self._generated.append('%s -> %s%s' % (keyword, value, where))

    def gz_note_generated(self, keyword, value):
        """One tally entry for a value a `Gz` keyword generated (Gz Pick)."""
        self._note(keyword, value)
        return value

    def gz_generated_values(self):
        """Every generated value of this run so far, in order, as `<keyword> -> <value>`."""
        return list(self._generated)
