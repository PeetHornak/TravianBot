import re

from abc import ABC, abstractmethod
from asyncio import sleep
from random import randint

from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from check_adventure import check_adventure
from authorization import logged_in_session
from credentials import SERVER_URL, ROME_ACTIVE
from logger import info_logger_for_future_events, get_logger

logger = get_logger(__name__)

class Builder(ABC):

    queue = []
    queue_file = None
    resources_dict = {
        'Dřevo': 'Dřevorubec',
        'Železo': 'Železný důl',
        'Hlína': 'Hliněný důl',
        'Obilí': 'Obilné pole'
    }
    """Extendable class for building"""
    def __init__(self, main_page_url):
        self.main_page_url = main_page_url
        self.parser_location_to_build = None
        self.parser_main_page = None
        self.session = None

    async def __call__(self, *args, **kwargs):
        self.load_queue()
        self.session = logged_in_session()
        self.set_parser_of_main_page()
        check_adventure(self.session, self.parser_main_page)
        if not await self.check_queue():
            return False
        result = self.set_parser_location_to_build()
        if not result:
            info_logger_for_future_events('Could not find location to build, waiting until ', 300)
            await sleep(300)
            return False

        if result == -1:
            logger.info('Did not find building, removing from queue')
            return True

        successfully_built = await self.build()
        self.load_queue()
        # Trying to build something until success then return True.
        if successfully_built:
            return True
        else:
            return False

    @abstractmethod
    def dummy(self):
        """ Dummy """

    def load_queue(self):
        queue_file = open(Builder.queue_file, 'r+')
        buildings_queue = queue_file.read()
        if buildings_queue:
            queue_file.truncate(0)
        queue_file.close()
        buildings_queue = buildings_queue.split(',')
        if '' in buildings_queue:
            buildings_queue.remove('')
        if buildings_queue:
            Builder.queue += [building.strip() for building in buildings_queue]

    async def build(self):
        """Building function with handle of errors. If success return True, else None"""
        try:
            link_to_build = self.parse_link_to_build()
            if link_to_build is None:
                seconds_to_enough = self.parse_seconds_to_enough_resources() + randint(15, 90)

                info_logger_for_future_events('Lack of resources. Will be enough in ', seconds_to_enough)
                await sleep(seconds_to_enough)
                return False
            else:
                self.session.get(link_to_build)

        except RequestException:
            info_logger_for_future_events('RequestException occurred. Waiting... Next attempt in', 1500)
            await sleep(1500)

        else:
            self.set_parser_of_main_page()
            # if ROME_ACTIVE:
            seconds_left = await self.parse_specific_seconds_build_left() + randint(15, 90)
            # else:
            #     seconds_left = await self.parse_seconds_build_left() + randint(15, 90)
            info_logger_for_future_events('Building... Will be completed in ', seconds_left)
            await sleep(seconds_left)

            return True

    async def check_queue(self):
        """If buildings queue is not empty, then sleep until complete."""
        # if ROME_ACTIVE:
        seconds_build_left = await self.parse_specific_seconds_build_left()
        # else:
        #     seconds_build_left = await self.parse_seconds_build_left()
        if seconds_build_left:
            info_logger_for_future_events('Something is building already... Will be completed in ', seconds_build_left)
            await sleep(seconds_build_left)
            return False
        else:
            return True

    def parse_link_to_build(self):
        """Return a link which starts building if enough resources, else ValueError"""
        building_link = None
        # If enough resources parse onclick attribute
        if self.is_enough_resources():
            button = self.parser_location_to_build.find_all(class_='section1')
            if button:
                button = button[0]
            else:
                button = self.parser_location_to_build.find(class_='contractLink')
            link_to_upgrade = button.button.get('onclick')
            coins = button.button.get('coins')
            if not link_to_upgrade or coins:
                return None
            # parse link to build
            pattern = re.compile(r'(?<=\').*(?=\')')
            building_link = SERVER_URL + pattern.search(link_to_upgrade).group(0)

        return building_link

    def parse_required_resources(self):
        """Return dictionary with resources which required to build smth"""
        required_resources = self.parser_location_to_build.find(id='contract')
        if required_resources:
            required_resources = required_resources.find_all(class_='resource')
            required_resources = {span.get('title'): int(span.contents[1].contents[0]) for span in required_resources}
        else:
            resources = ['Dřevo', 'Hlína', 'Železo', 'Obilí', 'Spotřeba obilí']
            values = [int(val.text) for val in self.parser_location_to_build.find_all(class_='inlineIcon resource')]
            required_resources = dict(zip(resources, values))

        return required_resources

    def parse_resources_amount(self):
        """Return a dict with amount of current resources."""
        lumber = int(self.parse_resource('l1'))
        clay = int(self.parse_resource('l2'))
        iron = int(self.parse_resource('l3'))
        crop = int(self.parse_resource('l4'))

        resources_amount = {'Dřevo': lumber, 'Hlina': clay,
                            'Železo': iron, 'Obilí': crop}

        return resources_amount

    def parse_resource(self, id):
        """Takes id of resource-tag in html and return amount of this resource"""
        pattern = re.compile(r'\d+')
        resource = self.parser_main_page.find(id=id).text
        resource = resource.replace('.', '')
        resource = resource.replace(',', '')
        resource = resource.replace(' ', '').strip()

        amount = pattern.search(resource)
        amount = amount.group(0)

        return amount

    def parse_seconds_to_enough_resources(self):
        """Return time in seconds after which will be enough resources to build smth."""

        # TODO handle extend granary/warehouse status
        parsed_class = self.parser_location_to_build.find_all(class_='hide')[0]

        seconds_to_enough_resources = parsed_class.span.get('value')
        seconds_to_enough_resources = int(seconds_to_enough_resources)

        return seconds_to_enough_resources

    async def parse_seconds_build_left(self):
        """Return amount of time in order to build smth."""
        parser = self.parser_main_page
        second_left = parser.find_all(class_='buildDuration')
        # If found buildDuration class then return its value.
        #  Or there is no queue at all so we can build, return 0.
        if second_left:
            second_left = second_left[0].span.get('value')
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

    @abstractmethod
    def parse_specific_seconds_build_left(self):
        """Return amount of time in order to build smth."""

    def is_enough_crop(self):
        """Check if enough crop for building smth new."""
        parse_status_messages = self.parser_location_to_build.find_all(class_='errorMessage')
        if parse_status_messages:
            parse_message = parse_status_messages[0].text
            if parse_message == 'Nedostatek potravy: postavte nebo rozšiřte obilné pole':
                return False

        return True

    def is_enough_resources(self):
        """Checks amount of resources in order to build something."""
        required_resources = self.parse_required_resources()
        available_resources = self.parse_resources_amount()

        for key in required_resources:
            if (key in available_resources) and (available_resources[key] < required_resources[key]):
                return False

        return True

    def set_parser_of_main_page(self):
        """Renew the parser of the main page"""
        main_page_html = self.session.get(self.main_page_url).text
        self.parser_main_page = BeautifulSoup(main_page_html, 'html.parser')

    @abstractmethod
    def set_parser_location_to_build(self):
        """Set parser to location where will be built new building or field"""

