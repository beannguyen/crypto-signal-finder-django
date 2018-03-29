import scrapy
from scrapy import Request, FormRequest
import traceback

from items.ccn_items import PostItem
import psycopg2


class Postgres:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                "dbname='bsf_test1' user='bsfuser' host='localhost' password='Th3NeWorld@@@1893'")
        except:
            print("Unable to connect to the database")

    def is_article_exist(self, url):
        cur = self.conn.cursor()
        sql = "SELECT COUNT(*) FROM rest_newsitem WHERE url = '{}'".format(url)
        # print(sql)
        cur.execute(sql)
        row = cur.fetchone()
        count = 0
        if row is not None:
            count = row[0]
        return count

    def insert_article(self, article):
        try:
            cur = self.conn.cursor()
            if self.is_article_exist(article['url']) == 0:
                sql = "INSERT INTO rest_newsitem(title, url, img, short_desc, category_title, date, category_url) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}');".format(
                    article['title'],
                    article['url'],
                    article['img'],
                    '',
                    article['category']['title'],
                    article['date'],
                    article['category']['url'])
                # print(sql)
                cur.execute(sql)
                self.conn.commit()
        except:
            traceback.print_exc()

    def is_category_exist(self, url):
        cur = self.conn.cursor()
        sql = "SELECT COUNT(*) FROM rest_newscategory WHERE url = '{}'".format(url)
        # print(sql)
        cur.execute(sql)
        row = cur.fetchone()
        count = 0
        if row is not None:
            count = row[0]
        return count

    def insert_category(self, category):
        try:
            cur = self.conn.cursor()
            if self.is_category_exist(category['url']) == 0:
                sql = "INSERT INTO rest_newscategory(title, url) VALUES ('{}', '{}');".format(category['title'],
                                                                                              category['url'])
                # print(sql)
                cur.execute(sql)
                self.conn.commit()
        except:
            traceback.print_exc()


class SpidyQuotesSpider(scrapy.Spider):
    name = 'ccn_spider'
    start_urls = ['https://www.ccn.com/wp-admin/admin-ajax.php']
    page = 0
    payload = {
        "action": 'loadmore',
        "query": 'a:6:{s:14:"posts_per_page";i:16;s:16:"category__not_in";a:2:{i:0;i:2207;i:1;i:8663;}s:6:"offset";i:3;s:5:"paged";i:1;s:10:"fix_offset";b:1;s:5:"order";s:4:"DESC";}',
        "page": str(page)
    }

    def start_requests(self):
        self.db = Postgres()
        yield FormRequest(self.start_urls[0], callback=self.parse, formdata=self.payload)

    def parse(self, response):
        self.log('parsing...')
        articles = response.css('article')
        self.log('Got {} article'.format(len(articles)))
        for article in articles:
            item = PostItem()
            item['title'] = article.xpath('header/h4/a/text()').extract_first().strip()
            item['url'] = article.xpath('header/h4/a/@href').extract_first().strip()
            item['img'] = article.xpath('div/a/img/@src').extract_first().strip()
            item['category'] = {
                'title': article.xpath('header/div/span/a/@title').extract_first().strip(),
                'url': article.xpath('header/div/span/a/@href').extract_first().strip()
            }
            self.db.insert_category(item['category'])
            item['date'] = article.xpath('header/div/time/text()').extract_first().strip()
            self.db.insert_article(item)
            # break

        self.page += 1
        if self.page <= 20:
            self.payload['page'] = str(self.page)
            yield FormRequest(self.start_urls[0], callback=self.parse, formdata=self.payload)
