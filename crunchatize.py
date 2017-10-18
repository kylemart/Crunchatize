# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import time
from os import environ
from collections import deque


CRUNCHYROLL_URL = 'http://www.crunchyroll.com'


class TailSet:
    """A set that removes old elements after exceeding a max length."""
    def __init__(self, maxlen):
        """Creates a new tailset with a specified max length."""
        self._q = deque(maxlen=maxlen)
        self._s = set()

    def __contains__(self, item):
        """Returns True if the item is in the tailset."""
        return item in self._s

    def __iter__(self):
        """Provides a generator for the tailset."""
        for item in self._q:
            yield item

    def __str__(self):
        """Returns a deque representation of the tailset."""
        return self._q.__str__()

    def add(self, item):
        """Adds an item to the tailset. If the tailset is at max capacity, an
           old element will be removed."""
        if item in self._s:
            return
        if self._q.maxlen and len(self._q) == self._q.maxlen:
            removing = self._q.popleft()
            self._s.remove(removing)
        self._q.append(item)
        self._s.add(item)

    def update(self, items):
        """Adds a collection of items to the tailset."""
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
        """Formats the code as a pretty message and sends it."""
        link = CRUNCHYROLL_URL + '/coupon_redeem?code=' + code
        msg = code + ' | ' + link
        self.send_msg(msg)


class ForumTopic:
    """Handles page retrieval from a crunchyroll forum topic."""
    def __init__(self, forumtopic_id):
        """Constructs a new forumtopic with a given id."""
        self.url = CRUNCHYROLL_URL + '/forumtopic-' + forumtopic_id

    def get_last(self):
        """Retrieves the last page of the forum topic."""
        return requests.get(self.url + '?pg=last').content


def extract_post_text(html):
    """Returns the contents of each post contained within the html."""
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
    """Extracts a set of all codes posted to the forum topic's last page."""
    try:
        page = forumtopic.get_last()
        text = extract_post_text(page)
        return find_codes(text)
    except requests.RequestError as e:
        print(e)
        return set()


def main():
    """Execution entry point."""
    bot = GroupMeBot(environ.get('BOT_ID'))
    seen = TailSet(int(environ.get('MAX_SEEN', '20')))
    delay = int(environ.get('POLL_DELAY_SECS', '60'))
    forumtopic = ForumTopic(environ.get('FORUMTOPIC_ID', '803801'))

    print('Ignoring codes already posted...')
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
