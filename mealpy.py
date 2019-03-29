import click
import getpass
import json
import time

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

BASE_DOMAIN = 'secure.mealpal.com'
BASE_URL = f'https://{BASE_DOMAIN}'
LOGIN_URL = f'{BASE_URL}/1/login'
CITIES_URL = f'{BASE_URL}/1/functions/getCitiesWithNeighborhoods'
MENU_URL = f'{BASE_URL}/api/v1/cities/{{}}/product_offerings/lunch/menu'
RESERVATION_URL = f'{BASE_URL}/api/v2/reservations'
KITCHEN_URL = f'{BASE_URL}/1/functions/checkKitchen3'

LOGGED_IN_COOKIE = 'isLoggedIn'

HEADERS = {
    'Host': BASE_DOMAIN,
    'Origin': BASE_URL,
    'Referer': f'{BASE_URL}/login',
    'Content-Type': 'application/json',
}


class MealPal():

    def __init__(self):
        self.cookies = None
        self.cities = None

    def login(self, username, password):
        data = {'username': username, 'password': password}
        request = requests.post(LOGIN_URL, data=json.dumps(data), headers=HEADERS)
        self.cookies = request.cookies
        self.cookies.set(LOGGED_IN_COOKIE, 'true', domain=BASE_URL)
        return request.status_code

    @staticmethod
    def get_cities():
        request = requests.post(CITIES_URL, headers=HEADERS)
        return request.json()['result']

    def get_city(self, city_name):
        city = next((i for i in self.get_cities() if i['name'] == city_name), None)
        return city

    def get_schedules(self, city_name):
        city_id = self.get_city(city_name)['objectId']
        request = requests.get(MENU_URL.format(city_id), headers=HEADERS, cookies=self.cookies)
        return request.json()['schedules']

    def get_schedule_by_restaurant_name(self, restaurant_name, city_name):
        restaurant = next(
            i
            for i in self.get_schedules(city_name)
            if i['restaurant']['name'] == restaurant_name
        )
        return restaurant

    def get_schedule_by_meal_name(self, meal_name, city_name):
        return next(i for i in self.get_schedules(city_name) if i['meal']['name'] == meal_name)

    def reserve_meal(
            self,
            timing,
            city_name,
            restaurant_name=None,
            meal_name=None,
            cancel_current_meal=False,
    ):  # pylint: disable=too-many-arguments
        assert restaurant_name or meal_name
        if cancel_current_meal:
            self.cancel_current_meal()

        if meal_name:
            schedule_id = self.get_schedule_by_meal_name(meal_name, city_name)['id']
        else:
            schedule_id = self.get_schedule_by_restaurant_name(restaurant_name, city_name)['id']

        reserve_data = {
            'quantity': 1,
            'schedule_id': schedule_id,
            'pickup_time': timing,
            'source': 'Web',
        }

        request = requests.post(RESERVATION_URL, data=json.dumps(reserve_data), headers=HEADERS, cookies=self.cookies)
        return request.status_code

    def get_current_meal(self):
        request = requests.post(KITCHEN_URL, headers=HEADERS, cookies=self.cookies)
        return request.json()

    def cancel_current_meal(self):
        raise NotImplementedError()


# SCHEDULER = BlockingScheduler()
# EMAIL = input('Enter email: ')
# PASSWORD = getpass.getpass('Enter password: ')
EMAIL = 'a'
PASSWORD = 'b'


@click.group()
def cli_group():
    pass


@cli_group.command('save_user', short_help='Save username and password details into keyring for use by mealpy.')
def save_user():
    # update and store email and password here?
    pass


@cli_group.command('reserve', short_help='Reserve a meal on MealPal.')
@click.argument('restaurant')
@click.argument('time')
@click.argument('city')
def reserve(restaurant, time, city):
    execute_reserve_meal(restaurant, time, city)

cli = click.CommandCollection(sources=[cli_group])


# @SCHEDULER.scheduled_job('cron', hour=16, minute=59, second=58)
def execute_reserve_meal(restaurant, time, city):
    mealpal = MealPal()

    # Try to login
    while True:
        # TODO: Get email and password from keyring etc.
        status_code = mealpal.login(EMAIL, PASSWORD)
        if status_code == 200:
            print('Logged In!')
            break
        else:
            print('Login Failed! Retrying...')

    # Once logged in, try to reserve meal
    while True:
        try:
            status_code = mealpal.reserve_meal(
                time,
                restaurant_name=restaurant,
                city_name=city,
            )
            if status_code == 200:
                print('Reservation success!')
                print('Leave this script running to reschedule again the next day!')
                break
            else:
                print('Reservation error, retrying!')
        except IndexError:
            print('Retrying...')
            time.sleep(0.05)

# SCHEDULER.start()


if __name__ == '__main__':
    cli()
