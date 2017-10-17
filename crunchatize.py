# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import time
from os import environ
from collections import deque


CRUNCHYROLL_URL = 'http://www.crunchyroll.com'


class TailSet:
    """A specialized set that drops elements after exceeding a max length. The
    oldest element will be the first to be dropped."""
    def __init__(self, maxlen):
        """Creates a new tailset with a specified max length."""
        self._q = deque(maxlen=maxlen)
        self._s = set()

    def __contains__(self, item):
        """Returns True if the item is in the set."""
        return item in self._s

    def __iter__(self):
        """Provides a generator for the set."""
        for item in self._q:
            yield item

    def __str__(self):
        """Returns a deque representation of the set."""
        return self._q.__str__()

    def add(self, item):
        """Adds an item to the set. If the set is at max capacity remove the
        oldest element out of the set, then add the item."""
        if item in self._s:
            return
        if self._q.maxlen and len(self._q) == self._q.maxlen:
            removing = self._q.popleft()
            self._s.remove(removing)
        self._q.append(item)
        self._s.add(item)

    def update(self, items):
        """Adds a collection of items to the set."""
        for item in items:
            self.add(item)


class GroupMeBot:
    """Allows sending crunchyroll passes via a GroupMe bot."""
    POST_URL = 'https://api.groupme.com/v3/bots/post'

    def __init__(self, bot_id):
        """Creates a new wrapper for the GroupMe API."""
        self.bot_id = bot_id

    def send_msg(self, msg):
        """Sends a plaintext message as-is."""
        payload = {'bot_id': self.bot_id, 'text': msg}
        requests.post(GroupMeBot.POST_URL, payload)

    def send_code(self, code):
        """Formats the code as a link and sends it."""
        link = CRUNCHYROLL_URL + '/coupon_redeem?code=' + code
        msg = code + ' | ' + link
        self.send_msg(msg)


class ForumTopic:
    """Manages get requests to a crunchyroll forumtopic."""
    def __init__(self, forumtopic_id):
        """Constructs a new forumtopic."""
        self.url = CRUNCHYROLL_URL + '/forumtopic-' + forumtopic_id

    def get_last(self):
        """Returns the last page of the forumtopic."""
        return requests.get(self.url + '?pg=last')


def find_all_post_text(html):
    """Returns the bodies of all posts found on the page."""
    soup = BeautifulSoup(html, 'html.parser')
    posts = soup.find_all('div', 'showforumtopic-message-contents-text')
    return [post.text for post in posts]


def find_codes(text):
    """Returns a set of all codes found within a list of text."""
    codes = set()
    for item in text:
        found = re.findall('[0-9A-Z]{11}', item)
        codes.update(found)
    return codes


def latest_codes(forumtopic):
    """Gets the last page of the forumtopic and extracts all codes from it."""
    response = forumtopic.get_last()
    print('Reponse status:', response.status_code)
    text = find_all_post_text(response.content)
    return find_codes(text)


def main():
    """Execution entry point."""
    # Load Configuration and Setup:
    bot = GroupMeBot(environ.get('BOT_ID'))
    seen = TailSet(int(environ.get('MAX_SEEN', '20')))
    delay = int(environ.get('POLL_DELAY_SECS', '60'))
    forumtopic = ForumTopic('803801')
    # Begin Working:
    print('Ignoring latest codes...')
    seen.update(latest_codes(forumtopic))
    print('Seen:', seen)
    bot.send_msg('Y\'arr! Took me a quick nap, but I\'m bak to plunder! 🏴☠️')
    while True:
        print('Polling...')
        new_codes = latest_codes(forumtopic).difference(seen)
        print('New codes:', new_codes)
        for code in new_codes:
            print('Bot is sending %s...' % code)
            bot.send_code(code)
        seen.update(new_codes)
        print('Seen:', seen)
        print('Sleeping for', delay, 'seconds...')
        time.sleep(delay)


if __name__ == '__main__':
    main()
