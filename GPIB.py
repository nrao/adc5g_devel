import socket

# addr when in the tape room
#addr = '10.16.96.174'

# addr when in the equipment room
#addr = '10.16.98.79'

class GPIB:

    """
    This code opens a socket to the GPIB->lan controller, and uses it 
    to set the synthesizer frequency.  
    
    It's not very smart or bulletproof...
    """

    def __init__(self, addr, test = True, freq = None, ampl = None):

        self.test = test
        self.addr = addr

        self.sock = None
        if not test:
            try:
                self.sock = socket.socket()
                self.sock.connect((self.addr, 1234))
            except:
                print "*** Could not connect GPIB to: ", self.addr
                self.test = True

        self.freq_cmd= ":FREQ:CW"
        self.pwr_cmd= ":POW:LEV"

        # history of all cmds sent to socket
        self.cmds = []

        self.freq = None
        self.ampl = None

        if freq is not None:
            self.set_freq(freq)

        if ampl is not None:
            self.set_ampl(ampl)

        self.set_rf_power("ON")

    def send(self, cmd):
        self.cmds.append(cmd)
        if not self.test:
            self.sock.send(cmd)

    def set_rf_power(self, state):
        cmd_str = "%s %s\r" % (":OUTP:STAT", state)
        self.send(cmd_str)

    def set_freq(self, freq):
        self.freq = freq
        self.set_frequency(str(freq)+"E6")

    def set_frequency(self, freq):    
        cmd_str = "%s %s\r" % (self.freq_cmd, freq)
        self.send(cmd_str)

    def set_ampl(self, ampl):
        self.ampl = ampl
        self.set_power(str(ampl))

    def set_power(self, pwr ):
        cmd_str = "%s %s DBM\r" % (self.pwr_cmd, pwr) 
        self.send(cmd_str)

    def close(self):
        if not self.test:
            self.sock.close()

    def clean_up(self):
        self.set_rf_power("OFF")
        self.close()

if __name__ == "__main__":
    gpib = GPIB("", test = True, freq = 10.0, ampl = 1.0)
    gpib.clean_up()
    print gpib.cmds
