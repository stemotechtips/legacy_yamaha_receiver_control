# Todo: Make sure every XML 'findall' has a test for if len() is 0
# Todo: Handle missing zones / inputs / features
# Todo: Handle validity declarations / tests
# Todo: Make global timeout to all put requests after startup
# Todo: Implement tuner / net radio settings
# Todo: Better tests and safety features

import asyncio
from datetime import datetime
import xml.etree.ElementTree as ET

from .enums import *
from .helper_functions import *
from .protocol import *
import functools

ZONE_STARTUP_COOLDOWN = 5

async def get_receiver_details(http_session, ip_address):
    model_name, system_ID, firmware_version = await get_receiver(http_session, ip_address)

    if model_name is not None and system_ID is not None and firmware_version is not None:
        assert isinstance(model_name, str)
        assert isinstance(system_ID, str)
        assert isinstance(firmware_version, str)

        print(model_name)
        print(system_ID)
        print(firmware_version)

        return model_name, system_ID, firmware_version

    else:

        return None, None, None


class Receiver:

    def __init__(self, http_session, ip_address):
        """Initialise a receiver object without performing blocking network setup."""
        self.valid_setup = False
        self.http_session = http_session
        self.ip_address = ip_address
        self.model_name = ""
        self.system_ID = ""
        self.firmware_version = ""
        self.available_inputs = []
        self.available_audio_programs = []
        self.zones = []

    #Expose function that allows users to check whether IP address reveals a receiver
       

    async def initialise_receiver(self):
        """Create a receiver using the async HTTP helpers."""
        
        #self.model_name, self.system_ID, self.firmware_version = await get_receiver(self.http_session, self.ip_address)
        self.model_name, self.system_ID, self.firmware_version = await get_receiver_details(self.http_session, self.ip_address)

        if self.model_name is not None and self.model_name == "RX-V3900":
            self.valid_setup = True
            #[TO FIX] Currently this only returns true for the RX-V3900, but there is no reason why we couldn't extend this to the other models in the same family.
            
            await self.setup_devices()
            await self.setup_zones()
            await self.update_zones_statuses()
        
        return self

    async def setup_devices(self):
        
        self.analog_tuner = Device("Tuner")
        await self.analog_tuner.initialise_device(self)
        self.HD_tuner = Device("HD_Radio")
        await self.HD_tuner.initialise_device(self)
        self.sirius_tuner = Device("SIRIUS")
        await self.sirius_tuner.initialise_device(self)
        self.XM_tuner = Device("XM")
        await self.XM_tuner.initialise_device(self)

        # Currently these devices just silently fail - I can't work out how they initialise.
        self.ipod = Device("iPod")
        await self.ipod.initialise_device(self)
        self.rhapsody_tuner = Device("Rhapsody")
        #await self.rhapsody_tuner.initialise_device(self)
        self.bluetooth = Device("Bluetooth")
        await self.bluetooth.initialise_device(self)

        # once we have initialised the devices we populate a list of available inputs
        self.populate_inputs()
        self.populate_audio_programs()

    async def setup_zones(self):
        
        for zone_name in Zone_Names:
            zone = Zone(self, zone_name.value)
            await zone.initialise_zone(self)
            self.zones.append(zone)

    async def update_zones_statuses(self):
        results = await asyncio.gather(
            *(zone.async_update_zone_status(self) for zone in self.zones),
            return_exceptions=True,
        )
        failures = [
            zone.zone_name + ": " + str(result)
            for zone, result in zip(self.zones, results)
            if isinstance(result, Exception)
        ]
        if failures:
            raise RuntimeError("; ".join(failures))

    def populate_inputs(self):
        for input in Input_Type:
            if (
                input.name == Input_Type.SIRIUS.name
                or input.name == Input_Type.SIRIUS_2.name
            ):
                if self.sirius_tuner.exists:
                    self.available_inputs.append(input)
            elif input.name == Input_Type.TUNER.name:
                if self.analog_tuner.exists:
                    self.available_inputs.append(input)
            #Currently no way to include HD tuner? 

            elif input.name == Input_Type.XM.name:
                if self.XM_tuner.exists:
                    self.available_inputs.append(input)

            elif input.name == Input_Type.IPOD.name:
                if self.ipod.exists:
                    self.available_inputs.append(input)
            elif input.name == Input_Type.BTH.name:
                if self.bluetooth.exists:
                    self.available_inputs.append(input)

            elif input.name == Input_Type.RHAPSODY.name:
                if self.rhapsody_tuner.exists:
                    self.available_inputs.append(input)

            else:

                self.available_inputs.append(input)
        self.available_inputs.sort(key=functools.cmp_to_key(input_comparator))

    def populate_audio_programs(self):
        for program in Audio_Setting_Type:

            if program.name == Audio_Setting_Type.STEREO_NINECH.name or program.name == Audio_Setting_Type.ENHANCER_9CH.name:
                #These specific model names are built in to the Yamaha code, so we (probably) know that these are the only models that support 9 channels (in which case they are substituted for the 7 channel settings, as below).
                if self.model_name == "RX-Z7" or self.model_name == "DSP_Z7":
                    self.available_audio_programs.append(program)

            elif program.name == Audio_Setting_Type.STEREO_SEVENCH.name or program.name == Audio_Setting_Type.ENHANCER_7CH.name:
                #Again, these specific model names are built into the Yamaha code.
                if self.model_name != "RX-Z7" and self.model_name != "DSP_Z7":
                    self.available_audio_programs.append(program)

            else:
                self.available_audio_programs.append(program)
        self.available_audio_programs.sort(key=functools.cmp_to_key(audio_setting_comparator))

        #self.available_audio_programs.sort()

    async def change_zone_power(self, zone, desired_power_state):
        if isinstance(zone, Zone):
            await zone.change_zone_power(self, desired_power_state)
        else:
            print("Can only pass zone to this function!")

    async def change_zone_input(self, zone, desired_input):
        if desired_input in self.available_inputs:
            if isinstance(zone, Zone) and isinstance(desired_input, Input_Type):
                await zone.change_zone_input(self, desired_input)
                # print("Valid input!")
            else:
                print("Can only pass zone and valid input to this function!")

        else:
            print("Input not available: check device initialisation")

    async def change_zone_volume(self, zone, desired_volume):
        if isinstance(zone, Zone):
            await zone.change_zone_volume(self, desired_volume)
            # print("Valid input!")
        else:
            print("Can only pass zone and valid input to this function!")

    async def change_zone_mute(self, zone, desired_mute_state):
        if isinstance(zone, Zone) and isinstance(desired_mute_state, bool):
            await zone.change_zone_mute(self, desired_mute_state)

        else:
            print("Can only pass zone and valid input to this function!")

    async def change_zone_audio_setting(self, zone, desired_audio_program):

        if isinstance(zone, Zone) and isinstance(
            desired_audio_program, Audio_Setting_Type
        ):
            if zone.zone_name == "Main_Zone":

                await zone.change_zone_audio_setting(self, desired_audio_program)

            else:
                print("Only the main zone can have an audio program!")

        else:
            print("Can only pass zone and valid input to this function!")

    def print_all_details(self):
        self.print_receiver_details()
        self.print_devices_details()
        self.print_zone_details()
        self.print_available_inputs()

    def print_receiver_details(self):
        print("Details of receiver:")
        print("Model name is: " + self.model_name)
        print("System ID no. is: " + self.system_ID)
        print("Firmware version is: " + self.firmware_version)

    def print_devices_details(self):
        self.analog_tuner.print_device_details()
        self.HD_tuner.print_device_details()
        self.sirius_tuner.print_device_details()
        self.XM_tuner.print_device_details()
        self.ipod.print_device_details()
        self.rhapsody_tuner.print_device_details()
        self.bluetooth.print_device_details()

    def print_zone_details(self):
        for zone in self.zones:
            zone.print_details()

        # self.zone_four.print_details()

    def print_zone_details_fancy(self):
        headers = ("Zone", "Name", "Power", "Volume", "Mute", "Input", "Audio")
        rows = []

        for zone in self.zones:
            volume = getattr(zone, "volume_status", None)
            input_status = getattr(zone, "input_status", None)
            audio_program = getattr(zone, "audio_program", None)
            rows.append(
                (
                    zone.zone_name,
                    zone.friendly_name,
                    "On" if zone.is_on else "Standby",
                    (str(volume.volume_level) + volume.volume_unit) if volume else "-",
                    "On" if volume and volume.is_mute else "Off" if volume else "-",
                    input_status.selected_input.name if input_status else "-",
                    audio_program.program.name if audio_program else "-",
                )
            )

        widths = [max(len(str(row[index])) for row in (headers,) + tuple(rows)) for index in range(len(headers))]
        print("Zone details:")
        print("  ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers)))
        print("  ".join("-" * width for width in widths))
        for row in rows:
            print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))

    def print_available_inputs(self):
        print("Currently available inputs are: ")
        for input in self.available_inputs:
            print(input)

