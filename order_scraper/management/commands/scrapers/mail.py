import logging
import os
import sys
from django.conf import settings

from django.core.management.base import BaseCommand, CommandError
from imapclient import IMAPClient


class MailScraper(object):

    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        self.client = IMAPClient(host=settings.SCRAPER_MAIL_SERVER, port=settings.SCRAPER_MAIL_PORT)
        self.client.login(settings.SCRAPER_MAIL_USERNAME, settings.SCRAPER_MAIL_PASSWORD)

    #with  as client:
    #    print(
    #    print("")
    #    print(client.select_folder('[Gmail]/All e-post'))
    #    print("")
    #    print(len(client.search(['FROM', '"*@ebay.com"'])))
    #    print("")
    #    for x in client.list_folders():
    #        if any([x for x in x[0] if x.decode("utf-8") == "\All"]):
    #            print(x[2])
    #    print(M.noop())
    #    print(M.utf8_enabled)
    #    lst = M.list()
    #    if lst[0]:
    #        for item in lst[1]:
    #            print(item.decode("utf-8"))
    #    print(M.select("INBOX"))
    #    print(M.search(None, 'FROM', '"@ebay.com"'))
    #    print(M.logout())
    #
