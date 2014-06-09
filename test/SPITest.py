import unittest
import logging
import numpy as np
from datetime import datetime
from struct import unpack

from SPI import SPI

class SPITest(unittest.TestCase):
    'Unit tests for SPI.'

    def test_inc_mmcm_phase(self):
    
        spi = SPI(zdok = 0, test = True)
        spi.inc_mmcm_phase()
        self.assertEquals([(196608,)], spi.get_int_roach_writes())

    def test_set_test_mode(self):

        spi = SPI(zdok = 0, test = True)

        self.assertEqual(spi.regs, [])

        spi.set_test_mode()

        expRegs = [('0x85', '0x0'), ('0x81', '0x13c8')]
        self.assertEqual(expRegs, spi.get_hex_regs())

        # writes: [(4, '\x00\x00\x85\x01'), (4, '\x13\xc8\x81\x01')]
        writes = spi.get_int_roach_writes() #[unpack(">I", data) for offset, data in spi.writes]
        expWrites = [(34049,), (331907329,)]
        self.assertEqual(expWrites, writes)

    def test_set_control(self):

        spi = SPI(zdok = 0, test = True)

        self.assertEqual(spi.regs, [])

        spi.set_control()

        self.assertEqual(len(spi.regs), 1)

        #regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]
        exp = [('0x81', '0x3c8')]

        self.assertEqual(exp, spi.get_hex_regs())


        # writes: [(4, '\x03\xc8\x81\x01')]
        writes = [unpack(">I", data) for offset, data in spi.writes]
        expWrites = [(63471873,)] # 
        self.assertEqual(expWrites, writes)

    def test_set_offset(self):

      
        spi = SPI(zdok = 0, test = True)
        self.assertEqual(spi.regs, [])

        offsets = [-2.535, -5.0077, -6.7831, -2.5544]

        spi.set_offsets(offsets)

        self.assertEqual(len(spi.regs), 12)
        regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]
        exp = [('0x8f', '0x1')
             , ('0xa0', '0x7a')
             , ('0x90', '0x8')
             , ('0x8f', '0x2')
             , ('0xa0', '0x73')
             , ('0x90', '0x8')
             , ('0x8f', '0x3')
             , ('0xa0', '0x6f')
             , ('0x90', '0x8')
             , ('0x8f', '0x4')
             , ('0xa0', '0x79')
             , ('0x90', '0x8')
             ]

        self.assertEqual(exp, regs)

    def test_set_gains(self):

        spi = SPI(zdok = 0, test = True)
        self.assertEqual(spi.regs, [])

        values =  [-2.6737, 0.5534, 0.5995, 1.5208]

        spi.set_gains(values)

        self.assertEqual(len(spi.regs), 12)
        regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]

        exp = [('0x8f', '0x1'), ('0xa2', '0x6d'), ('0x90', '0x20'), ('0x8f', '0x2'), ('0xa2', '0x84'), ('0x90', '0x20'), ('0x8f', '0x3'), ('0xa2', '0x84'), ('0x90', '0x20'), ('0x8f', '0x4'), ('0xa2', '0x8b'), ('0x90', '0x20')]
        self.assertEqual(exp, regs)

    def test_set_phases(self):

        spi = SPI(zdok = 0, test = True)
        self.assertEqual(spi.regs, [])

        values = [-5.8921, -6.4829, 5.9341, 6.4409]

        spi.set_phases(values)

        self.assertEqual(len(spi.regs), 12)
        regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]

        exp = [('0x8f', '0x1'), ('0xa4', '0x4a'), ('0x90', '0x80'), ('0x8f', '0x2'), ('0xa4', '0x45'), ('0x90', '0x80'), ('0x8f', '0x3'), ('0xa4', '0xb6'), ('0x90', '0x80'), ('0x8f', '0x4'), ('0xa4', '0xbb'), ('0x90', '0x80')]
        self.assertEqual(exp, regs)

    def test_set_inl_registers(self):

        spi = SPI(zdok = 0, test = True)
        self.assertEqual(spi.regs, [])
        values = [ 0., -0.0049, -0.158,  -0.0952,  0.0614,  0.0008, -0.0537,  0.161,   0.1902, 0.5033,  0.327,   0.2102,  0.1048, -0.0875, -0.2342, -0.0445,  0.    ]

        spi.set_inl_registers(1, values)
        self.assertEqual(len(spi.regs), 8)
        regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]

        exp = [('0x8f', '0x1'), ('0xb0', '0x20'), ('0xb1', '0x1400'), ('0xb2', '0x0'), ('0xb3', '0x19'), ('0xb4', '0x6140'), ('0xb5', '0xa000'), ('0x90', '0x2')]
        
        self.assertEqual(exp, regs)

        # reset and test again
        spi.regs = []
        values = [ 0.,      0.0105,  0.0668, -0.0788, -0.233,  -0.0821,  0.0365,  0.0753,  0.1046, -0.0899, -0.0987,  0.2009,  0.1752,  0.2263, -0.0184, -0.0449,  0.    ]

        spi.set_inl_registers(2, values)
        self.assertEqual(len(spi.regs), 8)
        regs = [(hex(int(x)), hex(int(y))) for x, y in spi.regs]

        exp = [('0x8f', '0x2'), ('0xb0', '0x4'), ('0xb1', '0x2'), ('0xb2', '0x0'), ('0xb3', '0x9'), ('0xb4', '0x6949'), ('0xb5', '0x8000'), ('0x90', '0x2')]
        
        self.assertEqual(exp, regs)


    def test_get_inl_registers(self):

        spi = SPI(zdok = 0, test = True)
        self.assertEqual(spi.regs, [])

        offs = spi.get_inl_registers(1)
        #print offs
        exp = [0.0]*17 
        self.assertEqual(exp, list(offs))

    def test_get_control(self):

        spi = SPI(zdok = 0, test = True)

        # in test mode, controls are hardwired to this
        exp = {'fs': 0, 'adcmode': 8, 'bdw': 3, 'bg': 1, 'test': 0, 'stdby': 0, 'dmux': 1}
        controls = spi.get_control()
        self.assertEqual(exp, controls)

