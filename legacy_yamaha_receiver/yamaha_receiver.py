import asyncio
import argparse
import aiohttp
from contextlib import suppress
from io import StringIO
from contextlib import redirect_stderr
import sys
from urllib.parse import urlsplit, urlunsplit

from .enums import Audio_Setting_Type, Input_Type, Zone_Names
from .receiver_system import Receiver

CONTROL_PATH = "/YamahaRemoteControl/ctrl"
STATUS_UPDATE_INTERVAL = 10
INITIALISATION_ATTEMPTS = 3
INITIALISATION_TIMEOUT = 5
INITIALISATION_RETRY_DELAY = 1


def target_url(address):
    """Return the Yamaha control endpoint for a host or URL."""
    address = address.strip()
    if "://" not in address:
        address = "http://" + address

    parsed = urlsplit(address)
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        path = CONTROL_PATH
    elif not path.endswith(CONTROL_PATH):
        path += CONTROL_PATH

    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def zone_for(receiver, name):
    try:
        zone_name = Zone_Names[name.lower()].value
    except KeyError:
        valid_names = ", ".join(zone.name for zone in Zone_Names)
        raise ValueError("unknown zone " + name + "; choose from: " + valid_names)

    for zone in receiver.zones:
        if zone.zone_name == zone_name:
            return zone

    raise ValueError("zone is not available: " + name)


def enum_value(enum_type, name):
    try:
        return enum_type[name.upper()]
    except KeyError:
        valid_names = ", ".join(item.name for item in enum_type)
        raise ValueError("unknown value " + name + "; choose from: " + valid_names)


def boolean_value(value):
    normalized = value.lower()
    if normalized in ("on", "true", "yes"):
        return True
    if normalized in ("off", "false", "no"):
        return False
    raise ValueError("expected on or off, got " + value)


def build_parser():
    parser = argparse.ArgumentParser(description="Control a Yamaha receiver.")
    parser.add_argument("address", nargs="?", help="receiver IP address or control URL")
    subparsers = parser.add_subparsers(dest="command")

    for command in ("help", "status", "receiver-details", "zones", "inputs"):
        subparsers.add_parser(command)

    power = subparsers.add_parser("power", help="turn a zone on or off")
    power.add_argument("zone", choices=[zone_name.name for zone_name in Zone_Names])
    power.add_argument("state", choices=("on", "off"))

    input_command = subparsers.add_parser("input", help="select a zone input")
    input_command.add_argument("zone", choices=[zone_name.name for zone_name in Zone_Names])
    input_command.add_argument("input")

    volume = subparsers.add_parser("volume", help="set a zone volume level")
    volume.add_argument("zone", choices=[zone_name.name for zone_name in Zone_Names])
    volume.add_argument("level", type=int)

    mute = subparsers.add_parser("mute", help="mute or unmute a zone")
    mute.add_argument("zone", choices=[zone_name.name for zone_name in Zone_Names])
    mute.add_argument("state", choices=("on", "off"))

    audio = subparsers.add_parser("audio", help="set the main-zone audio program")
    audio.add_argument("zone", choices=("main",))
    audio.add_argument("program")

    return parser


def print_help(parser=None):
    if parser is not None:
        parser.print_help()
        return

    print("Available commands:")
    print("  status                        Show all receiver details")
    print("  receiver-details              Show receiver details")
    print("  zones                         Show zone details")
    print("  inputs                        Show available inputs")
    print("  power <zone> <on|off>         Turn a zone on or off")
    print("  input <zone> <input>          Select an input")
    print("  volume <zone> <level>         Set the volume level")
    print("  mute <zone> <on|off>          Mute or unmute a zone")
    print("  audio main <program>          Set the main-zone audio program")
    print("  help                          Show this command list")
    print("  quit                          Exit the interactive session")


