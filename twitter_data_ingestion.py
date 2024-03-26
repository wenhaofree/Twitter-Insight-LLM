# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime, timedelta
import re
import json
import time
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import logging
from config import TWITTER_AUTH_TOKEN
import os
from notion_client import Client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
class NotionClient:
    def __init__(self):
        """
        初始化
        """
        global global_query_results
        global global_notion
        global global_database_id
        global_token = "secret_SGSgYlUHk8knQRLcwJr1alzjzVTwXFwrr0UDBawy0Sw"
        global_database_id = "294cc39bf0424a5ca79de50d76e2f6e1"
        global_notion = Client(auth=global_token)
        global_query_results = global_notion.databases.query(database_id=global_database_id)
        print('Notion初始化...')
    """
    创建新的页面
    1. 属性名字和字段个数要对应上
    2. 不同的属性用不同的构参方式
    """
    def create_page(self, page):
        new_page = global_notion.pages.create(
            parent={
                'database_id': global_database_id
            },
            properties={
                'Name': {
                    'title': [
                        {
                            'text': {
                                'content': 'title'
                            }
                        }
                    ]
                },
                '正文内容': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['text']
                            }
                        }
                    ]
                },
                "Tags": {
                    "multi_select": [
                        {
                            "name": "初始化"
                        }
                    ]
                },
                '昵称new': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['author_name']
                            }
                        }
                    ]
                },
                "点赞数": {
                    "number": page['num_like']
                },
                "评论数": {
                    "number": page['num_reply']
                },
                "转发数": {
                    "number": page['num_retweet']
                },
                '发布人': {
                    'rich_text': [
                        {
                            'text': {
                                'content': page['author_handle']
                            }
                        }
                    ]
                },
                "正文地址URL": {
                    'url': page['url']
                },
                "原始URL": {
                    'url': page['url']
                },
                "发布时间": {
                    "date": {
                        "start": page['date'],
                    }
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": page['text']
                                }
                            }
                        ]
                    }
                }
            ]
        )
        return new_page



