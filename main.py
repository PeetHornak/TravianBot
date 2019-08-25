import asyncio
import os

from building.parse_town_buildings import UpgradeBuilding
from building.parse_village_fields import BuildField
from credentials import VILLAGE_URL, TOWN_URL, SERVER_URL
from send_troops import TroopsOrder
from logger import get_logger

logger = get_logger(__name__)

async def builders_manager(village_url, village_number):
    f = open(f'/tmp/BUILDINGS_QUEUE_{village_number}', 'w+')
    f.write(os.environ.get(f'BUILDINGS_QUEUE_{village_number}'))
    f.close()
    build_field = BuildField(VILLAGE_URL + village_url)
    upgrade_building = UpgradeBuilding(TOWN_URL + village_url, f'/tmp/BUILDINGS_QUEUE_{village_number}')
    while True:
        await asyncio.gather(upgrade_building(), build_field())
    # loop = asyncio.get_event_loop()
    # loop.create_task(upgrade_building())
    # loop.create_task(build_field())
    # loop.run_forever()


async def troop_raid(url, village_number):
    open(f'/tmp/RAIDS_{village_number}', 'w+').close()
    send_troops = TroopsOrder(SERVER_URL + 'build.php' + url + 'id=39&tt=2&gid=16', village_number)
    while True:
        await send_troops()


def main():
    loop = asyncio.get_event_loop()
    village_number = 1
    url = os.environ.get(f'VILLAGE_URL_{village_number}')
    while url:
        loop.create_task(builders_manager(url, village_number))
        loop.create_task(troop_raid(url, village_number))
        village_number += 1
        url = os.environ.get(f'VILLAGE_URL_{village_number}')

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()
    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    main()
