import xml.etree.ElementTree as ET

#from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp
import asyncio

from .enums import *


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


async def get_device(session, target_url, device_name):
    xml_payload_child = ET.Element("Config")
    xml_payload_child.text = "GetParam"
    xml_payload = construct_xml_status_request(device_name, xml_payload_child)

    results = await http_request(session, target_url, xml_payload)
    try:
        return ET.fromstring(results)
    except Exception:
        return ET.Element("Error")


async def get_zone_name(session, target_url, formal_zone_name):
    xml_payload_child = ET.Element("Rename")
    xml_payload_grandchild = ET.SubElement(xml_payload_child, "Rename_Latin_1")
    xml_payload_grandchild.text = "GetParam"

    xml_payload = construct_xml_status_request(formal_zone_name, xml_payload_child)
    results = await http_request(session, target_url, xml_payload)
    try:
        return ET.fromstring(results)
    except Exception:
        return ET.Element("Error")


async def get_zone_status(session, target_url, formal_zone_name):
    xml_payload_child = ET.Element("Basic_Status")
    xml_payload_child.text = "GetParam"

    xml_payload = construct_xml_status_request(formal_zone_name, xml_payload_child)

    results = await http_request(session, target_url, xml_payload)
    try:
        return ET.fromstring(results)
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