async def run_command(receiver, arguments):
    command = arguments.command or "status"
    if command in ("status", "zones"):
        await refresh_zone_statuses(receiver)

    if command == "help":
        print_help()
    elif command == "status":
        receiver.print_all_details()
    elif command == "receiver-details":
        receiver.print_receiver_details()
    elif command == "zones":
        receiver.print_zone_details_fancy()
    elif command == "inputs":
        receiver.print_available_inputs()
    elif command == "power":
        await receiver.change_zone_power(zone_for(receiver, arguments.zone), boolean_value(arguments.state))
    elif command == "input":
        await receiver.change_zone_input(
            zone_for(receiver, arguments.zone), enum_value(Input_Type, arguments.input)
        )
    elif command == "volume":
        await receiver.change_zone_volume(zone_for(receiver, arguments.zone), arguments.level)
    elif command == "mute":
        await receiver.change_zone_mute(zone_for(receiver, arguments.zone), boolean_value(arguments.state))
    elif command == "audio":
        await receiver.change_zone_audio_setting(
            zone_for(receiver, arguments.zone), enum_value(Audio_Setting_Type, arguments.program)
        )

    if command not in ("help", "status", "zones"):
        await refresh_zone_statuses(receiver)


async def refresh_zone_statuses(receiver):
    try:
        await receiver.update_zones_statuses()
    except Exception as error:
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            detail = "timeout"
        else:
            detail = error.__class__.__name__ + ": " + (str(error) or "no details")
        print("Status update failed: " + detail)


async def initialise_receiver(http_session, address):
    last_error = "receiver did not report a valid setup"
    for attempt in range(INITIALISATION_ATTEMPTS):
        print("Attempting to initialise...")
        try:
            receiver = await asyncio.wait_for(
                Receiver.async_create(http_session, address),
                timeout=INITIALISATION_TIMEOUT,
            )
            if receiver.valid_setup:
                print("Success!  Valid receiver setup detected")
                return receiver
            print("Invalid setup")
        except Exception as error:
            if isinstance(error, asyncio.TimeoutError):
                print("Timeout")
            else:
                print("Invalid setup")
            last_error = str(error) or error.__class__.__name__

        if attempt < INITIALISATION_ATTEMPTS - 1:
            await asyncio.sleep(INITIALISATION_RETRY_DELAY)

    raise RuntimeError(
        "Could not initialise a valid receiver after "
        + str(INITIALISATION_ATTEMPTS)
        + " attempts: "
        + last_error
    )


def prompt_address():
    return input("Receiver IP address or URL: ").strip()


async def interactive_session(receiver, parser, address):
    print_help()
    async def update_statuses_periodically():
        while True:
            started_at = asyncio.get_running_loop().time()
            await refresh_zone_statuses(receiver)
            elapsed = asyncio.get_running_loop().time() - started_at
            await asyncio.sleep(max(0, STATUS_UPDATE_INTERVAL - elapsed))

    status_update_task = asyncio.create_task(update_statuses_periodically())
    try:
        while True:
            line = (await asyncio.to_thread(input, "yamaha> ")).strip()
            if line.lower() in ("quit", "exit"):
                return
            if not line:
                continue
            if line.lower() == "help":
                print_help()
                continue
            try:
                with redirect_stderr(StringIO()):
                    command_arguments = parser.parse_args([address] + line.split())
                await run_command(receiver, command_arguments)
            except (SystemExit, ValueError):
                print("Command not recognized: " + line)
                print_help()
    finally:
        status_update_task.cancel()
        with suppress(asyncio.CancelledError):
            await status_update_task


async def main(arguments=None):
    parser = build_parser()
    if arguments is None:
        command_line = sys.argv[1:]
        if len(command_line) == 1 and not command_line[0].startswith("-"):
            arguments = argparse.Namespace(address=command_line[0], command=None)
        else:
            arguments = parser.parse_args(command_line)

    interactive = arguments.command is None
    if arguments.address is None:
        address = prompt_address()
    else:
        address = arguments.address

    async with aiohttp.ClientSession() as http_session:
        try:
            receiver = await initialise_receiver(http_session, target_url(address))
        except RuntimeError as error:
            raise SystemExit("Error: " + str(error))
        if interactive:
            await interactive_session(receiver, parser, address)
        else:
            await run_command(receiver, arguments)


def cli():
    try:
        asyncio.run(main())
    except ValueError as error:
        raise SystemExit("Error: " + str(error))


if __name__ == "__main__":
    cli()