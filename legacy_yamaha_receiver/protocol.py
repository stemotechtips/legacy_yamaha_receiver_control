import xml.etree.ElementTree as ET
import asyncio

from enums import *
from helper_functions import *


def required_xml_element(xml_response, path):
    elements = xml_response.findall(path)
    if not elements:
        raise ValueError("receiver response is missing XML element: " + path)
    return elements[0]


def construct_xml_status_request(system, subelement_payload):
    root = ET.Element("YAMAHA_AV", cmd="GET")
    child = ET.SubElement(root, system)
    child.append(subelement_payload)

    return ET.tostring(root, encoding="utf-8", short_empty_elements=False).decode(
        "utf-8"
    )


def construct_xml_payload(system, subelement_payload):
    root = ET.Element("YAMAHA_AV", cmd="PUT")
    child = ET.SubElement(root, system)
    child.append(subelement_payload)

    return ET.tostring(root, encoding="utf-8", short_empty_elements=False).decode(
        "utf-8"
    )


async def http_request(session, target_url, xml_string):
    """Send an XML request to the Yamaha receiver without blocking the event loop."""
    #session = async_get_clientsession(hass)
    #session = aiohttp.ClientSession()
    async with session.post(target_url, data=xml_string, timeout=10) as response:
        response.raise_for_status()
        return await response.read()

async def get_receiver(session, target_url):

    xml_payload_child = ET.Element("Service_Info")
    xml_payload_child.text = "GetParam"
    xml_payload = construct_xml_status_request("System", xml_payload_child)
    results = await http_request(session, target_url, xml_payload)

    xml_response = ET.fromstring(results)

    model_name = required_xml_element(
        xml_response, "./System/Service_Info/Model_Name"
    ).text.strip()
    system_ID = required_xml_element(
        xml_response, "./System/Service_Info/System_ID"
    ).text.strip()
    firmware_version = required_xml_element(
        xml_response, "./System/Service_Info/Version/Main"
    ).text.strip()

    #need to return something if there's a failure.

    return model_name, system_ID, firmware_version

async def get_device(session, target_url, device_name):
    xml_payload_child = ET.Element("Config")
    xml_payload_child.text = "GetParam"
    xml_payload = construct_xml_status_request(device_name, xml_payload_child)

    results = await http_request(session, target_url, xml_payload)
    #print(results)
    xml_response = ET.fromstring(results)

    search_string = "./" + device_name + "/Config/Device"
    #print(search_string)
    xml_search = xml_response.findall(search_string)

    if len(xml_search) != 0 and xml_search[0].text == "Ready":
        return True
    else:
        return False

async def get_radios(session, target_url, device_name):

    xml_payload_child = ET.Element("Config")
    xml_payload_child.text = "GetParam"
    xml_payload = construct_xml_status_request(device_name, xml_payload_child)

    results = await http_request(session, target_url, xml_payload)
    xml_response = ET.fromstring(results)

    xml_results = xml_response.findall("./Tuner/Config/Range_and_Step/*")

    radios_details = []

    for radio_xml in xml_results:
        valid_setup = True
        name = radio_xml.tag
        frequency_min = return_int_if_numbers(
            radio_xml.findall("./Min/Val")[0].text.strip()
        )
        frequency_decimals = return_int_if_numbers(
            radio_xml.findall("./Min/Exp")[0].text.strip()
        )
        frequency_unit = radio_xml.findall("./Min/Unit")[0].text.strip()
        frequency_max = return_int_if_numbers(
            radio_xml.findall("./Max/Val")[0].text.strip()
        )
        frequency_step = return_int_if_numbers(
            radio_xml.findall("./Step/Val")[0].text.strip()
        )

        if (
            isinstance(frequency_min, int)
            and isinstance(frequency_decimals, int)
            and isinstance(frequency_max, int)
            and isinstance(frequency_step, int)
        ):
            valid_setup = False

        if frequency_decimals != return_int_if_numbers(
            radio_xml.findall("./Max/Exp")[0].text.strip()
        ) or frequency_decimals != return_int_if_numbers(
            radio_xml.findall("./Step/Exp")[0].text.strip()
        ):
            print("Warning: Inconsistent details for frequency decimals")
            print(frequency_decimals)
            print(
                return_int_if_numbers(radio_xml.findall("./Max/Exp")[0].text.strip())
            )
            print(
                return_int_if_numbers(
                    radio_xml.findall("./Step/Exp")[0].text.strip()
                )
            )

        if (
            frequency_unit != radio_xml.findall("./Max/Unit")[0].text.strip()
            or frequency_unit
            != radio_xml.findall("./Step/Unit")[0].text.strip()
        ):
            print("Warning: Inconsistent details provided for frequency units")

        if valid_setup:

            radio = {

                "name": name,
                "frequency_min": frequency_min,
                "frequency_max": frequency_max,
                "frequency_decimals": frequency_decimals,
                "frequency_unit": frequency_unit,
                "frequency_step": frequency_step,
            }

            radios_details.append(radio)

    return radios_details    