class TwitterExtractor:
    def __init__(self, headless=True):
        self.driver = self._start_chrome(headless)
        self.set_token()

    def _start_chrome(self, headless):
        options = Options()
        options.headless = headless
        port=9222
        ip=f'127.0.0.1:{port}'
        options.add_experimental_option("debuggerAddress", ip)
        driver = webdriver.Chrome(options=options)
        driver.get("https://twitter.com")
        return driver

    def set_token(self, auth_token=TWITTER_AUTH_TOKEN):
        if not auth_token or auth_token == "YOUR_TWITTER_AUTH_TOKEN_HERE":
            raise ValueError("Access token is missing. Please configure it properly.")
        expiration = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        cookie_script = f"document.cookie = 'auth_token={auth_token}; expires={expiration}; path=/';"
        self.driver.execute_script(cookie_script)

    def fetch_tweets(self, page_url, start_date, end_date):
        self.driver.get(page_url)
        cur_filename = f"data/{username}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        # cur_filename = f"data/tweets_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        # Convert start_date and end_date from "YYYY-MM-DD" to datetime objects
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        while True:
            tweet = self._get_first_tweet()
            if not tweet:
                continue

            row = self._process_tweet(tweet)
            if row["date"]:
                try:
                    date = datetime.strptime(row["date"], "%Y-%m-%d")

                except ValueError as e:
                    # infer date format
                    logger.info(
                        f"Value error on date format, trying another format.{row['date']}",
                        e,
                    )
                    date = datetime.strptime(row["date"], "%d/%m/%Y")

                if date < start_date:
                    break
                elif date > end_date:
                    self._delete_first_tweet()
                    continue

            self._save_to_json(row, filename=f"{cur_filename}.json")
            logger.info(
                f"Saving tweets...\n{row['date']},  {row['author_name']} -- {row['text'][:50]}...\n\n"
            )
            self._delete_first_tweet()

        # Save to Excel
        # self._save_to_excel(
        #     json_filename=f"{cur_filename}.json", output_filename=f"{cur_filename}.xlsx"
        # )
        return f"{cur_filename}.json"




    # 获取详情数据:
    def fetch_tweets_detail(self, exist_ids, filename):
        #文件是否存在
        if not os.path.exists(filename):
            return
        urls=[]
        with open(filename) as f:
            for line in f:
                row=json.loads(line)
                urls.append(row['url'])
                # print(row['url'])
            f.close()
        print(urls)
        pages=[]
        # exist_ids=self.get_message_ids()
        for url in urls:
            try:
                #判断数据是否存在
                tweet_id = re.search(r'/status/(\d+)', url).group(1)
                if tweet_id in exist_ids:
                    continue
                time.sleep(5)
                self.driver.get(url)
                time.sleep(5)
                tweet = self._get_first_tweet()
                if not tweet:
                    continue
                row = self._process_tweet(tweet)     
                # tweet_id = re.search(r'/status/(\d+)', row['url']).group(1)

                page={
                    'tweet_id':tweet_id,
                    'text':row['text'],
                    'author_name':row['author_name'],
                    'author_handle':row['author_handle'],
                    'date':row['date'],
                    'lang':row['lang'],
                    'url':row['url'],
                    'mentioned_urls':row['mentioned_urls'],
                    'is_retweet':row['is_retweet'],
                    'media_type':row['media_type'],
                    'images_urls':row['images_urls'],
                    'num_reply':row['num_reply'],
                    'num_retweet':row['num_retweet'],
                    'num_like':row['num_like'],
                }
                pages.append(page)
                self._delete_first_tweet()
            except Exception as e:
                logger.error("Error on fetch_tweets_detail", e)
                continue
        return pages
        # 保存Notion
        # self._save_to_notion(pages)
    '''
    1. 只获取缩略的内容.存储
    '''
    def fetch_tweets_detail_json(self,exist_ids, filename):
        #文件是否存在
        if not os.path.exists(filename):
            return
        # urls=[]
        pages=[]
        # exist_ids=self.get_message_ids()
        with open(filename) as f:
            for line in f:
                row=json.loads(line)
                
                url=row['url']
                #判断数据是否存在
                tweet_id = re.search(r'/status/(\d+)', url).group(1)
                if tweet_id in exist_ids:
                    continue
                page={
                    'tweet_id':tweet_id,
                    'text':row['text'],
                    'author_name':row['author_name'],
                    'author_handle':row['author_handle'],
                    'date':row['date'],
                    'lang':row['lang'],
                    'url':row['url'],
                    'mentioned_urls':row['mentioned_urls'],
                    'is_retweet':row['is_retweet'],
                    'media_type':row['media_type'],
                    'images_urls':row['images_urls'],
                    'num_reply':row['num_reply'],
                    'num_retweet':row['num_retweet'],
                    'num_like':row['num_like'],
                }
                pages.append(page)
        return pages

    # 保存数据
    def _save_to_notion(self,client, pages):
        try:
            # client=NotionClient()
            inserted_pages=[]
            for page in pages:
                try:
                #判断数据是否存在
                    new_page=client.create_page(page)
                    store_page={
                        "pageId":new_page['id'],
                        "tweet_id":page['tweet_id']
                    }
                    inserted_pages.append(store_page)
                    print(f"Inserting {page['tweet_id']}")
                except Exception as e:
                    logger.error("NotionClient save page Error", e)
                    continue
            # Notion数据保存记录
            notion_path = os.path.join(os.path.dirname(__file__), "data", f'twitter-noiton.json')
            with open(notion_path, 'a') as f:
                for i in inserted_pages:
                    json.dump(i, f)
                    f.write('\n')
                f.close()
            logger.info("NotionClient Save Success")
        except Exception as e:
            logger.error("NotionClient Save Error", e)
    
    def get_message_ids(self):
        set_message_ids = set()
        # 判断文件是否存在
        result_path = os.path.join(os.path.dirname(__file__), "data", f'twitter-noiton.json')
        if not os.path.exists(result_path):
            print(f'[文件不存在:{result_path}')
            return set_message_ids
        # 读取json文件
        try:
            with open(result_path, 'r') as file:
                for line in file:
                    if len(line)>0:
                        obj = json.loads(line)
                        set_message_ids.add(obj['tweet_id'])
        except Exception as e:
            logger.error("NotionClient get_message_ids Error", e)
        print(f'[初始化...已记录nodeId数量:{len(set_message_ids)}]')
        return set_message_ids


    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(TimeoutException),
    )
    def _get_first_tweet(
        self, timeout=10, use_hacky_workaround_for_reloading_issue=True
    ):
        try:
            # Wait for either a tweet or the error message to appear
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(By.XPATH, "//article[@data-testid='tweet']")
                or d.find_elements(By.XPATH, "//span[contains(text(),'Try reloading')]")
            )

            # Check for error message and try to click "Retry" if it's present
            error_message = self.driver.find_elements(
                By.XPATH, "//span[contains(text(),'Try reloading')]"
            )
            if error_message:
                self.driver.refresh()
                time.sleep(2)
                error_message = self.driver.find_elements(
                By.XPATH, "//span[contains(text(),'Try reloading')]"
            )

            if error_message and use_hacky_workaround_for_reloading_issue:
                logger.info(
                    "Encountered 'Something went wrong. Try reloading.' error.\nTrying to resolve with a hacky workaround (click on another tab and switch back). Note that this is not optimal.\n"
                )
                logger.info(
                    "You do not have to worry about data duplication though. The save to excel part does the dedup."
                )
                self._navigate_tabs()

                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.find_elements(
                        By.XPATH, "//article[@data-testid='tweet']"
                    )
                )
            elif error_message and not use_hacky_workaround_for_reloading_issue:
                raise TimeoutException(
                    "Error message present. Not using hacky workaround."
                )

            else:
                try:
                # If no error message, assume tweet is present
                    return self.driver.find_element(
                        By.XPATH, "//article[@data-testid='tweet']"
                    )
                except Exception as e:
                    logger.error("Error processing tweet: " + str(e))
                    return None


        except TimeoutException:
            logger.error("Timeout waiting for tweet or after clicking 'Retry'")
            raise
        except NoSuchElementException:
            logger.error("Could not find tweet or 'Retry' button")
            raise
    def _navigate_tabs(self, target_tab="Likes"):
        # Deal with the 'Retry' issue. Not optimal.
        try:
            # Click on the 'Media' tab
            self.driver.find_element(By.XPATH, "//span[text()='Media']").click()
            time.sleep(2)  # Wait for the Media tab to load

            # Click back on the Target tab. If you are fetching posts, you can click on 'Posts' tab
            self.driver.find_element(By.XPATH, f"//span[text()='{target_tab}']").click()
            time.sleep(2)  # Wait for the Likes tab to reload
        except NoSuchElementException as e:
            logger.error("Error navigating tabs: " + str(e))

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def _process_tweet(self, tweet):

        author_name, author_handle = self._extract_author_details(tweet)
        try:
            data = {
                "text": self._get_element_text(
                    tweet, ".//div[@data-testid='tweetText']"
                ),
                "author_name": author_name,
                "author_handle": author_handle,
                "date": self._get_element_attribute(tweet, "time", "datetime")[:10],
                "lang": self._get_element_attribute(
                    tweet, "div[data-testid='tweetText']", "lang"
                ),
                "url": self._get_tweet_url(tweet),
                "mentioned_urls": self._get_mentioned_urls(tweet),
                "is_retweet": self.is_retweet(tweet),
                "media_type": self._get_media_type(tweet),
                "images_urls": (
                    self._get_images_urls(tweet)
                    if self._get_media_type(tweet) == "Image"
                    else None
                ),
            }
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            logger.info(f"Tweet: {tweet}")
            raise
        # Convert date format
        if data["date"]:
            data["date"] = datetime.strptime(data["date"], "%Y-%m-%d").strftime(
                "%Y-%m-%d"
            )

        # Extract numbers from aria-labels
        data.update(
            {
                "num_reply": self._extract_number_from_aria_label(tweet, "reply"),
                "num_retweet": self._extract_number_from_aria_label(tweet, "retweet"),
                "num_like": self._extract_number_from_aria_label(tweet, "like"),
            }
        )
        return data

    def _get_element_text(self, parent, selector):
        try:
            return parent.find_element(By.XPATH, selector).text
        except NoSuchElementException:
            return ""

    def _get_element_attribute(self, parent, selector, attribute):
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).get_attribute(
                attribute
            )
        except NoSuchElementException:
            return ""

    def _get_mentioned_urls(self, tweet):
        try:
            # Find all 'a' tags that could contain links. You might need to adjust the selector based on actual structure.
            link_elements = tweet.find_elements(
                By.XPATH, ".//a[contains(@href, 'http')]"
            )
            urls = [elem.get_attribute("href") for elem in link_elements]
            return urls
        except NoSuchElementException:
            return []

    def is_retweet(self, tweet):
        try:
            # This is an example; the actual structure might differ.
            retweet_indicator = tweet.find_element(
                By.XPATH, ".//div[contains(text(), 'Retweeted')]"
            )
            if retweet_indicator:
                return True
        except NoSuchElementException:
            return False

    def _get_tweet_url(self, tweet):
        try:
            link_element = tweet.find_element(
                By.XPATH, ".//a[contains(@href, '/status/')]"
            )
            return link_element.get_attribute("href")
        except NoSuchElementException:
            return ""

    def _extract_author_details(self, tweet):
        author_details = self._get_element_text(
            tweet, ".//div[@data-testid='User-Name']"
        )
        # Splitting the string by newline character
        parts = author_details.split("\n")
        if len(parts) >= 2:
            author_name = parts[0]
            author_handle = parts[1]
        else:
            # Fallback in case the format is not as expected
            author_name = author_details
            author_handle = ""

        return author_name, author_handle

    def _get_media_type(self, tweet):
        if tweet.find_elements(By.CSS_SELECTOR, "div[data-testid='videoPlayer']"):
            return "Video"
        if tweet.find_elements(By.CSS_SELECTOR, "div[data-testid='tweetPhoto']"):
            return "Image"
        return "No media"

    def _get_images_urls(self, tweet):
        images_urls = []
        images_elements = tweet.find_elements(
            By.XPATH, ".//div[@data-testid='tweetPhoto']//img"
        )
        for image_element in images_elements:
            images_urls.append(image_element.get_attribute("src"))
        return images_urls

    def _extract_number_from_aria_label(self, tweet, testid):
        try:
            text = tweet.find_element(
                By.CSS_SELECTOR, f"div[data-testid='{testid}']"
            ).get_attribute("aria-label")
            numbers = [int(s) for s in re.findall(r"\b\d+\b", text)]
            return numbers[0] if numbers else 0
        except NoSuchElementException:
            return 0

    def _delete_first_tweet(self, sleep_time_range_ms=(0, 1000)):
        try:
            tweet = self.driver.find_element(
                By.XPATH, "//article[@data-testid='tweet'][1]"
            )
            self.driver.execute_script("arguments[0].remove();", tweet)
        except NoSuchElementException:
            logger.info("Could not find the first tweet to delete.")

    @staticmethod
    def _save_to_json(data, filename="data.json"):
        with open(filename, "a", encoding="utf-8") as file:
            json.dump(data, file)
            file.write("\n")

    @staticmethod
    def _save_to_excel(json_filename, output_filename="data/data.xlsx"):
        # Read JSON data
        cur_df = pd.read_json(json_filename, lines=True)

        # Drop duplicates & save to Excel
        cur_df.drop_duplicates(subset=["url"], inplace=True)
        cur_df.to_excel(output_filename, index=False)
        logger.info(
            f"\n\nDone saving to {output_filename}. Total of {len(cur_df)} unique tweets."
        )

