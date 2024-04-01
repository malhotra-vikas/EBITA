import scrapy
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bizbuysellscrapper.s3_bucket_manager import S3BucketManager
from bizbuysellscrapper.s3_utils import get_file_format, get_input_urls_from_s3
from scrapy.utils.project import get_project_settings
from bizbuysellscrapper.settings import custom_logger

settings = get_project_settings()


def remove_special_characters(text):
    pattern = r'[^\w\s.,\'"&\-\®™©€\r\n\t]+'
    return re.sub(pattern, '', text)

def get_input_urls_from_local_fs(folder_name):
    # Open the file with the appropriate mode ('r' for reading text, 'rb' for reading bytes)

    with open(folder_name) as file:
        input_urls = file.read().split('\n')

    return input_urls

class BussinessforsaleSpider(scrapy.Spider):
    name = "bussinessforsale"

    def __init__(self):
        self.visited_urls = set()

    def start_requests(self):
        isTest = settings.get("IS_TEST")
        # Running Local tests
        if isTest: 
            urls = get_input_urls_from_local_fs("/Users/vikas/builderspace/EBITA-1/test.txt")
            for url in urls:
                url = url.strip()
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    custom_logger.info('Requesting Main URL: %s', url)
                    yield scrapy.Request(url, callback=self.parse)
        else:
            # Get S3 bucket name from settings
            s3_bucket_name = settings.get("INPUT_S3_BUCKET_NAME")
            source_bucket_name = settings.get("SOURCE_BUCKET_NAME")

            if not s3_bucket_name:
                custom_logger.error(
                    "Please provide INPUT_S3_BUCKET_NAME environment variable.")
                return

            s3 = S3BucketManager(s3_bucket_name)

            response = s3.list_objects()
            for input_file_key in response:

                file_format = get_file_format(s3_bucket_name, input_file_key)

                urls = get_input_urls_from_s3(
                    s3_bucket_name, input_file_key, file_format)
                s3.move_object(input_file_key, source_bucket_name, input_file_key)
                for url in urls:
                    url = url.strip()
                    if url not in self.visited_urls:
                        self.visited_urls.add(url)
                        custom_logger.info('Requesting Main URL: %s', url)
                        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        self.logger.info('Parsing URL: %s', response.url)
        articles = response.css('table.result-table').getall()
        businesses_title = response.css('h1::text').get()
        for article in articles:
            article_selector = scrapy.Selector(text=article)
            anchor_tag = article_selector.css('h2 a::attr(href)').get()
            if anchor_tag:
                self.logger.info('Article URL: %s', anchor_tag)
                yield scrapy.Request(url=anchor_tag, callback=self.parse_article, meta={"businesses_title": businesses_title})

        next_page_url = response.css('li.next-link a::attr(href)').get()
        if next_page_url:
            next_page_url = urljoin(response.url, next_page_url)
            self.logger.info('Next page URL: %s', next_page_url)
            # If there's a next page URL, follow it
            yield scrapy.Request(url=next_page_url, callback=self.parse)

    def parse_article(self, response):
        self.logger.info('Parsing article URL: %s', response.url)
        ad_id = response.css("span#listing-id::text").get()+"_BFS",
        self.logger.info('Parsing ad_id: %s', ad_id)

        title = response.css('title::text').get()
        category = response.meta.get("businesses_title")
        location = response.css('div#address > span::text').get()
        asking_price = response.css(
            'dl.price dt:contains("Asking Price:") + dd strong::text').get()
        sales_revenue = response.css('dl#revenue dd strong::text').get()
        cash_flow = response.css('dl#profit dd strong::text').get()
        business_description_body = response.css(
            'p.listing-paragraph::text').getall()
        single_business_description_tags = ' '.join(business_description_body)
        business_description_text = BeautifulSoup(
            single_business_description_tags, "html.parser").get_text(strip=True)
        business_operation_element = response.css('div#business-operation')
        reasons_for_selling = business_operation_element.css(
            'dl.listing-details dt:contains("Reasons for selling:") + dd p::text').get()
        employees = business_operation_element.css(
            'dl.listing-details dt:contains("Employees:") + dd::text').get()
        years_established = business_operation_element.css(
            'dl.listing-details dt:contains("Years established:") + dd::text').get()
        other_information_div = response.css('div#other-information')
        support_training = other_information_div.css(
            'dl.listing-details dt:contains("Support & training:") + dd p::text').get()
        furniture_fixtures_value = other_information_div.css(
            'dl.listing-details dt:contains("Furniture / Fixtures value:") + dd::text').get()
        inventory_stock_value = other_information_div.css(
            'dl.listing-details dt:contains("Inventory / Stock value:") + dd::text').get()
        listing_photos = response.css('#listing-gallery > ul > li > a > img::attr(src)').getall()
        dynamic_dict = {}
        for index, url in enumerate(listing_photos, start=1):
            dynamic_dict[f"link-{index}"] = url
        #source = response.css("title#logo-dt-title::text").get()

        listed_by = response.css("div.broker-details div.with-logo h4::text").get()
        yield {
            "businessOpportunity": {
                "ad_id": ad_id if ad_id else None,
                "source": "BusinessForSale",
                "article_url": response.url,
                "category": category.strip() if category else None,
                "title": title.strip() if title else None,
                "location": location.strip() if location else None,
                "listing-photos": json.dumps(dynamic_dict),
                "businessListedBy": listed_by.strip() if listed_by else None,
                "broker-phone":"Need to find",
                "broker-name":"Need to find",
                "asking_price": asking_price.strip() if asking_price else None,
                "cash_flow": cash_flow.strip() if cash_flow is not None else None,
                "rent":"Not Available",
                "established": "Not Available",
                "gross_revenue": sales_revenue.strip() if sales_revenue is not None else None,
                "detailedInformation": json.dumps({
                    'business_description': remove_special_characters(business_description_text.strip()) if business_description_text is not None else None,
                    'reasons_for_selling': reasons_for_selling.strip() if reasons_for_selling else None,
                    'employees': employees.strip() if employees else None,
                    'years_established': years_established.strip() if years_established else None,
                    "support_and_training": support_training.strip() if support_training else None,
                    "furniture_fixtures_value": furniture_fixtures_value.strip() if furniture_fixtures_value else None,
                    "inventory_stock_value": inventory_stock_value.strip() if inventory_stock_value else None
                })

            }
        }
