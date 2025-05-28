# XBee modem

import xbee, datetime

from umqtt.simple import MQTTClient
import time, network

from digi import gnss

from machine import UART
uart = UART(1,baudrate=115200)
uart.init(baudrate=115200, bits=8, parity=None, stop=1)

# AWS endpoint parameters
host = b'a189c4jm4usz34-ats'  # ex: b'abcdefg1234567'
region = b'ca-central-1'  # ex: b'us-east-1'
client_id = b'XBee'

aws_endpoint = b'%s.iot.%s.amazonaws.com' % (host, region)
ssl_params = {'keyfile': "/flash/cert/aws.key",
              'certfile': "/flash/cert/aws.crt",
              'ca_certs': "/flash/cert/aws.ca"}  # ssl certs

c = MQTTClient(client_id, aws_endpoint, ssl=True, ssl_params=ssl_params)
x = xbee.XBee()

wait = 500 # wait for half a second
command = bytearray(b"") # commands sent from aws
location = bytearray(b"") # gps data
msgs_received = False # if there was a message sent from aws

def sub_cb(topic, msg):
    global msgs_received
    msgs_received = True
    global command
    command = msg

def check_sub():
    c.set_callback(sub_cb)
    c.subscribe("xbee/test")
    global msgs_received
    msgs_received = False
    timeout = time.time() + wait
    while (not msgs_received) and (time.time() < timeout):
        c.check_msg()
        time.sleep(1)
    if command != b'':
        print(command)
        send_command()

def location_cb(gps):
    if gps is not None:
        sys_time = str(gps["timestamp"] - 363896460)
        uart.write(bytearray(sys_time, 'utf-8'))
        print(sys_time + "\n")
        print(str(gps["latitude"]) + "\n")
        print(str(gps["longitude"]) + "\n")
        print(str(gps["altitude"]) + "\n")
        global location
        location = bytearray(str(gps["latitude"]) + ", " + str(gps["longitude"]) + ", " + str(gps["altitude"]), 'utf-8')
    else:
        uart.write(bytearray(b'gps error\n'))
        print("gps error\n")

def send_command():
    global command
    command = command[16:-3]
    command = command
    print(command)
    uart.write(command)

conn = network.Cellular()

def main():
    gnss.single_acquisition(location_cb,60)
    time.sleep(60)
    attempts = 0
    while (not conn.isconnected()) and (attempts < 15):
        time.sleep(4)
        attempts += 1
    if not conn.isconnected():
        uart.write(bytearray(b'connection failed\n'))
        print("connection failed\n")
        x.sleep_now(None)
    c.connect()
    uart.write(bytearray(b'connected\n'))
    print("connected\n")
    global location
    if location != b"":
        location = b'{"message": "' + location + b'"}'
        c.publish('xbee/test', location)
    on = True  # if the buoy is sampling
    while on is True:
        # check for commands from aws
        check_sub()
        # get data from board
        data = uart.readline()
        if data == b'sleep\n':
            on = False
        # if the buffer can handle a full sample
        elif data is not None:
            # publish data to aws
            sample = bytearray(data)
            sample = sample[:-1]
            sample = b'{"message": "' + sample + b'"}'
            c.publish('xbee/test', sample)
    c.disconnect()
    uart.write(bytearray(b'disconnected\n'))
    print("disconnected\n")
    # sleep forever
    x.sleep_now(None)

if __name__ == "__main__":
    main()