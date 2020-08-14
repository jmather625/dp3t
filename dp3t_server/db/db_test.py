import unittest
from unittest import mock
import datetime
from freezegun import freeze_time
import fakeredis
import json

from db import db
from shared import (
    REDIS_CLIENT,
    REDIS_DISTRIBUTE_INFECTED_USERS_KEY,
    REDIS_LATEST_INFECTED_USERS_KEY,
    DATE_FORMAT,
)

class DbTest(unittest.TestCase):

    @freeze_time('2020-06-25 02:05:33')
    @mock.patch("time.sleep")
    def test_sleep_until_utc_midnight(self, time_mock):
        # run function
        db.sleep_until_utc_midnight()

        expected_sleep_time = 78867
        time_mock.assert_called_once_with(expected_sleep_time)


    @freeze_time('2020-06-25 02:05:33')
    def test_purge_old_infected_users_list(self):
        today = datetime.datetime(
            year=2020,
            month=6,
            day=25,
            hour=2,
            minute=5,
            second=33,
            tzinfo=datetime.timezone.utc,
        )
        yday = today + datetime.timedelta(days=-1)
        today_key = REDIS_DISTRIBUTE_INFECTED_USERS_KEY.format(today.year, today.month, today.day)
        yday_key = REDIS_DISTRIBUTE_INFECTED_USERS_KEY.format(yday.year, yday.month, yday.day)

        REDIS_CLIENT.rpush(
            today_key,
            "user1",
            "user2",
        )
        REDIS_CLIENT.rpush(
            yday_key,
            "user3",
            "user4",
        )

        # run function
        db.purge_old_infected_users_list()

        users = REDIS_CLIENT.lrange(yday_key, 0, -1)
        self.assertEqual(len(users), 0)

        users = REDIS_CLIENT.lrange(today_key, 0, -1)
        self.assertEqual(users, [b'user1', b'user2'])

    
    @freeze_time('2020-06-25 02:05:33')
    def test_migrate_all_infected_user_reports(self):
        fakeuser1 = {
            "user_id": "abcd_1",
            "date": "2020-06-25",
        }
        fakeuser2 = {
            "user_id": "abcd_2",
            "date": "2020-06-25",
        }
        fakeuser3 = {
            "user_id": "abcd_3",
            "date": "2020-06-24",
        }

        # these people have reported themselves as sick
        for user in [fakeuser1, fakeuser2, fakeuser3]:
            REDIS_CLIENT.rpush(REDIS_LATEST_INFECTED_USERS_KEY, json.dumps(user))

        # run command
        db.migrate_all_infected_user_reports()

        today = datetime.datetime(
            year=2020,
            month=6,
            day=25,
            hour=2,
            minute=5,
            second=33,
            tzinfo=datetime.timezone.utc,
        )
        yday = today + datetime.timedelta(days=-1)
        today_key = REDIS_DISTRIBUTE_INFECTED_USERS_KEY.format(today.year, today.month, today.day)
        yday_key = REDIS_DISTRIBUTE_INFECTED_USERS_KEY.format(yday.year, yday.month, yday.day)

        users = REDIS_CLIENT.lrange(yday_key, 0, -1)
        self.assertEqual(users, [b'abcd_3'])

        users = REDIS_CLIENT.lrange(today_key, 0, -1)
        self.assertEqual(users, [b'abcd_1', b'abcd_2'])