class Device:

    def __init__(self, device_name):
        """Initialise a device without a blocking network call."""
        self.device_name = device_name
        self.xml_response = None
        self.exists = False
        self.radios = []
        self.device_type = Device_Type.OTHER

    async def initialise_device(self, receiver):
        """Create a device using the async Yamaha protocol helper."""

#        if receiver is not None and isinstance(receiver, Receiver):
#            raise TypeError("Need to provide already instantiated Receiver System")

        self.exists = await get_device(receiver.http_session, receiver.ip_address, self.device_name)

        if self.exists and (self.device_name == "Tuner" or self.device_name == "HD_Radio"):
            #self.exists = False
            self.device_type = Device_Type.RADIO

            await self.setup_radios(receiver)


    async def setup_radios(self, receiver):
        #Radios not implemented yet
        if self.exists:
            radio_results = await get_radios(receiver.http_session, receiver.ip_address, self.device_name)
            # print(ET.tostring(radio_results))
            for radio_result in radio_results:
                #print(radio_result)
                radio_instance = Radio(radio_result.get("name"), radio_result.get("frequency_min"), 
                                       radio_result.get("frequency_max"), radio_result.get("decimals"), 
                                       radio_result.get("frequency_unit"), radio_result.get("frequency_step"))

                if radio_instance.valid_setup:
                    self.radios.append(radio_instance)
                else:
                    print("Invalid radio - not setting up")

        else:
            print("Tuner does not appear to be valid")

    def print_device_details(self):
        print("Device name is: " + self.device_name)
        if self.exists:
            print("Device exists")
            if self.device_type == Device_Type.RADIO:
                self.print_radio_details()
        else:
            print("Device does not exist")

    def print_radio_details(self):
        if self.device_type == Device_Type.RADIO and self.radios is not None:
            for radio in self.radios:
                if isinstance(radio, Radio):
                    radio.print_details()

                else:
                    print("Radio not instantiated correctly")

        else:
            print("No radios instantiated")

