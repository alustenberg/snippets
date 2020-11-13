#!/usr/bin/python3 -u

from serial import Serial
from time import time, sleep
from datetime import datetime, timedelta
from sys import stderr


def cmd(ser,cmd, want_ok = True):
    if isinstance(cmd,str):
        ser.write(cmd.encode())
    else:
        ser.write(cmd)
    ser.write(b"\r");
    if want_ok:
        return ser.readline() == 'OK'
    else:
        return ser.readline().decode('ascii')


def cmd_getd(ser):
    ret = cmd(ser,'GETD',False)
    s = ret.split('\r')[0]
    v = int(s[0:4])/100.0
    a = int(s[4:8])/100.0
    cc = s[8] == '1'

    #print('getd: {:s} {:s} {:s}'.format(s[0:4], s[4:8], s[8]))
    #print('getd: {:f} {:f} {:b}'.format(v,a,cc))

    return (v,a,cc)

def cmd_volt(ser, v):
    cmd(ser,'VOLT{:03.0f}'.format(v * 10))

def cmd_curr(ser, a):
    cmd(ser,'CURR{:03.0f}'.format(a * 100))

def charge_loop(ser, end_v, min_a, max_a, ah ):
    tmah = 0
    tick_time = 15

    cmd_volt(ser,end_v)  # set max voltage to termination voltage
    cmd_curr(ser,max_a)  # set charge voltage
    cmd(ser,'SOUT0') # enable output

    start = tick = datetime.now()
    print('"time (m)","v","A","mAh"')

    while True:
        (charge_v,charge_a,charge_cc) = cmd_getd(ser)
        run = tick - start
        print('{:5.2f},{:2.1f},{:2.1f},{:5.0f}'.format(run.total_seconds()/60, charge_v, charge_a, tmah))

        tick = tick + timedelta(seconds=tick_time)
        # amp * ( 1000 mah / 60 min ) ( tick * 1/60 sec/min )
        tmah = tmah + charge_a * ( 1000.0 / 60 ) * ( tick_time / 60 )

        if min_a is not None and charge_a <= min_a:
            break

        if ah is not None and tmah >= (1000*ah):
            break

        sleep((tick-datetime.now()).total_seconds())

    print('charge complete, {:6.0f}mAh charged'.format(tmah))


if __name__ == '__main__':
    import argparse
    argp = argparse.ArgumentParser( description = 'battery charging' )
    argp.add_argument( '--volt', dest='volt', nargs='?', type=float, default=51  , help="End voltage")
    argp.add_argument( '--amp' , dest='amp' , nargs='?', type=float, default=1.0 , help="max amperage")
    argp.add_argument( '--min' , dest='min' , nargs='?', type=float, default=None, help="shutoff amperage")
    argp.add_argument( '--ah'  , dest='ah'  , nargs='?', type=float, default=None, help="max charge Ah")

    argp.add_argument( '--serial', dest='serial', nargs='?', type=str, default='/dev/ttyUSB0', help="Serial Device")

    args = argp.parse_args()

    with Serial(args.serial,9600,timeout=2) as ser:
        try:
            charge_loop(ser, args.volt, args.min, args.amp, args.ah)
        except:
            raise
        finally:
            cmd(ser,'SOUT1') # disable output

