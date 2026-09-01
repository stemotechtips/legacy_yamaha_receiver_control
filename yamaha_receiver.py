from receiver_system import Receiver
import asyncio
import aiohttp

target_url = "http://192.168.1.31/YamahaRemoteControl/ctrl"

async def main():

    async with aiohttp.ClientSession() as hass:
        system_test = await Receiver.async_create(hass, target_url)


    system_test.print_all_details()

asyncio.run(main())