class Radio:

    def __init__(self, name, frequency_min, frequency_max, frequency_decimals, frequency_unit, frequency_step):
        # The idea is that we iterate through the radios provided in the 'tuner' XML, and then give each entity to
        # this function to instantiate them.  It assumes the root XML element is the "AM" or "FM", etc, element
        self.valid_setup = True
        #Currently we have no way of invalidating a radio setup...
        self.name = name
        self.frequency_min = frequency_min
        self.frequency_max = frequency_max
        self.frequency_decimals = frequency_decimals
        self.frequency_unit = frequency_unit
        self.frequency_step = frequency_step

        if not self.valid_setup:
            print("Help! Something went wrong!")

    def print_details(self):
        print("Name of radio is: " + self.name)
        print("Minimum frequency is: " + str(self.frequency_min))
        print("Maximum frequency is: " + str(self.frequency_max))
        print(
            "Frequency includes the following number of decimals: "
            + str(self.frequency_decimals)
        )
        print("Frequency increases by the following steps: " + str(self.frequency_step))
        print("Frequency is defined by the following units: " + self.frequency_unit)


class Zone:

    def __init__(self, receiver, zone_name):
        self.zone_name = zone_name
        self.zone_id = f"{receiver.system_ID}_{self.zone_name}"
        self.friendly_name = zone_name
        self.exists = True
        self.is_on = False
        self.volume_status = None
        self.input_status = None
        self.audio_program = None
        self.time_at_on = None

        if self.zone_name == "Main_Zone":
            self.available_audio_programs = receiver.available_audio_programs
        else:
            self.available_audio_programs = None

    async def initialise_zone(self, receiver):
        """Create a zone using async Yamaha network calls."""

        if not isinstance(receiver, Receiver):
            raise TypeError("Need to provide already instantiated Receiver System")

        friendly_name = await get_zone_name(
            receiver.http_session, receiver.ip_address, self.zone_name
        )
        if friendly_name != self.zone_name:
            self.friendly_name = friendly_name
            await self.async_update_zone_status(receiver)
        else:
            self.exists = False

    async def async_update_zone_status(self, receiver):
        if self.exists:
            if isinstance(receiver, Receiver):
                
                power_status_string, volume_xml, input_xml, audio_program_xml = await get_zone_status(
                    receiver.http_session, receiver.ip_address, self.zone_name
                )

                if power_status_string == "Standby":
                    self.is_on = False
                elif power_status_string == "On":
                    self.is_on = True
                    if self.time_at_on is None:
                        self.time_at_on = datetime.now()

                if len(volume_xml) != 0:
                    self.volume_status = Volume(volume_xml)

                if len(input_xml) != 0:
                    self.input_status = Input(input_xml, receiver.available_inputs)

                if audio_program_xml is not None:
                    self.audio_program = Audio_Program(audio_program_xml)


            else:
                print(
                    "Not instantiated correctly: Need to provide already instantiated Receiver System"
                )

        else:
            print("Help! Does not exist!")

    async def change_zone_power(self, receiver, desired_power_state):
        if isinstance(receiver, Receiver) and isinstance(desired_power_state, bool):
            if self.is_on == desired_power_state:
                print("Nothing to do - ignoring power change request")

            else:
                await self.wait_for_startup_cooldown()
                await toggle_zone_power(
                    receiver.http_session,
                    receiver.ip_address,
                    self.zone_name,
                    desired_power_state,
                )
                if desired_power_state:
                    self.time_at_on = datetime.now()

        else:
            print("Must provide Receiver System and valid input")

    async def change_zone_input(self, receiver, desired_input):
        if self.is_on:
            if isinstance(receiver, Receiver) and isinstance(desired_input, Input_Type):
                await self.wait_for_startup_cooldown()
                if not hasattr(self, "input_status") or self.input_status is None:
                    print("Zone input status not available")
                    return

                if self.input_status.selected_input == desired_input:
                    print("Nothing to do - ignoring input change request")

                else:
                    # print(
                    #    "Changing input from: "
                    #    + self.input_status.selected_input.name
                    #    + " to "
                    #    + desired_input.name
                    # )

                    await change_zone_input(
                        receiver.http_session,
                        receiver.ip_address,
                        self.zone_name,
                        desired_input,
                    )

            else:
                print("Must provide Receiver System and correctly formed input ")

        else:
            print("Zone must be on before we can switch inputs!")

    async def change_zone_volume(self, receiver, new_vol):
        if isinstance(receiver, Receiver):
            if self.is_on:
                await self.wait_for_startup_cooldown()
                if self.volume_status is not None:
                    self.volume_status.volume_level = new_vol
                    await update_volume(
                        receiver.http_session,
                        receiver.ip_address,
                        self.zone_name,
                        self.volume_status,
                    )
                else:
                    print("Zone volume status not available")
            else:
                print("Zone must be on before we can change volume!")

        else:
            print("Must provide Receiver System and correctly formed input ")

    async def change_zone_mute(self, receiver, new_mute_state):
        if isinstance(receiver, Receiver) and isinstance(new_mute_state, bool):
            if self.is_on:
                await self.wait_for_startup_cooldown()
                
                if self.volume_status is not None:
                    await update_zone_mute(
                        receiver.http_session, receiver.ip_address, self.zone_name, new_mute_state
                    )
            else:
                print("Zone must be on before we change mute!")

        else:
            print("Must provide Receiver System and correctly formed input ")

    async def change_zone_audio_setting(self, receiver, new_audio_program):
        if isinstance(receiver, Receiver) and isinstance(
            new_audio_program, Audio_Setting_Type
        ):
            if self.is_on:
                await self.wait_for_startup_cooldown()
                if not hasattr(self, "audio_program") or self.audio_program is None:
                    print("Zone audio program not available")
                    return
                await self.audio_program.change_zone_audio_setting(
                    receiver, self, new_audio_program
                )
            else:
                print("Zone must be on before we change audio program!")

        else:
            print("Must provide Receiver System and correctly formed input")

    async def wait_for_startup_cooldown(self):
        if self.time_at_on is None or self.is_on is False:
            return

        elapsed = (datetime.now() - self.time_at_on).total_seconds()
        remaining = ZONE_STARTUP_COOLDOWN - elapsed
        if remaining > 0:
            print(
                "Zone turned on too recently. Waiting "
                + str(round(remaining, 1))
                + " seconds"
            )
            await asyncio.sleep(remaining)

    def print_details(self):
        if self.exists:
            print("Zone details are:")
            print("Zone name is: " + self.zone_name)
            print("Zone friendly name is: " + self.friendly_name)
            print("Zone is currently on: " + str(self.is_on))
            if hasattr(self, "volume_status") and self.volume_status is not None and self.volume_status.valid_setup:
                self.volume_status.print_details()
            if hasattr(self, "input_status") and self.input_status is not None and self.input_status.valid_setup:
                self.input_status.print_details()

            if hasattr(self, "audio_program") and self.audio_program is not None and self.audio_program.valid_setup:
                self.audio_program.print_details()


