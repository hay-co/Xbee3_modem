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
client_id = b'XBee'             # ex: b'XBee' must be different for every device

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
    try:
        c.check_msg()
    except OSError as e:
        stdout.write("Error: check_msg failed: %s\n" % str(e))
        try:
            c.connect()
            c.set_callback(sub_cb)
            c.subscribe('buoy/commands')
            stdout.write("connected\n")
        except Exception as e:
            stdout.write("connection failed: %s\n" % str(e))
            x.sleep_now(100)
    global command
    if command is not None:
        command = command[12:-2]
        stdout.write(command)
        print("") # commands do not work without these empty print statements
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
        try:
            c.connect()
        except Exception as e:
            stdout.write("connection failed: %s\n" % str(e))
            x.sleep_now(100)
        stdout.write("connected\n")
    # subscribe to receive commands from aws
    c.set_callback(sub_cb)
    c.subscribe('buoy/commands')
    stdout.write("")
    sample_loop = True  # if the buoy is sampling
    #keep_alive = 0
    while sample_loop is True:
        # keep the connection from timing out
        #if keep_alive > 200:
            #c.ping()
            #keep_alive = 0
        #keep_alive += 1
        # check for commands from aws
        check_sub()
        # get data from logger board
        data = stdin.readline()
        #if data is not None and len(data) > 1:
        if data.startswith(b'CT'):
            # format for JSON and publish data to aws
            sample = b'{"message": "' + data[:-1] + b'"}'
            c.publish('buoy/data', sample)
        elif len(data) > 1:
            # format for JSON and publish data to aws
            sample = b'{"message": "' + data[:-1] + b'"}'
            c.publish('buoy/response', sample)

    c.disconnect()
    stdout.write("disconnected\n")
    # sleep forever
    x.sleep_now(100)

if __name__ == "__main__":
    main()