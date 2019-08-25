import sys

from asyncio import sleep

from bs4 import BeautifulSoup

from .builder import Builder
from credentials import SERVER_URL
from logger import info_logger_for_future_events, get_logger


logger = get_logger(__name__)


class BuildField(Builder):
    """Build field in village. Type depend on minimum resource"""
    def __init__(self, village_page_url):
        super().__init__(village_page_url)

    async def __call__(self, *args, **kwargs):
        try:
            await super().__call__()
        except Exception as e:
            msg = str(e).lower()
            logger.error(msg)
        finally:
            await self.__call__()

    async def dummy(self):
        await sleep(3)
        logger.info('FIELD')

    def set_parser_location_to_build(self):
        """Return link to field where will be built new resource field"""

        resource_name = self.minimal_resource()
        minimal_resource = resource_name[:2]
        field_link = self.link_to_field_to_build(minimal_resource)

        # If there are some field <10lvl then return link to it. Logged error and sleep otherwise.
        if field_link:
            full_field_link = SERVER_URL + field_link
            field_page = self.session.get(full_field_link).text

            self.parser_location_to_build = BeautifulSoup(field_page, 'html.parser')

            if self.is_enough_crop():
                logger.info('To be upgraded: {}'.format(resource_name))
                return True

            else:
                field_link = self.link_to_field_to_build('Ob')
                full_field_link = SERVER_URL + field_link
                field_page = self.session.get(full_field_link).text
                self.parser_location_to_build = BeautifulSoup(field_page, 'html.parser')
                logger.info('To be upgraded: Obilí')
                return True
        else:
            return False

    def minimal_resource(self):
        """Return minimal resource"""
        resources_amount = self.parse_resources_amount()
        logger.info('Current resources: {}'.format(resources_amount))
        minimal_resource = min(resources_amount, key=resources_amount.get)

        return minimal_resource

    def parse_fields(self):
        """Return dictionary with names of fields and appropriate links"""
        # Last link leads to town, so delete its
        fields = self.parser_main_page.find_all('area')[:-1]

        # Level of buildings and related links in village
        fields = {field.get('alt'): field.get('href') for field in fields}

        return fields

    def link_to_field_to_build(self, minimal_resource):
        """Find link to field with minimal resource"""

        fields = self.parse_fields()
        field_link = None
        lowest_level = sys.maxsize

        for field, link in fields.items():
            fields_level = int(field[-1])
            if (minimal_resource.lower() in field.lower()) and (10 >= fields_level < lowest_level):
                lowest_level = fields_level
                field_link = link

        return field_link

    async def parse_specific_seconds_build_left(self):
        parser = self.parser_main_page
        is_built = parser.find_all(class_='buildDuration')
        if not is_built:
            return 0
        second_left1 = is_built[0]
        building_name1 = second_left1.parent.find(class_='name').text

        if any(field in building_name1 for field in self.resources_dict.values()):
            second_left = second_left1
        else:
            second_left = None

        if len(is_built) > 1 and second_left is None:
            second_left2 = is_built[1]
            building_name2 = second_left2.parent.find(class_='name').text
            if any(field in building_name2 for field in self.resources_dict.values()):
                second_left = second_left2
            else:
                second_left = None

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

