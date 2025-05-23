# XBee modem

import umqtt

from umqtt.simple import MQTTClient
import time, network

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

wait = 1 # wait for 1 s
command = "None"

msgs_received = False

conn = network.Cellular()
while not conn.isconnected():
    time.sleep(4)

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
        execute_command()

def execute_command():
    global command
    byte_command = bytearray(command, 'uft-8')
    uart.write(byte_command)

c.connect()

while True:

    # check for commands from aws
    check_sub()

    # get data from board
    sample = uart.readline()

    # send sample data to aws
    if sample is not None:
        # publish data to aws
        c.publish("buoy/data", sample)

