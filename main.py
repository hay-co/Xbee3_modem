# XBee modem

import xbee

from umqtt.simple import MQTTClient
import time, network

from sys import stdin, stdout

from machine import UART
uart = UART(1,baudrate=115200)
uart.init(baudrate=115200, bits=8, parity=None, stop=1)

# AWS endpoint parameters
host = b'a189c4jm4usz34-ats'    # ex: b'abcdefg1234567'
region = b'ca-central-1'        # ex: b'us-east-1'
client_id = b'XBee_2'             # ex: b'XBee'

aws_endpoint = b'%s.iot.%s.amazonaws.com' % (host, region)
ssl_params = {'keyfile': "/flash/cert/aws.key",
              'certfile': "/flash/cert/aws.crt",
              'ca_certs': "/flash/cert/aws.ca"}  # ssl certs

c = MQTTClient(client_id, aws_endpoint, ssl=True, ssl_params=ssl_params)
x = xbee.XBee()

wait = 500 # wait for half a second
command = None #bytearray(b"") # commands sent from aws

def sub_cb(topic, msg):
    global command
    command = msg

def check_sub():
    c.check_msg()
    global command
    if command is not None:
        command = command[16:-3]
        stdout.write(command)
        print("")
        stdout.write("")
        command = None

conn = network.Cellular()

def main():
    attempts = 0
    # attempt to connect ot the cell network
    while (not conn.isconnected()) and (attempts < 15):
        time.sleep(4)
        attempts += 1
        stdout.write("Attempt %d/15\n" % attempts)
    if not conn.isconnected():
        stdout.write("connection failed\n")
        x.sleep_now(100)
    else: # connect to aws
        c.connect()
        stdout.write("connected\n")
    # subscribe to receive commands from aws
    c.set_callback(sub_cb)
    c.subscribe('buoy/commands')
    stdout.write("")
    sample_loop = True  # if the buoy is sampling
    while sample_loop is True:
        # check for commands from aws
        check_sub()
        # get data from logger board
        data = stdin.readline()
    if data is not None and len(data) > 1:
        # format for JSON and publish data to aws
        sample = b'{"message": "' + data[:-1] + b'"}'
        c.publish('buoy/data', sample)

    c.disconnect()
    stdout.write("disconnected\n")
    # sleep forever
    x.sleep_now(100)

if __name__ == "__main__":
    main()