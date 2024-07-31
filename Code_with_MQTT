# Circuitpython code for biofilm cell factory
# Monitoring 2 CO2 sensors, lux sensor, LED light function, an RTC, and screen displaying collected data
# IoT connection to adafruitio to access data on adafruitio
# ===================================================================================================================

import time
import busio
import analogio
import board
import storage
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import sdcardio
import adafruit_veml7700
import digitalio
import adafruit_scd30
import adafruit_datetime
from adafruit_display_shapes.circle import Circle
from adafruit_ds3231 import DS3231
from adafruit_dps310 import DPS310
import adafruit_requests as requests
import adafruit_espatcontrol.adafruit_espatcontrol_socket as socket
from adafruit_espatcontrol import adafruit_espatcontrol
from adafruit_espatcontrol import adafruit_espatcontrol_wifimanager
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from secrets import secrets

# release display from previous screen use
displayio.release_displays()

# set the interval for measurements to be taken
measurement_interval = 30

# i2c for lux, CO2 ambient and screen
i2c0 = busio.I2C(board.GP5, board.GP4)
# i2c for CO2 metabolism
i2c1 = busio.I2C(board.GP27, board.GP26)
# use pressure sensor lib
dps310 = DPS310(i2c0)
# use scd30 library for sensiron sensor
scd_ambient = adafruit_scd30.SCD30(i2c0)
scd_system = adafruit_scd30.SCD30(i2c1)
# i2c for LED start
led = digitalio.DigitalInOut(board.GP2)
led.direction = digitalio.Direction.OUTPUT
# i2c for LED end
led2 = digitalio.DigitalInOut(board.GP7)
led2.direction = digitalio.Direction.OUTPUT
# Initialize UART connection to the ESP8266 WiFi Module.
RX = board.GP17
TX = board.GP16
uart = busio.UART(TX, RX, receiver_buffer_size=2048)
# initialize esp module
esp = adafruit_espatcontrol.ESP_ATcontrol(uart, 115200, debug=False)
# initialize WiFi
wifi = adafruit_espatcontrol_wifimanager.ESPAT_WiFiManager(esp, secrets)
# Set MQTT socket
MQTT.set_socket(socket, esp)

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

def connected(client):
    print("Connected to Adafruit IO! ")

def subscribe(client, userdata, topic, granted_qos):
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def disconnected(client):
    print("Disconnected from Adafruit IO!")

def on_msg(client, topic, message):
    # Method called whenever feeds has a new value
    print("New message on topic {0}: {1} ".format(topic, message))

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe

# Set up a callback for the feed
io.add_feed_callback("CO2", on_msg)

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

# Subscribe to all messages on the led feed
for feed_id in ['CO2', 'Lux-start', "Lux-end"]:
  io.subscribe(feed_id)

# RTC settings
rtc = DS3231(i2c0)
if rtc.lost_power:
    rtc.datetime = time.struct_time((2000, 4, 25, 12, 0, 0, 0, -1, -1))

# lux sensor settings start
veml7700 = adafruit_veml7700.VEML7700(i2c0)
veml7700.light_gain = veml7700.ALS_GAIN_1_8
veml7700.integration_time = veml7700.ALS_100MS

# lux sensor settings end
veml77001 = adafruit_veml7700.VEML7700(i2c1)
veml77001.light_gain = veml7700.ALS_GAIN_1_8
veml77001.integration_time = veml7700.ALS_100MS

# sd card settings
spi = busio.SPI(board.GP10, MOSI=board.GP11, MISO=board.GP12)
cs = board.GP15
sd = sdcardio.SDCard(spi, cs)

# filename is the date and time of start
current_file_time = rtc.datetime
filename = "{:04}-{:02}-{:02},{:02}-{:02}-{:02}".format(
    current_file_time.tm_year, current_file_time.tm_mon, current_file_time.tm_mday,
    current_file_time.tm_hour, current_file_time.tm_min, current_file_time.tm_sec)

# mount sd card
vfs = storage.VfsFat(sd)
storage.mount(vfs, "/sd")

# screen settings
# oled reset pin
oled_reset = board.GP20

# i2c = board.STEMMA_I2C()  for using the built-in STEMMA QT connector on a microcontroller
display_bus = displayio.I2CDisplay(i2c0, device_address=0x3C, reset=oled_reset)

# screen dimensions (W: 128, H: 64, B:0)
WIDTH = 128
HEIGHT = 64
BORDER = 0

display = adafruit_displayio_ssd1306.SSD1306(
    display_bus, width=WIDTH, height=HEIGHT)

# Make the display context
splash = displayio.Group()
display.show(splash)

color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White 0xFFFFFF

bg_sprite = displayio.TileGrid(
    color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Settings for border
inner_bitmap = displayio.Bitmap(WIDTH - BORDER * 2, HEIGHT - BORDER * 2, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black 0x000000
inner_sprite = displayio.TileGrid(
    inner_bitmap, pixel_shader=inner_palette, x=BORDER, y=BORDER
)
splash.append(inner_sprite)

# Create text labels for the screen to display with positions
text_labels = [
    label.Label(terminalio.FONT, text="Lux start:", 
                color=0xFFFFFF, x=0, y=4),
    label.Label(terminalio.FONT, text="Lux end:",
                color=0xFFFFFF, x=0, y= 15),
    label.Label(terminalio.FONT, text="Ambient CO2:",
                color=0xFFFFFF, x=0, y=26),
    label.Label(terminalio.FONT, text="System CO2:",
                color=0xFFFFFF, x=0, y=37),
    label.Label(terminalio.FONT, text="Biofilm CO2:",
                color=0xFFFFFF, x=0, y=48),
    label.Label(terminalio.FONT, text="Temperature:",
                color=0xFFFFFF, x=0, y=59)
]

# Add text labels to the display
for text_label in text_labels:
    splash.append(text_label)

# Create the data labels it will display
number_labels = [
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=70, y=4),
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=75, y=15),
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=80, y=26),
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=75, y=37),
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=75, y=48),
    label.Label(terminalio.FONT, text="0", color=0xFFFFFF, x=75, y=59),
]

