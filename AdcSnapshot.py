from struct import pack, unpack
import numpy as np
from numpy.fft import fft

class AdcSnapshot:

    def __init__(self, roach = None, zdok = None, test = False, clockrate = None):

        self.test = test
        self.zdok = zdok
        self.roach = roach
        
        self.clockrate = clockrate 

    def set_zdok(self, zdok):
        self.zdok = zdok

    def set_clockrate(self, clockrate):
        self.clockrate = clockrate

    def get_snap_name(self, zdok):
        return "adcsnap%d" % zdok

    def find_spike(self, nfr):
        "Given a normalized spectrum (positive only), find the spike location."
        maxnfr = max(nfr)
        spike_indices = np.array([i for i in range(len(nfr)) if nfr[i]==maxnfr])
        if len(spike_indices) == 0:
            spike_freqs = np.array([-1])
        else:
            spike_freqs = spike_indices*self.clockrate*1.0/len(nfr)
        return spike_freqs

    def get_spec(self, zdok=0):
        "Returns the FFT of get_raw"
        raw = self.get_raw(zdok)
        fr = abs(fft(raw))
        nfr = fr/max(fr)
        nfr = nfr[0:len(nfr)/2]
        return nfr
        
    def get_raw(self, zdok):
        self.set_zdok(zdok)
        raw = self.get_adc_snapshot(self.get_snap_name(zdok))
        return raw

    def get_adc_snapshot(self, snap_name = None, bitwidth=8, man_trig=True, wait_period=2):
        """
        Reads a one-channel snapshot off the given 
        ROACH and returns the time-ordered samples.
        """
        
        snap_name = "adcsnap%d" % self.zdok if snap_name is None else snap_name

        # if this is a unit test, return some canned data
        if self.test:
            fn = "testdata/adc_snapshots/snapshot_%s_1" % snap_name
            return np.genfromtxt(fn, dtype=int)

        grab = self.roach.snapshot_get(snap_name, man_trig=man_trig, wait_period=wait_period)
        
        data = unpack('%ib' %grab['length'], grab['data'])
    
        return list(d for d in data) 

    def get_test_vector(self, snap_names, bitwidth=8, man_trig=True, wait_period=2, iteration = None):
        """
        Sets the ADC to output a test ramp and reads off the ramp,
        one per core. This should allow a calibration of the MMCM
        phase parameter to reduce bit errors.
    
        core_a, core_c, core_b, core_d = get_test_vector(roach, snap_names)
    
        NOTE: This function requires the ADC to be in "test" mode, please use 
        set_spi_control(roach, zdok_n, test=1) before-hand to be in the correct 
        mode.
        """
        data_out = []
        cores_per_snap = 4/len(snap_names)
        for snap in snap_names:
            if not self.test:
                # this is not a drill!  Grap a snap shot from the actuall FPGA
                data = self.get_adc_snapshot(snap, bitwidth, man_trig=man_trig, wait_period=wait_period)
            else:
                # get the data from saved files; set up specifially for the unit test
                i = iteration if iteration is not None else 1
                fn = "testdata/adc_snapshots/snapshot_%s_%i" % (snap, i) 
                data = np.genfromtxt(fn, dtype=int)
            data_bin = list(((p+128)>>1) ^ (p+128) for p in data)
            for i in range(cores_per_snap):
                data_out.append(data_bin[i::cores_per_snap])
        return data_out          
