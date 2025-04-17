# Circuitpython code for biofilm cell factory
# Monitoring 2 CO2 sensors, lux sensor, LED light function, an RTC, and screen displaying collected data
# IoT connection to adafruitio to access data on adafruitio
# Refactored for OOP
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

# Define constants 
Reading_interval = 30
I2C_SDA_PIN = board.GP5
I2C_SCL_PIN = board.GP4
I2C_SDA_PIN_2 = board.GP27
I2C_SCL_PIN_2 = board.GP26
LED_PIN = board.GP2
LED_PIN_2 = board.GP7
WIFI_RX_PIN = board.GP17
WIFI_TX_PIN = board.GP16
OLED_RESET_PIN = board.GP20
SD_CS_PIN = board.GP15
SD_SCK_PIN = board.GP10
SD_MOSI_PIN = board.GP11
SD_MISO_PIN = board.GP12
Display_width = 128
Display_height = 64
Display_border = 0
displayio.release_displays()

class Biofilm_Measure:
    def __init__(self):
        self.setup_i2c()
        self.setup_sensors()
        self.setup_leds()
        self.setup_wifi()
        self.setup_adafruit_io()
        self.setup_rtc()
        self.setup_SD()
        self.setup_display()

        self.ambient_CO2_list = []
        self.start_time = time.monotonic()
        self.error_dict = {
            "lux_start": 0, "lux_end": 0, "ambient_co2": 0, 
            "system_co2": 0, "temp": 0, "humidity": 0, "pressure": 0
        }

    def setup_i2c(self): 
        self.i2c = busio.I2C(I2C_SDA_PIN, I2C_SCL_PIN)
        self.i2c2 = busio.I2C(I2C_SDA_PIN_2, I2C_SCL_PIN_2)

    def setup_sensors(self):
        self.dps310 = DPS310(self.i2c)
        self.scd_ambient = adafruit_scd30.SCD30(self.i2c)
        self.scd_system = adafruit_scd30.SCD30(self.i2c2)
        self.veml7700_start = adafruit_veml7700.VEML7700(self.i2c)
        self.veml7700_end  = adafruit_veml7700.VEML7700(self.i2c2)

    def setup_leds(self):
        self.led1 = digitalio.DigitalInOut(LED_PIN)
        self.led1.direction = digitalio.Direction.OUTPUT
        self.led2 = digitalio.DigitalInOut(LED_PIN_2)
        self.led2.direction = digitalio.Direction.OUTPUT

    def setup_wifi(self):
        uart = busio.UART(WIFI_TX_PIN, WIFI_RX_PIN, receiver_buffer_size=2048)
        self.esp = adafruit_espatcontrol.ESP_ATcontrol(uart, 115200, debug=False)
        self.wifi = adafruit_espatcontrol_wifimanager.ESPAT_WiFiManager(self.esp, secrets)
        print("WiFi connected")
        
    def connected(client):
        print("Connected to Adafruit IO! ")

    def subscribe(client, userdata, topic, granted_qos):
        print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

    def disconnected(client):
        print("Disconnected from Adafruit IO!")

    def on_msg(client, topic, message):
        # Method called whenever feeds has a new value
        print("New message on topic {0}: {1} ".format(topic, message))

    def setup_adafruit_io(self):
        MQTT.set_socket(socket, self.esp)
        mqtt_client = MQTT.MQTT(
            broker = "io.adafruit.com",
            username = secrets["aio_username"], 
            password = secrets["aio_key"]
        )
        self.io = IO_MQTT(mqtt_client)
        self.io.connect()
        for feed_id in ["CO2", "Lux-start", "Lux-end"]:
            self.io.subscribe(feed_id)

    def setup_rtc(self):
        self.rtc = DS3231(self.i2c)
        if self.rtc.lost_power:
            self.rtc.datetime = time.struct_time((2000, 4, 25, 12, 0, 0, 0, -1, -1))
            print("RTC lost power")

    def setup_SD(self):
        spi  = busio.SPI(SD_SCK_PIN, MOSI=SD_MOSI_PIN, MISO=SD_MISO_PIN)
        sd = sdcardio.SDCard(spi, SD_CS_PIN)
        vfs = storage.VfsFat(sd)
        storage.mount(vfs, "/sd")
        current_file_time = self.rtc.datetime
        self.filename = "{:04}-{:02}-{:02},{:02}-{:02}-{:02}".format(
            current_file_time.tm_year, current_file_time.tm_mon, current_file_time.tm_mday,
            current_file_time.tm_hour, current_file_time.tm_min, current_file_time.tm_sec)

    def setup_display(self):
        displayio.release_displays()
        display_bus = displayio.I2CDisplay(self.i2c, device_address=0x3C, reset=OLED_RESET_PIN)
        self.display = adafruit_displayio_ssd1306.SSD1306(
            display_bus, width=Display_width, height=Display_height)
        self.setup_display_group()

    def setup_display_group(self):
        self.splash = displayio.Group()
        self.display.show(self.splash)
        self.setup_display_background()
        self.setup_display_labels()

    def setup_display_background(self):
        colour_bitmap = displayio.Bitmap(Display_width, Display_height, 1)
        colour_palette  = displayio.Palette(1)
        colour_palette[0] = 0xFFFFFF # White=0xFFFFFF
        bg_sprite = displayio.TileGrid(colour_bitmap, pixel_shader=colour_palette, x=0, y=0)
        self.splash.append(bg_sprite)

        inner_bitmap = displayio.Bitmap(Display_width - Display_border * 2, Display_height - Display_border * 2, 1)
        inner_palette = displayio.Palette(1)
        inner_palette[0] = 0x000000 #Black=0x000000
        inner_sprite  = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=Display_border, y=Display_border)
        self.splash.append(inner_sprite)

    def setup_display_labels(self):
        self.text_labels = [
            self.create_label("Lux start:", 0, 4),
            self.create_label("Luxend:", 0, 15),
            self.create_label("Ambient CO2:", 0, 26),
            self.create_label("System CO2:", 0, 37),
            self.create_label("Biofilm CO2:", 0, 48),
            self.create_label("Temperature:", 0, 59)
        ]

        self.number_labels  = [
            self.create_label("0", 70, 4),
            self.create_label("0", 75, 15),
            self.create_label("0", 80, 26),
            self.create_label("0", 75, 37),
            self.create_label("0", 75, 48),
            self.create_label("0", 75, 48),
            self.create_label("0", 75, 59)
        ]

    def create_label(self, text: str, x: int, y: int) -> label.Label:
        lbl = label.Label(terminalio.FONT, text=text, color=0xFFFFFF, x=x, y=y)
        self.splash.append(lbl)
        return lbl
    
    def create_filename(self) -> str:
        current_time = self.rtc.datetime
        return "{:04}-{:02}-{:02},{:02}-{:02}-{:02}".format(
            current_time.tm_year, current_time.tm_mon, current_time.tm_mday,
            current_time.tm_hour, current_time.tm_min, current_time.tm_sec)
    
    def measure_lux_start(self) -> tuple[float]:
        self.led1.value = True
        try:
            return self.veml7700_start.lux
        except Exception as e:
            print(f"Error measuring start lux: {e}")
            self.error_dict["lux_start"] += 1
            return 0.0

    def measure_lux_end(self) -> tuple[float]:
        self.led2.value = True
        try:
            return self.veml7700_end.lux
        except Exception as e:
            print(f"Error measuring end lux: {e}")
            self.error_dict["lux_end"] += 1
            return 0.0
        
    
    def measure_CO2(self) -> tuple[float, float, float]:
        try:
            ambient_CO2 = self.scd_ambient.CO2
            self.ambient_CO2_list.append(ambient_CO2)
            system_CO2 = self.scd_system.CO2
            biofilm_CO2 = system_CO2  - ambient_CO2

            if len(self.ambient_CO2_list) == 16:
                actual_ambient = self.ambient_CO2_list.pop(0)
                biofilm_CO2 = system_CO2 - actual_ambient
            return ambient_CO2, system_CO2, biofilm_CO2
        except Exception as e:
            print(f"Error measuring CO2: {e}")
            self.error_dict["ambient_CO2"] += 1
            self.error_dict["system_CO2"] += 1
            return 0.0, 0.0, 0.0
        
    def measure_temperature(self) -> float:
        try:
            return self.dps310.temperature
        except Exception as e:
            print(f"Error measuring temperature: {e}")
            self.error_dict["temperature"] += 1
            return 0.0
        
    def measure_humidity(self) -> float:
        try:
            return self.scd_system.relative_humidity
        except Exception as e:
            print(f"Error reading humidity: {e}")
            self.error_dict["humidity"] += 1
            return 0.0
        
    def measure_pressure(self) -> float:
        try:
            return self.dps310.pressure
        except Exception as e:
            print(f"Error measuring pressure: {e}")
            self.error_dict["pressure"] += 1
            return 0.0
        
    def get_timestamp(self) -> tuple[float, str]:
        elapsed_time = time.monotonic() - self.start_time
        current_time = self.rtc.datetime
        timestamp = "{:04}-{:02}-{:02}, {:02}:{:02}:{:02}".format(
            current_time.tm_year, current_time.tm_mon, current_time.tm_mday,
            current_time.tm_hour, current_time.tm_min, current_time.tm_sec)
        return elapsed_time, timestamp
    
    def print_data(self, data: dict[str, float], timestamp: str):
        print(f"Time stamp: {timestamp}")
        print(f"Lux start: {data['lux_start']:.2f}")
        print(f"Lux end: {data['lux_end']:.2f}")
        print(f"Ambient CO2: {data['ambient_co2']:.2f}")
        print(f"System CO2: {data['system_co2']:.2f}")
        print(f"Biofilm CO2: {data['biofilm_co2']:.2f}")
        print(f"Temperature: {data['temperature']:.2f}")
        print(f"Humidity: {data['humidity']:.2f}")
        print(f"Pressure: {data['pressure']:.2f}")

    def update_display(self, data: dict[str, float]):
        self.number_labels[0].text = f"{data['lux_start']:.0f}"
        self.number_labels[1].text = f"{data['lux_end']:.0f}"
        self.number_labels[2].text = f"{data['ambient_co2']:.0f}"
        self.number_labels[3].text = f"{data['system_co2']:.0f}"
        self.number_labels[4].text = f"{data['biofilm_co2']:.2f}"
        self.number_labels[5].text = f"{data['temperature']:.2f}"

    def write_sd(self, data: dict[str, float], timestamp: str, elapsed_time: float):
        try:
            with open(f"/sd/{self.filename}.csv", "a") as file:
                data_string = f"{timestamp},{elapsed_time:.2f},{data['lux_start']:.2f},{data['lux_end']:.2f},{data['ambient_co2']:.2f},{data['system_co2']:.2f},{data['biofilm_co2']:.2f},{data['temperature']:.2f},{data['humidity']:.2f},{data['pressure']:.2f},{self.error_dict}\n"
                file.write(data_string)
        except Exception as e:
            print(f"Error writing to sd card: {e}")
    
    def adafruitio_upload(self, data: dict[str, float]):
        try:
            self.io.publish("CO2", data['biofilm_co2'])
            self.io.publish("Lux-start", data['lux_start'])
            self.io.publish("Lux-end", data['lux_end'])
        except Exception as e:
            print(f"Falied Adafruitio upload")
            try:
                self.wifi.reset()
                self.io.reconnect()
                self.io.publish("CO2", data['biofilm_co2'])
                self.io.publish("Lux-start", data['lux_start'])
                self.io.publish("Lux-end", data['lux_end'])
                print(f"Publish retry successful")
            except Exception as e:
                print(f"Failed retry")


    def main_loop(self):
        previous_reading_time = time.monotonic()
        while True:
            try:
                current_time  = time.monotonic()
                if (current_time - previous_reading_time) >= Reading_interval:
                    data = self.collect_data()    
                    elapsed_time, timestamp = self.get_timestamp()
                    self.print_data(data, timestamp)
                    self.update_display(data)
                    self.write_sd(data, timestamp, elapsed_time)
                    self.adafruitio_upload(data)

                    previous_reading_time = current_time
                    self.io.loop(0.1)

            except Exception as e:
                print(e)
                continue

    def collect_data(self) -> dict[str, float]:
        lux_start, lux_end = self.measure_lux_start(), self.measure_lux_end()
        ambient_co2, system_co2, biofilm_co2 = self.measure_CO2()
        temperature  = self.measure_temperature()
        humidity = self.measure_humidity()
        pressure = self.measure_pressure()

        return {
                'lux_start': lux_start,
                'lux_end': lux_end,
                'ambient_co2': ambient_co2,
                'system_co2': system_co2,
                'biofilm_co2': biofilm_co2,
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure        
        }
    
biofilm_monitor = Biofilm_Measure()
biofilm_monitor.main_loop()