# Add number labels to the display
for number_label in number_labels:
    splash.append(number_label)

# Error dictionary to see where fualts occur
dict_err = {"lux_err": 0, "amb_err": 0,
            "sys_err": 0, "temp_err": 0, 
            "humid_err": 0, "press_err": 0}

ambient_CO2_list = []

def lux_measuring():
    # turn LED on
    led.value = True
    led2.value = True
    # get readings from sensors
    try:
        global luminosity1
        luminosity1 = veml7700.lux
        global luminosity2
        luminosity2 = veml77001.lux
    except:
        dict_err["lux_err"] =+1

def pressure_measuring():
    try:
        global pressure
        pressure = dps310.pressure
    except:
        dict_err["press_err"] =+1
        pass

def CO2_measuring():
    try:
        global CO2_ambient
        CO2_ambient = scd_ambient.CO2
        ambient_CO2_list.append(CO2_ambient)
    except:
        dict_err["amb_err"] =+1
        pass
    try:
        global CO2_system
        CO2_system = scd_system.CO2
    except:
        dict_err["sys_err"] =+1
        pass
    try:
        global CO2_biofilm
        CO2_biofilm = float(CO2_system) - float(CO2_ambient)
    except:
        pass
    try:
        if len(ambient_CO2_list) == 16 :
            actual_ambient = ambient_CO2_list[0]
            CO2_biofilm = float(CO2_system) - float(actual_ambient)
            ambient_CO2_list.pop(0)
        else:
            pass
    except:
        pass

def temperature_measuring():
    try:
        global Temp
        Temp = dps310.temperature
    except:
        dict_err["temp_err"] =+1
        pass

def humidity_measuring():
    try:
        global Humid
        Humid = scd_ambient.relative_humidity
    except:
        dict_err["humid_err"] = +1
        pass

def time_settings():
    try:
        # get elapsed time in seconds
        global elapsed_time
        elapsed_time = time.monotonic() - initial_time
        # get current time at reading
        global current_time
        current_time = rtc.datetime
        global Time_stamp
        Time_stamp = "{:04}-{:02}-{:02}, {:02}:{:02}:{:02}".format(
            current_time.tm_year, current_time.tm_mon, current_time.tm_mday,
            current_time.tm_hour, current_time.tm_min, current_time.tm_sec)
    except:
        pass

def terminal_print():
    print("Time stamp: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time.tm_year, current_time.tm_mon, current_time.tm_mday,
        current_time.tm_hour, current_time.tm_min, current_time.tm_sec))
    print("Lux start:", luminosity1)
    print("Lux end:", luminosity2)
    print("Ambient CO2: %d PPM" % CO2_ambient)
    print("System CO2: %d PPM" % int(CO2_system))
    print("Biofilm CO2: %d PPM" % CO2_biofilm)
    print("Temperature: %0.2f degrees C" % Temp)
    print("Humidity: %0.2f %% rH" % Humid)
    print("Pressure: %d hPa" % pressure)
    print(elapsed_time)

def screen_update():
    try:
        # update number labels of readings
        number_labels[0].text = "{:.0f}".format(luminosity1)
        number_labels[1].text = "{:.0f}".format(luminosity2)
        number_labels[2].text = "{:.0f}".format(CO2_ambient)
        number_labels[3].text = "{:.0f}".format(CO2_system)
        number_labels[4].text = "{:.2f}".format(CO2_biofilm)
        number_labels[5].text = "{:.2f}".format(Temp)
    except:
        pass

def write_sd():
    # write readings to sd card
    try:
        file.write(
            "{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(
                Time_stamp, elapsed_time, luminosity1, luminosity2, CO2_ambient, CO2_system, CO2_biofilm, Temp, Humid, pressure, dict_err
            )
        )
    except:
        pass

def adafruit_upload():
    # Poll for incoming messages
    try:
        io.loop()
    except (ValueError, RuntimeError, Exception) as e:
        print("Failed to get data, retrying\n", e)
        try:
            wifi.reset()
            io.reconnect()
        except:
            pass
    # publish to adafruitio feed
    try:
        io.publish("CO2", CO2_biofilm)
        io.publish("Lux-start", luminosity1)
        io.publish("Lux-end", luminosity2)
    except (Exception):
    #Error handling skips uploading if it cant connect or publish0
        try:
            print("Failed to upload to cloud")
            io.reconnect()
            io.publish("CO2", CO2_biofilm)
            io.publish("Lux-start", luminosity1)
            io.publish("Lux-end", luminosity2)
            print("published")
        except:
            pass

# set start time
start_time = 0.0
initial_time = time.monotonic()

while True:
    with open(f"/sd/{filename}.csv", "a") as file:
        try:
            if (time.monotonic() - start_time) > measurement_interval:
                # get readings from sensors 
                lux_measuring()
                CO2_measuring()
                temperature_measuring()
                humidity_measuring()
                pressure_measuring()
                # time settings
                time_settings()
                # print to terminal
                terminal_print()
                # update the screen
                screen_update()
                # write to the sd card
                write_sd()
                adafruit_upload()
                start_time = time.monotonic()
                # set intervals at which readings should be taken
                # check lag in logging
        except:
                continue
    file.close()

