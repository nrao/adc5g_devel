#!/usr/bin/python

"""
This code opens a socket to the GPIB->lan controller, and uses it 
to set the synthesizer frequency.  

It's not very smart or bulletproof...
"""
#
# Import this, then define the constants used and the global socket variable.
#

import socket

#sock = socket.socket()
sock = None
freq_cmd= ":FREQ:CW"
pwr_cmd= ":POW:LEV"

# addr when in the tape room
#addr = '10.16.96.174'

# addr when in the equipment room
addr = '10.16.98.79'


def gpib_init(new_freq, new_ampl):
    global sock
    sock = socket.socket()
    open_gpib(sock, addr);
    set_freq(new_freq)
    set_ampl(new_ampl)
    #set_power(sock,"-20");  
    #set_frequency(sock,"1.0E6")
    RF_power(sock,"ON");

def open_gpib(sock, addr):
    #sock.connect(('10.16.98.79', 1234))
    sock.connect((addr, 1234))

def set_frequency(sock, freq):
    cmd_str = "%s %s\r" % (freq_cmd, freq) 
    sock.send(cmd_str)

def set_freq(freq):
    set_frequency(sock, str(freq)+"E6")

def set_ampl(ampl):
    set_power(sock, str(ampl))

def set_power(sock, pwr ):
    cmd_str = "%s %s DBM\r" % (pwr_cmd, pwr) 
    sock.send(cmd_str)

def RF_power(sock,state ):
    cmd_str = "%s %s\r" % (":OUTP:STAT", state) 
    sock.send(cmd_str)

def close_gpib(sock):
    sock.close()

def clean_up(sock):
    RF_power(sock, "OFF")
    close_gpib(sock)

def close_sock():
    global sock
    if sock is None:
        print 'Connection to the synthesizer hasn\'t been established...'
    else:
        clean_up(sock)

### End of function and variable definitions

#
# Here is what do do to initialize the system
#
#
# Here is where your code goes.  Just use the set_frequency() and 
# set_power() as needed in the code where you are looping.
#  

'''
while (1 < 2) :
    str = raw_input("Enter frequency in Hz");
    print "Got :",str ;
    pwr_level = raw_input("Enter power level in dBm");
    print "Got :",pwr_level ;
    set_frequency(sock,str)
    set_power(sock,pwr_level)
'''
#
# Clean up by turning off the power, and closing the socket.
#

#RF_power(sock, "OFF")
#close_gpib(sock)


