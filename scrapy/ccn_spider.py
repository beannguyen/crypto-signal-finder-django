import scrapy
from scrapy import Request, FormRequest

from items.ccn_items import PostItem


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
            item['date'] = article.xpath('header/div/time/text()').extract_first().strip()
            yield item

        self.page += 1
        if self.page <= 20:
            self.payload['page'] = str(self.page)
            yield FormRequest(self.start_urls[0], callback=self.parse, formdata=self.payload)