class Volume:

    # We've hard coded these in - they are hardcoded in the javascript sent by the

    max_vol = 165
    min_vol = -805

    def __init__(self, vol_xml):
        self.valid_setup = True
        self.volume_level = return_int_if_numbers(
            vol_xml.findall("./Lvl/Val")[0].text.strip()
        )
        self.volume_decimals = return_int_if_numbers(
            vol_xml.findall("./Lvl/Exp")[0].text.strip()
        )

        if not isinstance(self.volume_level, int):
            self.valid_setup = False
            print(vol_xml.findall("./Lvl/Val")[0].text.strip())
            print("Something went wrong setting up volume level")

        # else:
        # print("Volume level valid!")
        # print(self.volume_level)

        if not isinstance(self.volume_decimals, int):
            self.valid_setup = False
            print("Something went wrong setting up volume decimal unit")

        self.volume_unit = vol_xml.findall("./Lvl/Unit")[0].text.strip()
        mute_string = vol_xml.findall("./Mute")[0].text.strip()
        if mute_string == "On":
            self.is_mute = True
        elif mute_string == "Off":
            self.is_mute = False
        else:
            self.valid_setup = False

        if not self.valid_setup:
            print("Help! Something went wrong setting up the volume entity!")

    async def change_zone_volume(self, receiver, zone, new_vol):
        if (
            isinstance(receiver, Receiver)
            and isinstance(zone, Zone)
            and isinstance(new_vol, int)
        ):
            if self.volume_level != new_vol:
                print(
                    "Changing volume in: "
                    + zone.friendly_name
                    + " from: "
                    + str(self.volume_level)
                    + " to "
                    + str(new_vol)
                    + str(self.volume_unit)
                )
                self.volume_level = new_vol
                await update_volume(
                    receiver.http_session, receiver.ip_address, zone.zone_name, self
                )

            else:
                print("Nothing to do: volume hasn't changed")

        else:
            print(
                "Not instantiated correctly: Need to provide already instantiated Receiver System and zone"
            )

    async def change_zone_mute(self, receiver, zone, new_mute_state):
        if (
            isinstance(receiver, Receiver)
            and isinstance(zone, Zone)
            and isinstance(new_mute_state, bool)
        ):
            if self.is_mute != new_mute_state:
                print(
                    "Changing mute state in: "
                    + zone.friendly_name
                    + " from: "
                    + str(self.is_mute)
                    + " to "
                    + str(new_mute_state)
                )
                self.is_mute = new_mute_state
                await update_zone_mute(
                    receiver.http_session, receiver.ip_address, zone.zone_name, self.is_mute
                )

            else:
                print("Nothing to do: mute state is the same.")

        else:
            print(
                "Not instantiated correctly: Need to provide already instantiated Receiver System and zone"
            )

    def display_volume(self):
        if isinstance(self.volume_level, int):
            division_factor = 10**self.volume_decimals

            friendly_volume = float(self.volume_level / division_factor)

            print(str(friendly_volume))
            # return friendly_volume

        else:
            print("Error!  Volume level is not int")

    def print_details(self):
        if self.valid_setup:
            print("Volume details:")
            print("Volume level is: " + str(self.volume_level))
            print(
                "Volume includes the following number of decimals: "
                + str(self.volume_decimals)
            )
            print("Volume unit is: " + self.volume_unit)
            print("Volume is muted: " + str(self.is_mute))
        else:
            print("Not valid!")


