# rkitpy Miscellaneous functions
# Copyright (C) 2026 Raffaele Mancuso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Utilities for interacting with Scopus author profiles."""

from fake_useragent import UserAgent
import requests
import re
import logging
import time


class ScopusUtils:
    """
    Utility class for retrieving updated Scopus author IDs.

    Scopus may change author IDs over time. This class helps retrieve
    the current (non-tombstoned) author ID from an old Scopus ID.

    :ivar ua: A UserAgent instance for generating random user agents.
    """

    def __init__(self):
        """Initialize ScopusUtils with a random user agent."""
        self.ua = UserAgent()

    def get_new_scopus_id(self, old_scopus_id: str) -> str:
        """
        Get the current (non-tombstoned) Scopus author ID from an old one.

        :param old_scopus_id: The old Scopus author ID.
        :type old_scopus_id: str
        :return: The new, non-tombstoned Scopus author ID. Returns the old ID
            unchanged if the author is not found (ID is "0").
        :rtype: str
        :raises Exception: If the HTML response is malformed after 5 retries.
        """

        def get_match(old_scopus_id):
            headers = {"User-Agent": self.ua.chrome}
            url = "https://www.scopus.com/authid/detail.uri?authorId=" + old_scopus_id
            for _ in range(5):
                resp = requests.get(url, headers=headers)
                assert resp.status_code == 200
                match = re.search(r'nonTombstonedAuthorId="(\d+)"', resp.text)
                if match is None:
                    time.sleep(2)
                else:
                    return match
            logging.error(f"HTML is malformed: {url}")
            raise Exception("Malformed HTML")

        match = get_match(old_scopus_id)
        new_id = match.group(1)
        logging.info(f"Downloaded new Scopus ID: {old_scopus_id} -> {new_id}")
        if new_id == "0":
            return old_scopus_id
        assert new_id.isdigit()
        assert 10 <= len(new_id) <= 11
        return new_id