def main():
    global username
    '''
    1. 获取到数据是省略的
    2. 点击详情获取所有数据
    3. 数据保存到Notion中
    '''

    user_list=[
        # 'https://twitter.com/dotey/',
        # 'https://twitter.com/op7418/',
        # 'https://twitter.com/lidangzzz/',
        # 'https://twitter.com/vista8/',
        # 'https://twitter.com/imxiaohu/',
        # 'https://twitter.com/WaytoAGI/',
        # 'https://twitter.com/hanqing_me/',
        # 'https://twitter.com/jesselaunz/',
        # 'https://twitter.com/lewangx/',
        # 'https://twitter.com/JefferyTatsuya/',
        # 'https://twitter.com/OwenYoungZh/',
        # 'https://twitter.com/thinkingjimmy/',
        # 'https://twitter.com/oran_ge/',
        # 'https://twitter.com/99aico/',
        # 'https://twitter.com/Cydiar404/',
        # 'https://twitter.com/tangpanqing/',
        # 'https://twitter.com/didengshengwu/',
        # 'https://twitter.com/BennyLeeBTC/',
        'https://twitter.com/Mr_BlackMirror/',
        # 'https://twitter.com/baoshu88/'
    ]
    
    scraper = TwitterExtractor()
    exist_ids=scraper.get_message_ids()
    client=NotionClient()
    for user in user_list:
        try:
            username = re.search(r'twitter\.com/(\w+)', user).group(1)
            file_path=scraper.fetch_tweets(
                user,
                start_date="2024-03-26",
                end_date="2024-03-30",
            )
            file_path = os.path.join(os.path.dirname(__file__), file_path)
            if not os.path.exists(file_path):
                continue
            pages=scraper.fetch_tweets_detail(exist_ids=exist_ids,filename=file_path)
            # pages=scraper.fetch_tweets_detail_json(exist_ids=exist_ids,filename=file_path)
            if pages is None:
                continue
            scraper._save_to_notion(client=client,pages=pages)
        except Exception as e:
            logger.error('获取数据异常:{e}')

from notion_clean_twitter import main as clean_main
if __name__ == "__main__":
    main()
    # clean_main()


# if __name__ == "__main__":
#     scraper = TwitterExtractor()
#     scraper.fetch_tweets(
#         "https://twitter.com/GZhan5/likes",
#         start_date="2024-03-01",
#         end_date="2024-03-05",
#     )  # YYYY-MM-DD format

#     # If you just want to export to Excel, you can use the following line
#     # scraper._save_to_excel(json_filename="tweets_2024-02-01_14-30-00.json", output_filename="tweets_2024-02-01_14-30-00.xlsx")
