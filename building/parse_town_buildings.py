import re

from bs4 import BeautifulSoup

from .builder import Builder
from credentials import SERVER_URL
from logger import get_logger

logger = get_logger(__name__)

class UpgradeBuilding(Builder):
    """Build the list of buildings"""
    def __init__(self, town_page_url, queue):
        super().__init__(town_page_url)
        self.queue = list(queue)

    async def __call__(self, *args, **kwargs):
        """Build buildings until queue is not empty."""
        if self.queue:
            successfully_built = await super().__call__(*args, **kwargs)

            if successfully_built:
                del self.queue[0]

            await self.__call__()

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
        if not self.queue:
            return False
        building_to_build = self.queue[0]
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
