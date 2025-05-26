# XBee modem

import xbee

from umqtt.simple import MQTTClient
import time, network

from digi import gnss

from machine import UART
uart = UART(0,baudrate=115200)
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
command = "None" # commands sent from aws
sample = "" # final sample sent to aws
location = "" # gps data
msgs_received = False # if there was a message sent from aws

def sub_cb(topic, msg):
    global msgs_received
    msgs_received = True
    global command
    command = msg

def check_sub():
    c.set_callback(sub_cb)
    c.subscribe("buoy/data")
    global msgs_received
    msgs_received = False
    timeout = time.time() + wait
    while (not msgs_received) and (time.time() < timeout):
        c.check_msg()
        time.sleep(1)
    if command != "none":
        send_command()

def gps_cb(gps):
    if gps is not None:
        sys_time = gps["timestamp"]
        uart.write(sys_time)
        global location
        location = gps
    else:
        uart.write(bytearray(b'gps error\n'))

def send_command():
    global command
    command.replace('{"message": "', "")
    command.replace('"}', "")
    command = bytearray(command, 'uft-8')
    uart.write(command)

conn = network.Cellular()

def main():
    gnss.single_acquisition(gps_cb,60)
    attempts = 0
    while (not conn.isconnected()) and (attempts < 30):
        time.sleep(4)
        attempts += 1
    if not conn.isconnected():
        uart.write(bytearray(b'connection failed\n'))
        x.sleep_now(None)
    c.connect()
    uart.write(bytearray(b'connected\n'))
    global location
    if location is not None:
        location = '{"message": "' + location + '"}'
        c.publish('buoy/data', location)
    on = True  # if the buoy is sampling
    while on is True:

        # check for commands from aws
        check_sub()

        # get data from board
        data = uart.readline()
        if data is b'sleep\n':
            on = False
        # if the buffer can handle a full sample
        elif data is not None:
            # publish data to aws
            data = data.decode()
            data.replace("\n", "")
            data = '{"message": "' + data + '"}'
            c.publish('buoy/data', data)
        ''' 
        # if the buffer is too small for a full sample
        elif data is not None:
            data = data.decode()
            data.replace("\n", "")
            sample = sample + data
        # send sample data to aws
        elif data is b'end':
            # publish data to aws
            sample = '{"message": "' + sample + '"}'
            c.publish('buoy/data', sample)
            sample = ""
        '''

    c.disconnect()
    uart.write(bytearray(b'disconnected\n'))
    # sleep forever
    x.sleep_now(None)