class Input:

    def __init__(self, input_xml, available_inputs):
        self.valid_setup = True
        self.selected_input = None
        asserted_input = Input_Type(input_xml.findall("./Input_Sel")[0].text)

        if Input_Type(asserted_input) in available_inputs:

            self.selected_input = asserted_input
            self.selected_input_title = input_xml.findall("./Input_Sel_Title")[0].text
            
        else:
            print("Help! Zone set to unavailable input")
            self.valid_setup = False

    def print_details(self):
        if self.valid_setup:
            print("Input details: ")
            print("Zone is currently set to: " + self.selected_input.name)
            print("Zone title is currently set to: " + self.selected_input_title)


class Audio_Program:
    valid_setup = True

    def __init__(self, audio_xml):
        straight_audio_string = audio_xml.findall("./Pgm_Sel/Straight")[0].text

        if straight_audio_string:
            self.straight_audio = True
        else:
            self.straight_audio = False

        self.program = Audio_Setting_Type(audio_xml.findall("./Pgm_Sel/Pgm")[0].text)

    async def change_zone_audio_setting(self, receiver, zone, new_audio_program):
        if (
            isinstance(receiver, Receiver)
            and isinstance(zone, Zone)
            and isinstance(new_audio_program, Audio_Setting_Type)
        ):
            if self.program != new_audio_program:
               # print(
               #     "Changing audio program in: "
               #     + zone.friendly_name
               #     + " from: "
               #    + self.program.value
               #     + " to "
               #     + new_audio_program.value
               # )
                self.program = new_audio_program
                await update_zone_audio_program(
                    receiver.http_session, receiver.ip_address, zone.zone_name, self.program
                )

            else:
                # print("Nothing to do: audio program is the same.")
                pass

        else:
            print(
                "Not instantiated correctly: Need to provide already instantiated Receiver System, zone and input"
            )

    def print_details(self):
        if self.valid_setup:
            print("Audio setting details: ")
            print("Straight is currently set to: " + str(self.straight_audio))
            print("Audio program is currently set to: " + self.program.name)
