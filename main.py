# XBee modem

import umqtt
import xbee

from umqtt.simple import MQTTClient
import time, network

from machine import UART
uart = UART(0,baudrate=115200)
uart.init(baudrate=115200, bits=8, parity=None, stop=1)

x = xbee.XBee()

# AWS endpoint parameters
host = b'a189c4jm4usz34-ats'  # ex: b'abcdefg1234567'
region = b'ca-central-1'  # ex: b'us-east-1'
client_id = b'XBee'

aws_endpoint = b'%s.iot.%s.amazonaws.com' % (host, region)
ssl_params = {'keyfile': "/flash/cert/aws.key",
              'certfile': "/flash/cert/aws.crt",
              'ca_certs': "/flash/cert/aws.ca"}  # ssl certs

wait = 500 # wait for half a second
command = "None"
on = True
sample = ""
msgs_received = False

c = MQTTClient(client_id, aws_endpoint, ssl=True, ssl_params=ssl_params)

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

def send_command():
    global command
    command = bytearray(command, 'uft-8')
    uart.write(command)

conn = network.Cellular()

while True:
    while not conn.isconnected():
        time.sleep(4)
    uart.write(bytearray(b'connected'))
    c.connect()
    while on is True:

        # check for commands from aws
        check_sub()

        # get data from board
        data = uart.readline()
        data = data.decode()
        data.replace("\n", "")
        if data is "sleep":
            on = False
        # send sample data to aws
        elif data is not None:
            sample = sample + data
        elif data is "end":
            # publish data to aws
            sample = '{"message": "' + sample + '"}'
            c.publish('buoy/data', sample)
            sample = ""

    c.disconnect()
    # sleep until pin wake
    x.sleep_now(None, True)
    on = True
