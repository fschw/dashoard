#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import logging
import ccs811LIBRARY
import os
import subprocess


logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG,  datefmt='%Y-%m-%d %H:%M:%S')

picdir = os.path.join(os.path.join(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'e-Paper'),'RaspberryPi_JetsonNano'),'python'),'pic')
logging.info("Add pic dir: "+ picdir)

#inintialize mockups on dev env, and real libs on rasp
if os.path.exists('/sys/bus/platform/drivers/gpiomem-bcm2835'):
    logging.info("Start in productive mode...")
    libdir = os.path.join(os.path.join(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'e-Paper'),'RaspberryPi_JetsonNano'),'python'),'lib')
    if os.path.exists(libdir):
        sys.path.append(libdir)
    logging.info("Add lib dir: "+ libdir)

    libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Adafruit_Python_DHT')
    if os.path.exists(libdir):
        sys.path.append(libdir)
    logging.info("Add lib dir: "+ libdir)

    import Adafruit_DHT
    from waveshare_epd import epd4in2
else:
    logging.info("Start in mockup mode...")
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mockups'))
    import Adafruit_DHT_mock
    from waveshare_epd import epd4in2_mock

import time
from PIL import Image, ImageDraw, ImageFont
import subprocess
import traceback
import requests
from flask import Flask
from flask import request
import threading

access_token = ""
app = Flask(__name__)
@app.route("/")
def receive_code():
    logging.info("HTTP req")
    code = request.args.get('code', '')
    if code != "":
        print("Code received:" + code)
        url = "https://iam.viessmann.com/idp/v2/token"
        header = {"Content-Type": "application/x-www-form-urlencoded"}
        data = "grant_type=authorization_code&client_id=9ceff2a5f57d345a580142626e3b4a7f&redirect_uri=http://192.168.178.202:4200/&code_verifier=2e21faa1-db2c-4d0b-a10f-575fd372bc8c-575fd372bc8c&code="+code
        response = requests.post(url=url, headers=header, data=data)
        if response.ok:
            global access_token
            access_token = response.json()['access_token']
            logging.info("New access token: " + access_token)

            return "Authorisation OK"
        else:
            return "Authorisation NOK"
    return "No code received"


if __name__ == "__main__":
    args = {'host': '0.0.0.0', 'port' : 4200}
    threading.Thread(target=app.run, kwargs=args).start()

font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

sensor = ccs811LIBRARY.CCS811()
def setup(mode=1):
    print('Starting CCS811 Read')
    sensor.configure_ccs811()
    sensor.set_drive_mode(mode)

    if sensor.check_for_error():
        sensor.print_error()
        raise ValueError('Error at setDriveMode.')

    result = sensor.get_base_line()
    sys.stdout.write("baseline for this sensor: 0x")
    if result < 0x100:
        sys.stdout.write('0')
    if result < 0x10:
        sys.stdout.write('0')
    sys.stdout.write(str(result) + "\n")


#start pigpiod
'''
try:
    res = subprocess.run("sudo pigpiod", shell=True, check=True, text=True)
    logging.info(res.stdout)
    setup(1)
    res = subprocess.run("sudo killall pigpiod", shell=True, check=True, text=True)
    logging.info(res.stdout)
except IOError as e:
    logging.info(e)
'''

#check garage door state
#os.system("ssh -i /home/pi/.ssh/id_rsa.pub fsc@192.168.178.201")
cmd = "ssh -i /home/pi/.ssh/id_rsa.pub fsc@192.168.178.201"# & cd garage & python readSwitch.py"
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
print(process.communicate()[0])

