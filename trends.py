import pandas as pd
import csv
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from parsel import Selector
import coloredlogs
import logging
from tqdm import tqdm
import os
import requests
import random


class TrendRequest(object):
    def __init__(self, useProxies=False, extensiveLogging=False, geo=''):
        self.GLASS_CEILING = 10
        self.RATE_LIMIT_ERROR = '(RATE LIMIT ERROR) An error occurred in retrieving trend data: Please try using proxies by switching on the "useProxies" flag.'
        self.resultDataFrame = pd.DataFrame()
        self.geo = geo

        self.useProxies = useProxies
        self.extensiveLogging = extensiveLogging
        # USE API TO ROTATE PROXIES (TO DO)
        self.proxyListData = []
        self.proxy = None
        if self.extensiveLogging:
            self.logger = logging.getLogger(__name__)
            coloredlogs.install(level='DEBUG', logger=self.logger)

        if self.useProxies:
            proxyListURL = 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt'
            rawProxyListData = requests.get(proxyListURL)
            # open('proxyData.txt', 'wb').write(rawProxyListData.content)
            self.proxyListData = rawProxyListData.text.split('\n')
            self.proxy = self.chooseRandomProxy()

        self.chromeDriverPath = '/usr/local/bin/chromedriver'

        self.downloadPath = './trendsData'

        self.chromeOptions = Options()
        self.downloadPreferences = {'download.default_directory' : self.downloadPath,
                          'download.prompt_for_download' : False,
                          'profile.default_content_settings.popups' : 0}

        self.chromeOptions.add_experimental_option('prefs', self.downloadPreferences)
        self.chromeOptions.add_argument('--headless')

        if self.useProxies:
            self.chromeOptions.add_argument('--proxy-server={}'.format(self.proxy))

        # self.chromeOptions.add_argument('--window-size=1920x1080')




    def chooseRandomProxy(self):
        randProxy = random.choice(self.proxyListData)
        proxyVal = None

        if randProxy and randProxy[0].isdigit():
            randProxyList = randProxy.split()
            proxyVal = randProxyList[0]
            proxySecuritySettings = randProxyList[1].split('-')
            googlePassedValue = randProxyList[2]

            if len(proxySecuritySettings) == 3 and proxySecuritySettings[2] == 'S' \
            and proxySecuritySettings[1] == 'H' and googlePassedValue == '+':
                self.logger.info("Proxy details: {}".format(randProxy))
                return proxyVal
            else:
                return self.chooseRandomProxy()
        else:
            return self.chooseRandomProxy()



    def enableHeadlessDownload(self, browser):
        browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
        downloadPath = self.downloadPath
        parameters = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': downloadPath}}
        browser.execute("send_command", parameters)


    def _converter(self, originalFileName='trendsData/multiTimeline.csv', finalFileName='trendsData/multiTimelineConverted.csv'):
        with open(originalFileName, 'r') as inp, open(finalFileName, 'w') as out:
            writer = csv.writer(out)
            i = 1
            for row in csv.reader(inp):
                if i>2:
                    splitSecondTitleColumn = row[1].split(':')[0]
                    row[1] = splitSecondTitleColumn
                    writer.writerow(row)
                i += 1


    def retrieveTrends(self, keywords, timeFrame='today 3-m', geo='', cat='', sleepTime=20):
        browser = webdriver.Chrome(self.chromeDriverPath,options=self.chromeOptions)
        timeFrame = timeFrame.replace(' ', '%20')
        self.geo = geo

        self.enableHeadlessDownload(browser)

        if isinstance(keywords, str):
            keywords = [keywords]

        ctr = 0
        emptyResultsSoFar = 0
        failedQueries = 0
        totalKeywords = len(keywords)
        glassCeilingErrorsCheck = 0
        pandasIdxInsertionVal = 0
        disableTqdm = self.extensiveLogging

        for keyIndex in tqdm(range(len(keywords)), disable=disableTqdm):
            keyword = keywords[keyIndex]
            ctr += 1

            if self.extensiveLogging:
                self.logger.info("{}/{} - {} empty results - {} failed queries".format(ctr, totalKeywords, emptyResultsSoFar, failedQueries))

            if glassCeilingErrorsCheck == self.GLASS_CEILING:
                self.logger.error(self.RATE_LIMIT_ERROR)
                # If useProxies == True then rotate the proxy, after completion write failedKeywords to csv
                # also if useProxies == True then set lower limit for GLASS_CEILING
                break


            url = 'http://trends.google.com/trends/explore?date={}'.format(timeFrame)
            if geo:
                url = url + "&geo={}".format(geo)

            if cat:
                url = url + "&cat={}".format(cat)


            url = url + "&q=" + keyword.replace(' ', '%20')

            try:
                browser.get(url)
                sleep(5)

                sel = Selector(text=browser.page_source)

                button = browser.find_element_by_css_selector('button.widget-actions-item.export')
                button.click()
                sleep(sleepTime)

                self._converter()

                convertedDataFrame = pd.read_csv('trendsData/multiTimelineConverted.csv', sep=',')

                convertedDataFrameValues = list(convertedDataFrame[keyword].values)

                if convertedDataFrameValues:
                    self.resultDataFrame.insert(loc=pandasIdxInsertionVal, column=keyword, value=convertedDataFrameValues)
                    pandasIdxInsertionVal += 1
                else:
                    emptyResultsSoFar += 1

                glassCeilingErrorsCheck = 0
            except Exception as e:
                self.logger.error(e)
                failedQueries += 1
                glassCeilingErrorsCheck += 1

        try:
            os.remove('trendsData/multiTimeline.csv')
        except:
            self.logger.info("No results for helper file 1")

        try:
            os.remove('trendsData/multiTimelineConverted.csv')
        except:
            self.logger.info("No results for helper file 2")

        browser.quit()
        try:
            self.resultDataFrame.to_csv('trendsData/trendsData.csv')
        except:
            self.logger.error("No final result produced :(")

        if emptyResultsSoFar > 0 or failedQueries > 0:
            self.logger.error("Errors: {} empty and {} failed results".format(emptyResultsSoFar, failedQueries))

        self.logger.info("PROCESS COMPLETE")
