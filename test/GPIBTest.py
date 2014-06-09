import unittest

from GPIB import GPIB

class GPIBTest(unittest.TestCase):

    def test(self):

        gpib = GPIB("", test = True, freq = 10.0, ampl = 1.0)
        gpib.clean_up()
        exp = [':FREQ:CW 10.0E6\r', ':POW:LEV 1.0 DBM\r', ':OUTP:STAT ON\r', ':OUTP:STAT OFF\r']
        self.assertEquals(exp, gpib.cmds)