async def get_zone_name(session, target_url, formal_zone_name):
    xml_payload_child = ET.Element("Rename")
    xml_payload_grandchild = ET.SubElement(xml_payload_child, "Rename_Latin_1")
    xml_payload_grandchild.text = "GetParam"

    xml_payload = construct_xml_status_request(formal_zone_name, xml_payload_child)
    results = await http_request(session, target_url, xml_payload)
    xml_response = ET.fromstring(results)

    search_string_template = "./" + formal_zone_name
    friendly_name_search_string = search_string_template + "/Rename/Rename_Latin_1"
    friendly_name = xml_response.find(friendly_name_search_string)

    try:
        return friendly_name.text.strip()
    except Exception:
        return ET.Element("Error")


async def get_zone_status(session, target_url, formal_zone_name):
    xml_payload_child = ET.Element("Basic_Status")
    xml_payload_child.text = "GetParam"

    xml_payload = construct_xml_status_request(formal_zone_name, xml_payload_child)

    results = await http_request(session, target_url, xml_payload)
    xml_response = ET.fromstring(results)
    search_string_template = "./" + formal_zone_name
    power_status_search_string = (
    search_string_template + "/Basic_Status/Power_Control/Power"
    )
    power_status_string = xml_response.findall(power_status_search_string)[
        0
    ].text.strip()

    vol_string = search_string_template + "/Basic_Status/Vol"
    vol_xml_all = xml_response.findall(vol_string)
    vol_xml = vol_xml_all[0]

    input_search_string = search_string_template + "/Basic_Status/Input"
    input_xml_all = xml_response.findall(input_search_string)
    input_string = input_xml_all[0]

    audio_search_string = search_string_template + "/Basic_Status/Surr"
    audio_program_xml_all = xml_response.findall(audio_search_string)

    if len(audio_program_xml_all) != 0:

        audio_program_xml = audio_program_xml_all[0]
    else:
        audio_program_xml = None
    
    try:
        return power_status_string, vol_xml, input_string, audio_program_xml
        
    except Exception:
        return ET.Element("Error")


async def toggle_zone_power(session, target_url, formal_zone_name, turn_on):
    xml_payload_child = ET.Element("Power_Control")
    xml_payload_grandchild = ET.SubElement(xml_payload_child, "Power")
    if turn_on:
        xml_payload_grandchild.text = "On"
    elif not turn_on:
        xml_payload_grandchild.text = "Standby"
    else:
        raise Exception

    xml_payload = construct_xml_payload(formal_zone_name, xml_payload_child)
    await http_request(session, target_url, xml_payload)


async def change_zone_input(session, target_url, formal_zone_name, target_input):
    xml_payload_child = ET.Element("Input")
    xml_payload_grandchild = ET.SubElement(xml_payload_child, "Input_Sel")

    if isinstance(target_input, Input_Type):
        xml_payload_grandchild.text = target_input.value
        xml_payload = construct_xml_payload(formal_zone_name, xml_payload_child)
        await http_request(session, target_url, xml_payload)
    else:
        raise Exception


async def update_volume(session, target_url, formal_zone_name, volume):
    xml_payload_child = ET.Element("Vol")
    xml_payload_grandchild = ET.SubElement(xml_payload_child, "Lvl")

    xml_payload_vol = ET.SubElement(xml_payload_grandchild, "Val")
    xml_payload_vol.text = str(volume.volume_level)
    xml_payload_exp = ET.SubElement(xml_payload_grandchild, "Exp")
    xml_payload_exp.text = str(volume.volume_decimals)
    xml_payload_unit = ET.SubElement(xml_payload_grandchild, "Unit")
    xml_payload_unit.text = volume.volume_unit

    xml_payload = construct_xml_payload(formal_zone_name, xml_payload_child)
    await http_request(session, target_url, xml_payload)


async def update_zone_mute(session, target_url, formal_zone_name, mute_on):
    if isinstance(mute_on, bool):
        xml_payload_child = ET.Element("Vol")
        xml_payload_grandchild = ET.SubElement(xml_payload_child, "Mute")

        if mute_on:
            xml_payload_grandchild.text = "On"
        elif not mute_on:
            xml_payload_grandchild.text = "Off"

        xml_payload = construct_xml_payload(formal_zone_name, xml_payload_child)
        await http_request(session, target_url, xml_payload)
    else:
        raise Exception


async def update_zone_audio_program(session, target_url, formal_zone_name, audio_program):
    if isinstance(audio_program, Audio_Setting_Type):
        xml_payload_child = ET.Element("Surr")
        xml_payload_grandchild = ET.SubElement(xml_payload_child, "Pgm_Sel")
        xml_payload_great_grandchild_straight = ET.SubElement(
            xml_payload_grandchild, "Straight"
        )

        if audio_program != Audio_Setting_Type.STRAIGHT:
            xml_payload_great_grandchild_straight.text = "Off"
            xml_payload_great_grandchild_pgm = ET.SubElement(
                xml_payload_grandchild, "Pgm"
            )
            xml_payload_great_grandchild_pgm.text = audio_program.value
        elif audio_program == Audio_Setting_Type.STRAIGHT:
            xml_payload_great_grandchild_straight.text = "On"
        xml_payload = construct_xml_payload(formal_zone_name, xml_payload_child)
        await http_request(session, target_url, xml_payload)
    else:
        raise Exception