try:
    epd = epd4in2.EPD()
    logging.info("Init and Clear display")
    epd.init()
    epd.Clear()
    loop = True
    cnt = 1
    while loop:
        image = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(image)
        logging.info("Updating for Iteration " + str(cnt))
        cnt = cnt + 1



        #os.system("ssh -i .ssh/id_rsa.pub fsc@192.168.178.201")
        #os.system("cd garage")
        #os.system("python readSwitch.py")

        '''client = SSHClient()
        client.look_for_keys(True)
        client.connect("172.168.178.201", username = "fsc")
        stdin, stdout, stderr = client.exec_command('cd garage & python readSwitch.py')
        print(type(stdin))
        print(type(stdout))
        print(type(stderr))
        client.close()'''

        #read outside temp
        logging.info("Read outside temp...")
        logging.info("Token:" + access_token)
        header = {"Authorization": "Bearer " + access_token}
        req1 = "https://api.viessmann.com/iot/v1/equipment/installations/952499/gateways/7637415022052208/devices/0/features/heating.sensors.temperature.outside"
        logging.info("reading temperature.outside")
        response = requests.get(url=req1, headers=header)
        outsideTemp = ""
        if response.status_code == 200:
            outsideTemp = response.json()["data"]["properties"]["value"]["value"]
            logging.info('Outside temp: {:.1f}°'.format(outsideTemp))
            draw.text((10, 0), 'Außen: {:.1f}°'.format(outsideTemp), font=font24, fill=0)

        # read humidity and inside temp
        logging.info("Read inside temperature and humidity...")
        insideHumidity, insideTemp = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 4)

        if insideHumidity is not None and insideTemp is not None:
            logging.info( 'Inside temp: {:.1f}°'.format(insideTemp))
            logging.info( 'Rel. Humidity: {:.1f}%'.format(insideHumidity))
            draw.text((10, 50), 'Innen: {:.1f}°'.format(insideTemp), font = font24, fill = 0)
            draw.text((10, 100), 'Rel: {:.1f}%'.format(insideHumidity), font = font24, fill = 0)
        else:
            logging.info( "Could not read from Inside temp/Humidity")

        #res = subprocess.run("sudo pigpiod", shell=True, check=True, text=True)
        #logging.info(res.stdout)
        '''
        logging.info("Read CO2 and TVOC...")
        if sensor.data_available():
            sensor.read_logorithm_results()
            logging.info( "CO2: {0:.1f} TVOC: {1:.1f}".format(sensor.CO2, sensor.tVOC))
            draw.text((10, 150), "CO2: {0:.1f} TVOC: {1:.1f}".format(sensor.CO2, sensor.tVOC), font = font24, fill = 0)
        elif sensor.check_for_error():
            logging.info( "Could not read from CO2/TVOC Sensor")
        '''
        #res = subprocess.run("sudo killall pigpiod", shell=True, check=True, text=True)
        #logging.info(res.stdout)

        logging.info("Adding visuals to image...")
        upper = 80
        lower = 299
        left = 70
        right = 330
        #house frame
        draw.line((left, lower, right, lower), fill = 0, width = 3)
        draw.line((left, lower, left, upper), fill = 0, width = 3)
        draw.line((left, upper, right, upper), fill = 0, width = 3)
        draw.line((right, upper, right, lower), fill = 0, width = 3)

        #roof
        mid = 200
        y = mid*upper/(mid-left)
        draw.line((mid, 1, 0, y), fill = 0, width = 3)
        draw.line((mid, 1, 400, y), fill = 0, width = 3)

        #buffer
        '''draw.line((70, 50, 20, 100), fill = 0)
        draw.rectangle((20, 50, 70, 100), outline = 0)
        draw.line((165, 50, 165, 100), fill = 0)
        draw.line((140, 75, 190, 75), fill = 0)
        draw.arc((140, 50, 190, 100), 0, 360, fill = 0)
        draw.rectangle((80, 50, 130, 100), fill = 0)'''
        #draw.chord((200, 50, 250, 100), 0, 360, fill = 0)
        epd.display(epd.getbuffer(image))
        time.sleep(30)


except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd.Clear()
    epd.sleep()
    epd4in2.epdconfig.module_exit()
    exit()
