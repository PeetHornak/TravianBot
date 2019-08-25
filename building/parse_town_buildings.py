import re

from bs4 import BeautifulSoup

from asyncio import sleep

from .builder import Builder
from credentials import SERVER_URL
from logger import info_logger_for_future_events, get_logger

logger = get_logger(__name__)

class UpgradeBuilding(Builder):
    """Build the list of buildings"""
    def __init__(self, town_page_url, queue_file):
        super().__init__(town_page_url)
        Builder.queue_file = queue_file
        Builder.queue = []
        super().load_queue()

    async def __call__(self, *args, **kwargs):
        """Build buildings until queue is not empty."""
        if Builder.queue:
            try:
                successfully_built = await super().__call__(*args, **kwargs)
                if successfully_built:
                    del Builder.queue[0]
            except Exception as e:
                msg = str(e).lower()
                logger.error(msg)
            finally:
                await self.__call__()

    async def dummy(self):
        await sleep(12)
        logger.info('BUILDING')

    def parse_buildings(self):
        """Return all buildings and related links"""
        buildings = self.parser_main_page.find_all(class_='good')
        buildings2 = self.parser_main_page.find_all(class_='notNow')
        buildings = list(set(buildings) | set(buildings2))
        building_links = {}
        for building in buildings:
            title_attr = building.get('title')
            name = title_attr.partition(" <span")[0]  # Gets the name of the building. I any language
            if not name:
                continue
            link = building.get('onclick').split("'")[1]
            building_links[name] = link

        return building_links

    def parse_not_built(self):
        buildings = self.parser_main_page.find_all(class_='g0')[:-3]
        if not buildings:
            return None
        link_to_be_build = buildings[0].get('class')
        building_links = {}
        for i in range(1,4):
            link_to_build = SERVER_URL + 'build.php?id=' + link_to_be_build[-2][-2:]+'&category={}'.format(i)
            page = self.session.get(link_to_build).text
            page = BeautifulSoup(page, 'html.parser')
            buildings = page.find(id='build')
            buildings = buildings.findChildren('div', class_='buildingWrapper', recursive=False)
            for building in buildings:
                name = building.h2.text
                building_links[name] = building

        return building_links

    def set_parser_location_to_build(self):
        if not Builder.queue:
            return False
        building_to_build = Builder.queue[0]
        building_sites = self.parse_buildings()

        # If given building was found then set parser, else try to find never building never built before.
        if building_to_build in building_sites:
            if building_sites[building_to_build] is None:
                return False
            link_to_building_field = SERVER_URL + building_sites[building_to_build]
            building_field_page = self.session.get(link_to_building_field).text

            self.parser_location_to_build = BeautifulSoup(building_field_page, 'html.parser')
            return True

        else:
            to_be_built = self.parse_not_built()
            if to_be_built is None:
                return -1
            if building_to_build in to_be_built:
                if to_be_built[building_to_build] is None:
                    return False
                self.parser_location_to_build = to_be_built[building_to_build]
                return True
            else:
                return -1

    async def parse_specific_seconds_build_left(self):
        parser = self.parser_main_page
        is_built = parser.find_all(class_='buildDuration')
        if not is_built:
            return 0
        second_left1 = is_built[0]
        building_name1 = second_left1.parent.find(class_='name').text

        if any(field in building_name1 for field in self.resources_dict.values()):
            second_left = None
        else:
            second_left = second_left1

        if len(is_built) > 1 and second_left is None:
            second_left2 = is_built[1]
            building_name2 = second_left2.parent.find(class_='name').text
            if any(field in building_name2 for field in self.resources_dict.values()):
                second_left = None
            else:
                second_left = second_left2

        # If found buildDuration class then return its value.
        #  Or there is no queue at all so we can build, return 0.
        if second_left:
            second_left = second_left.span.get('value')
            second_left = int(second_left)

            if second_left > 0:
                return second_left

            # Event-jam in travian. We can only wait.
            else:
                # 240 seconds to keep session alive.
                info_logger_for_future_events('Event jam. Waiting... Next attempt in ', 240)
                await sleep(240)
                self.set_parser_of_main_page()

                return await self.parse_seconds_build_left()

        return 0
