import os

from asyncio import sleep
from datetime import datetime
from time import time
from ast import literal_eval
from copy import copy
from credentials import SERVER_URL
from random import randint

from bs4 import BeautifulSoup

from authorization import logged_in_session
from logger import info_logger_for_future_events, get_logger

logger = get_logger(__name__)

ATTACK_TYPE = {'c': 4}

TROOPS = {'t' + str(i): 0 for i in range(1, 12)}


class TroopsOrder:
    """Creates an order for troops and send them to concrete point with timing."""

    def __init__(self, barrack_url, village_number):
        self.barrack_url = barrack_url
        self.session = None
        self.troops = copy(TROOPS)
        self.troops_to_send = copy(TROOPS)
        self.type = dict(ATTACK_TYPE)
        self.file_name = f'/tmp/RAIDS_{village_number}'
        self.attacks = []
        self.sent_troops = False

    async def __call__(self, *args, **kwargs):
        self.sent_troops =  False
        with open(self.file_name) as f:
            self.attacks += [line.rstrip('\n') for line in f]
            self.attacks = list(dict.fromkeys(self.attacks))
        if self.attacks:
            self.session = logged_in_session()
        else:
            info_logger_for_future_events('No raids, waiting until ', 60)
            await sleep(60)
            return

        self.parse_troops_amount()

        for attack in self.attacks:
            await sleep(randint(2,8))
            coords, troops = attack.split(';')
            # coords example {'x': 2, 'y': -5}
            try:
                x, y = coords.split('|')
                x = int(x[1:])
                y = int(y[:-1])
                self.coords = {'x': x, 'y': y}
                troops =  literal_eval(troops)
            except Exception as e:
                msg = str(e).lower()
                logger.error('Removing raid, wrong input\n' + msg)
                self.attacks.remove(attack)
            self.troops_to_send.update(troops)
            diffkeys = [k for k in self.troops_to_send.keys() if self.troops_to_send[k] != TROOPS[k]]
            if not diffkeys:
                continue
            if self.troops_available():
                self.send_troops()
                self.attacks.remove(attack)
            else:
                self.troops_to_send = TROOPS
                self.troops_to_send.update({'t4': 6})
                if self.troops_available():
                    logger.info("Don't have enough troops, sending 6 EIs")
                    self.send_troops()
                    self.attacks.remove(attack)
                else:
                    continue

        if self.sent_troops is False:
            time_to_return = self.time_for_troops_to_return()
            if time_to_return:
                info_logger_for_future_events('Did send any attack, waiting for return until ', time_to_return)
                await sleep(time_to_return)
            else:
                info_logger_for_future_events('Did send any attack and no one returning, waiting until ', time_to_return)
                await sleep(120)

    def send_troops(self):
        """The main function"""
        barrack_page = self.session.get(self.barrack_url).text
        barrack_parser = BeautifulSoup(barrack_page, 'html.parser')

        hidden_inputs_tags = barrack_parser.find_all('input', {'type': 'hidden'})

        post_data = {tag['name']: tag['value'] for tag in hidden_inputs_tags}

        post_data.update(self.troops_to_send)
        post_data.update(self.coords)
        post_data.update(self.type)
        post_data['dname'] = ''
        post_data['s1'] = 'ok'

        confirmation = self.session.post(SERVER_URL + 'build.php?gid=16&tt=2', data=post_data).text

        confirmation_parser = BeautifulSoup(confirmation, 'html.parser')
        # self.parse_time_of_next_raid(confirmation_parser)

        hidden_inputs_tags = confirmation_parser.find_all('input', {'type': 'hidden'})
        post_data = {tag['name']: tag['value'] for tag in hidden_inputs_tags}

        self.session.post(self.barrack_url, data=post_data)
        logger.info('Sending troops to: ({}|{})'.format(self.coords['x'], self.coords['y']))
        self.sent_troops = True

    def parse_troops_amount(self):
        """Parse amount of troops and save of to property"""
        overview_page_link = self.barrack_url.replace('tt=2', 'tt=1')
        overview_page = self.session.get(overview_page_link).text
        overview_page_parser = BeautifulSoup(overview_page, 'html.parser')

        # Get tags with amount of units.
        # unit_name_tags = overview_page_parser.find_all('img', class_='unit')
        overview_page_parser = overview_page_parser.find_all(class_="troop_details")[-1]
        unit_amount_tags = overview_page_parser.find_all('td', class_='unit')

        # Create dictionary with troops information
        # troops_amount = {name['alt']: amount.text for name, amount in zip(unit_name_tags, unit_amount_tags)}
        troops_amount = {'t{}'.format(i+1): int(unit_amount_tags[i].text) for i in range(len(unit_amount_tags))}
        self.troops = troops_amount

    def parse_time_of_next_raid(self, confirmation_parser):
        """Compute time to next raid. Takes parser of confirmation page"""
        timer_element = confirmation_parser.find('div', class_='at').contents[1]

        arrival_time_in_seconds = int(timer_element['value'])
        arrival_time = datetime.fromtimestamp(arrival_time_in_seconds) - datetime.now()

        seconds_to_come_back = arrival_time.total_seconds() * 2
        come_back_time = time() + seconds_to_come_back

        self.time_of_next_raid = come_back_time

    def save_next_raid_time(self):
        """Save coords and time for next raid in file."""
        with open("raids.txt", "rt") as file_input:
            with open("new_raids.txt", "wt") as file_output:

                for line in file_input:
                    if str(self.coords) in line:
                        file_output.write(str(self.coords) + ';' + str(self.time_of_next_raid) + '\n')
                    else:
                        file_output.write(line)

        os.rename('new_raids.txt', "raids.txt")

    def troops_available(self):
        """Determine what type of troops will be sent based on their availability. Return type and amount"""
        for key, value in self.troops.items():
            if value < self.troops_to_send[key]:
                return False
        return True

    def time_for_troops_to_return(self):
        overview_page_link = self.barrack_url.replace('tt=2', 'tt=1')
        overview_page = self.session.get(overview_page_link).text
        overview_page_parser = BeautifulSoup(overview_page, 'html.parser')
        try:
            back_time = int(overview_page_parser.find(class_="troop_details outRaid").find(class_="timer").get('value'))
        except:
            back_time = 0

        return back_time

