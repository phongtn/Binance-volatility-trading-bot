import sys
from time_util import now_str


# for colorful logging to the console
class TxColors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'


class StampedStdout:
    """Stamped stdout."""
    nl = True

    def __init__(self, old_out: sys.stdout):
        self.old_out = old_out

    def write(self, x):
        """Write function overloaded."""
        if x == '\n':
            self.old_out.write(x)
            self.nl = True
        elif self.nl:
            self.old_out.write(
                f'{TxColors.DIM}[{now_str()}]{TxColors.DEFAULT} {x}')
            self.nl = False
        else:
            self.old_out.write(x)

    def flush(self):
        pass