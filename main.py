# XBee modem

import xbee

from umqtt.simple import MQTTClient
import time, network

from sys import stdin, stdout

from machine import UART
uart = UART(1,baudrate=115200)
uart.init(baudrate=115200, bits=8, parity=None, stop=1)

# AWS endpoint parameters
# noinspection SpellCheckingInspection
host = b'a189c4jm4usz34-ats'  # ex: b'abcdefg1234567'
# noinspection SpellCheckingInspection
region = b'ca-central-1'      # ex: b'us-east-1'

stdout.write("ready for client id\n")
client_id = stdin.readline()
stdout.write(client_id)
stdin.readline()
stdout.write("ready for buoy name\n")
buoy_name = stdin.readline()
stdout.write(buoy_name)
stdin.readline()

# noinspection PyTypeChecker
status_topic = buoy_name[:-1] + "/status"
# noinspection PyTypeChecker
command_topic = buoy_name[:-1] + "/commands"
# noinspection PyTypeChecker
data_topic = buoy_name[:-1] + "/data"
# noinspection PyTypeChecker
response_topic = buoy_name[:-1] + "/response"

# noinspection SpellCheckingInspection
aws_endpoint = b'%s.iot.%s.amazonaws.com' % (host, region)
# noinspection SpellCheckingInspection
ssl_params = {'keyfile': "/flash/cert/aws.key",
              'certfile': "/flash/cert/aws.crt",
              'ca_certs': "/flash/cert/aws.ca"}  # ssl certs

c = MQTTClient(client_id, aws_endpoint, ssl=True, ssl_params=ssl_params)
x = xbee.XBee()

command = None #bytearray(b"") # commands sent from aws


# noinspection PyUnusedLocal
def sub_cb(topic, msg):
    global command
    command = msg

def check_sub():
    try:
        c.check_msg()
    except OSError as e:
        stdout.write("ERROR, check_msg failed: %s\n" % str(e))
        reconnect()
    global command
    if command is not None:
        command = command[12:-2]
        if command.startswith("PING"):
            c.publish(response_topic, '{"message": "Connected"}')
        else:
            stdout.write(command)
            print("") # commands do not work without these empty print statements
            stdout.write("")
        command = None

def reconnect():
    try:
        c.connect()
    except Exception as e:
        stdout.write("connection failed: %s\n" % str(e))
        reconnect()
    c.set_callback(sub_cb)
    c.subscribe(command_topic)
    stdout.write("reconnected\n")

conn = network.Cellular()

def main():
    attempts = 0
    # attempt to connect ot the cell network
    while (not conn.isconnected()) and (attempts < 15):
        time.sleep(1)
        attempts += 1
        stdout.write("Attempt %d/15\n" % attempts)
    if not conn.isconnected():
        stdout.write("connection failed\n")
        x.sleep_now(10)
    else: # connect to aws
        try:
            c.connect()
        except Exception as e:
            stdout.write("connection failed: %s\n" % str(e))
            reconnect()
        stdout.write("connected\n")
    # subscribe to receive commands from aws
    c.set_callback(sub_cb)
    try:
        c.subscribe(command_topic)
    except Exception as e:
        stdout.write("ERROR, subscribe failed: %s\n" % str(e))
        reconnect()
    stdout.write("")
    sample_loop = True  # if the buoy is sampling
    while sample_loop:
        # check for commands from aws
        check_sub()
        # get data from logger board
        data = stdin.readline()
        #if data is not None and len(data) > 1:
        if data.startswith(b'CT'):
            # format for JSON and publish data to aws
            sample = b'{"message": "' + data[:-1] + b'"}'
            try:
                c.publish(data_topic, sample)
            except OSError as e:
                stdout.write("ERROR, publish failed: %s\n" % str(e))
                reconnect()
        elif len(data) > 1:
            # format for JSON and publish data to aws
            sample = b'{"message": "' + data[:-1] + b'"}'
            try:
                c.publish(response_topic, sample)
            except OSError as e:
                stdout.write("ERROR, publish failed: %s\n" % str(e))
                reconnect()

    c.disconnect()
    stdout.write("disconnected\n")
    # sleep forever
    x.sleep_now(100)

if __name__ == "__main__":
    main()