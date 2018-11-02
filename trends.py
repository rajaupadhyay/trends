import pandas as pd
import csv
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from parsel import Selector
import coloredlogs
import logging



class TrendRequest(object):

    def __init__(self, useProxies=False, extensiveLogging=False, geo=''):
        self.GLASS_CEILING = 10
        self.RATE_LIMIT_ERROR = '(RATE LIMIT ERROR) An error occurred in retrieving trend data: Please try using proxies by switching on the "useProxies" flag.'
        self.resultDataFrame = pd.DataFrame()
        self.geo = geo

        self.useProxies = useProxies
        self.extensiveLogging = extensiveLogging
        # USE API TO ROTATE PROXIES (TO DO)

        self.chromeDriverPath = '/usr/local/bin/chromedriver'

        self.downloadPath = './trendsData'

        self.chromeOptions = Options()
        self.downloadPreferences = {'download.default_directory' : self.downloadPath,
                          'download.prompt_for_download' : False,
                          'profile.default_content_settings.popups' : 0}

        self.chromeOptions.add_experimental_option('prefs', self.downloadPreferences)
        self.chromeOptions.add_argument('--headless')
        # self.chromeOptions.add_argument('--window-size=1920x1080')

        if self.extensiveLogging:
            self.logger = logging.getLogger(__name__)
            coloredlogs.install(level='DEBUG', logger=self.logger)




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
                    writer.writerow(row)
                i += 1


    def retrieveTrends(self, keywords, timeFrame='today 3-m', geo=''):
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

        for keyIndex in range(len(keywords)):
            keyword = keywords[keyIndex]
            ctr += 1

            if self.extensiveLogging:
                self.logger.info("{}/{} - {} empty results - {} failed queries".format(ctr, totalKeywords, emptyResultsSoFar, failedQueries))

            if glassCeilingErrorsCheck == self.GLASS_CEILING:
                self.logger.error(self.RATE_LIMIT_ERROR)
                break


            url = 'http://trends.google.com/trends/explore?date={}&q='.format(timeFrame)
            url = url + keyword.replace(' ', '%20')


            try:
                browser.get(url)
                sleep(5)

                sel = Selector(text=browser.page_source)

                button = browser.find_element_by_css_selector('button.widget-actions-item.export')
                button.click()
                sleep(25)

                self._converter()

                convertedDataFrame = pd.read_csv('trendsData/multiTimelineConverted.csv', sep=',')

                columnName = "{}: (Worldwide)".format(keyword)
                convertedDataFrameValues = list(convertedDataFrame[columnName].values)

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

        browser.quit()
        self.resultDataFrame.to_csv('trendsData.csv')
        self.logger.info("Trends data obtained successfully!")
