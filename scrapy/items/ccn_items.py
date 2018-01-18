import scrapy


class PostItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    img = scrapy.Field()
    short_desc = scrapy.Field()
    category = scrapy.Field()
    date = scrapy.Field()
