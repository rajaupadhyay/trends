# trends
A Google Trends API

## Overview
trends is a Python Library that allows you to obtain trends in the form of a CSV. This library make use of Selenium to download the CSV file from Google Trends and works around the rate limit quite well. The idea for this library came about when I needed to scrape Google Trends data for thousands of keywords but no library could suffice because of issues with the rate limit and secondly there aren't many libraries out there for scraping Google Trends data. Please feel free to contribute!

## To-do
- Take care of line 116 trends.py
- Allow user to change sleep time
- Add support for proxies
- Delete helper folder with files (not required)
- Use tqdm for progress bar
- Custom timespans
