import asyncio
import os

from building.parse_town_buildings import UpgradeBuilding
from building.parse_village_fields import BuildField
from credentials import VILLAGE_URL, TOWN_URL, ROME_ACTIVE
from send_troops import TroopsOrder
from logger import get_logger

logger = get_logger(__name__)

async def builders_manager(village_url, village_number):
    f = open(f'/tmp/BUILDINGS_QUEUE_{village_number}', 'w+')
    f.write(os.environ.get(f'BUILDINGS_QUEUE_{village_number}'))
    f.close()
    build_field = BuildField(VILLAGE_URL + village_url)
    upgrade_building = UpgradeBuilding(TOWN_URL + village_url, f'/tmp/BUILDINGS_QUEUE_{village_number}')
    loop = asyncio.get_event_loop()
    loop.create_task(upgrade_building())
    loop.create_task(build_field())
    loop.run_forever()

    # buildings_queue = os.environ.get(f'BUILDINGS_QUEUE_{village_number}')
    # if buildings_queue:
    #     os.environ[f'BUILDINGS_QUEUE_{village_number}'] = ''
    # buildings_queue = buildings_queue.split(',')
    # if '' in buildings_queue:
    #     buildings_queue.remove('')
    # if buildings_queue:
    #     buildings_queue = [building.strip() for building in buildings_queue]
    # await builder(village_url, buildings_queue)

# async def builder(village_special_url, buildings_queue):
    # build_field = BuildField(VILLAGE_URL + village_special_url)
    # if buildings_queue:
    #     upgrade_building = UpgradeBuilding(TOWN_URL + village_special_url, buildings_queue)
    #     if ROME_ACTIVE:
    #         await asyncio.gather(upgrade_building(), build_field())
    #     else:
    #         await asyncio.gather(upgrade_building())
    #
    # else:
    #     await asyncio.gather(build_field())


# def trooper():
#     with open('raids.txt', 'r') as f:
#
#         for line in f.readlines():
#             coords, time_of_next_raid = line.split(';')
#             coords = eval(coords)
#             asyncio.async(order(coords=coords, time_of_next_raid=time_of_next_raid))
#
#
# async def order(coords=None, time_of_next_raid=None):
#
#     order = TroopsOrder(barrack_url='https://ts7.travian.com/build.php?newdid=57154&id=39&tt=2&gid=16',
#                         coords=coords, time_of_next_raid=time_of_next_raid)
#     await order()


def main():
    # trooper()
    loop = asyncio.get_event_loop()
    village_number = 1
    url = os.environ.get(f'VILLAGE_URL_{village_number}')
    while url:
        loop.create_task(builders_manager(url, village_number))
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
