import unittest
import logging
import os

from ADCConfFile import ADCConfFile

class ADCConfFileTest(unittest.TestCase):
    'Unit tests for .'

    def test_it(self):

        filename = 'testdata/noroach-adc.conf'
        cf = ADCConfFile(filename)

        bof = 'l8_ver139_2013_Dec_10_1334.bof'
        freq = 1500.0
        mmcms = cf.get_mmcms(bof, freq, 0)
        self.assertEquals([36], cf.get_mmcms(bof, freq, 0))
        self.assertEquals([29], cf.get_mmcms(bof, freq, 1))

        # ogps for zdok 0
        # '-0.3248,1.5234,-5.0277,4.9311,-1.3008,-4.5269,-0.8399,0.6527,4.0876,3.3885,-0.8754,5.4670'
        exp = [-0.3248, 4.9311, -0.8399, 3.3885]
        self.assertEquals(exp, cf.get_ogp_offsets(freq, 0))
        exp = [1.5234, -1.3008,  0.6527 ,-0.8754]
        self.assertEquals(exp, cf.get_ogp_gains(freq, 0))
        exp = [-5.0277, -4.5269, 4.0876, 5.4670]
        self.assertEquals(exp, cf.get_ogp_phases(freq, 0))

        exp = [[0.00000,-0.10133,-0.14213,-0.13309,-0.03288,-0.02201,0.04785,0.28533,0.23144,0.12245,0.00175,-0.14393,0.06759,0.01717,0.02305,0.04417,0.00000], [0.00000,-0.00089,-0.00880,-0.01382,0.05243,-0.00788,-0.08378,0.02892,0.04425,0.02460,0.04414,0.12746,0.25657,0.30780,-0.08435,0.01697,0.00000], [0.00000,-0.05272,-0.08472,0.03173,-0.27413,-0.27375,0.18520,0.20227,0.17200,0.38427,0.20219,-0.12959,-0.19174,0.05980,-0.01479,-0.00667,0.00000], [0.00000,-0.03374,-0.08598,0.10827,0.18885,0.20594,0.08379,0.10898,0.18270,0.12119,0.35429,0.20462,-0.04045,-0.08208,-0.10600,0.00753,0.00000]]

        self.assertEquals(exp, cf.get_inls(0))
