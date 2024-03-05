import scrapy
import re
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

class BizbuysellSpider(scrapy.Spider):
    name = "bizbuysell"
    

    def __init__(self):
        self.visited_urls = set()

    def start_requests(self):
        # Get S3 bucket name from settings
        s3_bucket_name = settings.get("INPUT_S3_BUCKET_NAME")
        source_bucket_name = settings.get("SOURCE_BUCKET_NAME")

        if not s3_bucket_name:
            custom_logger.error("Please provide INPUT_S3_BUCKET_NAME environment variable.")
            return

        s3 = S3BucketManager(s3_bucket_name)

        response = s3.list_objects()
        for input_file_key in response:

            file_format = get_file_format(s3_bucket_name, input_file_key)

            urls = get_input_urls_from_s3(s3_bucket_name, input_file_key, file_format)
            s3.move_object(input_file_key,source_bucket_name,input_file_key)
            for url in urls:
                url = url.strip()
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    custom_logger.info('Requesting Main URL: %s', url)
                    yield scrapy.Request(url, callback=self.parse)
        

    def parse(self, response):
        custom_logger.info('Parsing URL: %s', response.url)
        
        # Extracting all articles
        articles = response.css(
            'app-listing-showcase, app-listing-basic, app-listing-diamond, app-listing-auction').getall()
        businesses_title = response.css('h1.header::text').get()
        for article in articles:
            article_selector = scrapy.Selector(text=article)
      
            anchor_tags = article_selector.xpath('//a')

            # Iterating through each anchor tag
            for anchor in anchor_tags:
                # Extracting the href attribute from the current anchor tag
                href = anchor.xpath("./@href").get()
                article_url = response.urljoin(href)
                if article_url:
                    custom_logger.info('Article URL: %s', article_url)
                    id_attribute = anchor.xpath("./@id").get()

                    if id_attribute:
                        article_id = id_attribute
                    else:
                        article_id = None
                    yield scrapy.Request(url=article_url, callback=self.parse_article, meta={'article_id': article_id,"businesses_title":businesses_title})

        next_page_url = response.css(
            'pagination-template ul.ngx-pagination li.active + li a::attr(href)').get()
        if next_page_url:
            next_page_url = urljoin(response.url, next_page_url)
            custom_logger.info('Next page URL: %s', next_page_url)
            # If there's a next page URL, follow it
            yield scrapy.Request(url=next_page_url, callback=self.parse)

    def parse_article(self, response):

        custom_logger.info('Parsing article URL: %s', response.url)
        article_id = response.meta.get('article_id')
        # Parse the HTML content using BeautifulSoup
        article_url = response.url
        businesses_title = response.meta.get("businesses_title")
        title = response.css(
            'h1.bfsTitle::text, h1#franchise-header::text').get().strip()
        location = response.css(
            'h2.gray::text, div.text-p1::text, div.initial-info-table-col:contains("Corporate Headquarters") p.franchise-details-label::text').get().strip()
        asking_price = response.css(
            'p.price.asking b:not(:has(*))::text, span.auction-details-label.font-regular.lime.tablet-block::text, div.initial-info-table-col:contains("Cash Required") p.franchise-details-label::text').get().strip()
        cash_flow = response.css(
            'span.title:contains("Cash Flow:") + b::text').get()
        rent = response.css(
            'span.title:contains("Rent:") + b::text, div.initial-info-table-col:contains("Min. Franchise Fee") p.franchise-details-label::text').get()
        established = response.css(
            'span.title:contains("Established:") + b::text, div.property-fact-label:contains("Year Built") div.property-fact-value::text, div.initial-info-table-col:contains("Franchising Since") p.franchise-details-label::text').get()
        gross_revenue = response.css(
            'span.title:contains("Gross Revenue:") + b::text, div.franchise-data:contains("Average Unit Revenue") p.franchise-details-label::text').get()
        business_description_body = response.css(
            'div.businessDescription, div#content-section, div.ng-franchise-details').getall()
        single_business_description_tags = ' '.join(business_description_body)
        business_description_text = BeautifulSoup(
            single_business_description_tags, "html.parser").get_text(strip=True)
        building_sf = response.css(
            'dl.listingProfile_details dt:contains("Building SF:") + dd::text, div.property-fact-label:contains("Building Size") div.property-fact-value::text').get()
        competition = response.css(
            'dl.listingProfile_details dt:contains("Competition:") + dd::text').get()
        employees = response.css(
            'dl.listingProfile_details dt:contains("Employees:") + dd::text').get()
        facilites = response.css(
            'dl.listingProfile_details dt:contains("Facilities:") + dd::text').get()
        growth_expansion = response.css(
            'dl.listingProfile_details dt:contains("Growth & Expansion:") + dd::text').get()
        lease_expiration = response.css(
            'dl.listingProfile_details dt:contains("Lease Expiration:") + dd::text').get()
        real_estate = response.css(
            'dl.listingProfile_details dt:contains("Real Estate:") + dd::text').get()
        reason_for_selling = response.css(
            'dl.listingProfile_details dt:contains("Reason for Selling:") + dd::text').get()
        support_training = response.css(
            'dl.listingProfile_details dt:contains("Support & Training:") + dd::text').get()
        business_listed_by = response.css('div.broker h4 span::text').get()

        # Extracting image URLs from the ul#image-gallery container
        listing_photos = response.css(
            'ul#image-gallery img.image::attr(src), div.swiper-wrapper div img.swiper-image::attr(src)').getall()

        # Extracting the style attribute value for additional image URLs
        style_values = response.css(
            'a.slides::attr(style), div#mainPhoto::attr(style)').getall()
        # Process the extracted values further
        additional_photos = []
        for style_value in style_values:
            if style_value:
                try:
                    src_path = style_value.split("url(")[1].split(")")[
                        0].strip('"\'')
                    additional_photos.append(src_path)
                except IndexError:
                    # Handle the case where the style value does not contain a valid URL
                    pass

        dynamic_dict = {}
        for index, url in enumerate(listing_photos + additional_photos, start=1):
            dynamic_dict[f"link-{index}"] = url
        yield  {
            "businessOpportunity": {
                "ad_id":str(article_id),
                "article_url":article_url if article_url else None,
                "category":businesses_title.strip() if businesses_title else None,
                "title": title,
                "location": location,
                "listing-photos": dynamic_dict,
                "businessListedBy": business_listed_by.strip() if business_listed_by is not None else None,
                "asking_price": asking_price,
                "cash_flow": cash_flow.strip() if cash_flow is not None else None,
                "rent": rent.strip() if rent is not None else None,
                "established": established.strip() if established is not None else None,
                "gross_revenue": gross_revenue.strip() if gross_revenue is not None else None,
                "business_description": remove_special_characters(business_description_text.strip()) if business_description_text is not None else None,
                "detailedInformation": {
                    "building_sf": building_sf.strip() if building_sf is not None else None,
                    "competition": competition.strip() if competition is not None else None,
                    "employees": employees.strip() if employees is not None else None,
                    "facilites": remove_special_characters(facilites.strip()) if facilites is not None else None,
                    "growth_expansion": growth_expansion.strip() if growth_expansion is not None else None,
                    "lease_expiration": lease_expiration.strip() if lease_expiration is not None else None,
                    "real_estate": real_estate.strip() if real_estate is not None else None,
                    "reason_for_selling": reason_for_selling.strip() if reason_for_selling is not None else None,
                    "support_training": support_training.strip() if support_training is not None else None,
                }
            }}
      
        

