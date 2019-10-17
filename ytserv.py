#!/usr/bin/python

import argparse
import re
import urllib.parse

import irc.bot
import googleapiclient.discovery
import googleapiclient.errors

PATTERN_URL = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'


class YTServ(irc.bot.SingleServerIRCBot):
    def __init__(self, server, channel, nickname, api, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self,
                                            [(server, port)],
                                            nickname, nickname + '_')
        self.channel = channel
        self.count = 3500
        self.yt = googleapiclient.discovery.build(
            'youtube',
            'v3',
            developerKey=api,
        )
    
    def get_video_id(self, video_url):
        parsed = urllib.parse.urlparse(video_url, allow_fragments=True)

        if parsed.netloc.lower() == 'youtu.be':
            video_id = parsed.path.split('/')
            if len(video_id) > 1:
                video_id = video_id[1]
                return video_id

        query = urllib.parse.parse_qs(parsed.query)
        if 'v' in query:
            video_id = query['v']
            if video_id:
                return video_id[0]
        
        return None
    
    def get_video_title(self, video_url):
        video_id = self.get_video_id(video_url)
        if not video_id:
            return None

        request = self.yt.videos().list(
            part='snippet',
            hl='en',
            locale='en_US',
            id=video_id,
        )
        response = request.execute()

        if 'pageInfo' in response:
            if response['pageInfo']['totalResults']:
                title = response['items'][0]['snippet']
                title = title['title']
                return title

        return None

    def on_welcome(self, c, e):
        print('Welcome!')
        c.join(self.channel)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_join(self, c, e):
        def checker():
            print('Checking names.')
            c.names()
            self.reactor.scheduler.execute_after(120, checker)
        checker()

    def on_pubmsg(self, c, e):
        msg = e.arguments[0]
        self.count -= 1
        print('Got message:', msg)
        try:
            urls = re.findall(PATTERN_URL, msg)
            if urls:
                url = urls[0]
                print('Found url:', url)
                parsed = urllib.parse.urlparse(url)
                if 'youtu' in parsed.hostname:
                    title = self.get_video_title(url)
                    if title:
                        print('Sending title:', title)
                        c.privmsg(self.channel, title)
        except Exception as err:
            print('Got error:', err)

        if self.count == 0:
            self.die(';-;')

def parse_commandline():
    parser = argparse.ArgumentParser()
    
    help_txt = 'Server to connect to.'
    parser.add_argument('server', help=help_txt)

    help_txt = 'Channel to join.'
    parser.add_argument('channel', help=help_txt)

    help_txt = 'Nickname'
    parser.add_argument('nickname', help=help_txt)

    help_txt = 'API key for youtube.'
    parser.add_argument('api', help=help_txt)

    return parser.parse_args()

if __name__ == '__main__':
    ARGS = parse_commandline()
    while True:
        try:
            bot = YTServ(ARGS.server, ARGS.channel, ARGS.nickname, ARGS.api)
            bot.start()
        except KeyboardInterrupt:
            break
        except Exception as err:
            print(err)
            continue
