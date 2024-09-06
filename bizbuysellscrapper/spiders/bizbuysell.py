import scrapy
import re
import json
import os
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bizbuysellscrapper.listingDescriptionHandler import generate_readable_description, generate_readable_title_withAI, generate_image_from_AI, resize_and_convert_image
from bizbuysellscrapper.s3_bucket_manager import S3BucketManager
from bizbuysellscrapper.s3_utils import get_file_format, get_input_urls_from_s3
from scrapy.utils.project import get_project_settings
from bizbuysellscrapper.settings import custom_logger
import subprocess  # for running the python command
from scrapy.signalmanager import dispatcher
from scrapy import signals

settings = get_project_settings()
key_file_name = settings.get("KEY_FILE_NAME")

'''
def rebuild_business_description_post_spider_command():
    try:
        # Replace 'python your_command.py' with the command you want to run
        result = subprocess.run(['python3', 'bizbuysellscrapper/listingDescriptionHandler.py'], capture_output=True, text=True)
        if result.returncode == 0:
            custom_logger.info(f"Post-spider command output: {result.stdout}")
        else:
            custom_logger.error(f"Post-spider command failed with error: {result.stderr}")
    except Exception as e:
        custom_logger.error(f"Error running post-spider command: {str(e)}")
'''
def remove_special_characters(text):
    pattern = r'[^\w\s.,\'"&\-\®™©€\r\n\t]+'
    return re.sub(pattern, '', text)

def get_input_urls_from_local_fs(folder_name):
    # Open the file with the appropriate mode ('r' for reading text, 'rb' for reading bytes)

    with open(folder_name) as file:
        input_urls = file.read().split('\n')

    return input_urls

# Determine the environment
runEnv = os.getenv('RUN_ENV', 'local')  # Default to 'local' if not set
load_absentee_urls = os.getenv('LOAD_ABSENTEE_URLS', 'false').lower() == 'true'
load_sellerfinancing_urls = os.getenv('LOAD_SELLER_FINANCING_URLS', 'false').lower() == 'true'

# Set file path based on the environment
if runEnv == 'production':
    if load_absentee_urls:
        category_mapping_file_path = '/home/ubuntu/bizbuysell-absentee/EBITA/bizbuysellscrapper/CategoryMapping.csv'
    elif load_sellerfinancing_urls:
        category_mapping_file_path = '/home/ubuntu/bizbuysell-sellerfinanced/EBITA/bizbuysellscrapper/CategoryMapping.csv'
    else:
        category_mapping_file_path = '/home/ubuntu/bizbuysell-regular/EBITA/bizbuysellscrapper/CategoryMapping.csv'
else:
    if load_absentee_urls:
        category_mapping_file_path = '/Users/vikas/builderspace/EBITA/bizbuysellscrapper/CategoryMapping.csv'
    elif load_sellerfinancing_urls:
        category_mapping_file_path = '/Users/vikas/builderspace/EBITA/bizbuysellscrapper/CategoryMapping.csv'
    else:
        category_mapping_file_path = '/Users/vikas/builderspace/EBITA/bizbuysellscrapper/CategoryMapping.csv'

# Load the CSV file into a dictionary for category mapping
def load_category_mappings(category_mapping_file_path):
    df = pd.read_csv(category_mapping_file_path)
    return dict(zip(df['Original Category'], df['Mapped Category']))

# Load the mappings at the start
category_mapping = load_category_mappings(category_mapping_file_path)

def get_mapped_category(computed_category):
    # Check if the computed category exists in the dictionary
    if computed_category in category_mapping:
        # Print the mapped category if a match is found
        print("Mapped Category:", category_mapping[computed_category])
        return category_mapping[computed_category]
    else:
        # Print a message if no match is found
        print("No mapped category found for:", computed_category)
        return computed_category

class BizbuysellSpider(scrapy.Spider):
    name = "bizbuysell"

    def __init__(self):
        self.visited_urls = set()
    
    '''
    def __init__(self, *args, **kwargs):
        super(BizbuysellSpider, self).__init__(*args, **kwargs)
        self.visited_urls = set()
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)
    '''

    def start_requests(self):
        isTest = settings.get("IS_TEST")
        
        # Determine the environment
        runEnv = os.getenv('RUN_ENV', 'local')  # Default to 'local' if not set
        load_absentee_urls = os.getenv('LOAD_ABSENTEE_URLS', 'false').lower() == 'true'
        load_sellerfinancing_urls = os.getenv('LOAD_SELLER_FINANCING_URLS', 'false').lower() == 'true'

        # Set file path based on the environment
        if runEnv == 'production':
            if load_absentee_urls:
                file_path = "/home/ubuntu/bizbuysell-absentee/EBITA/bizbuysell-absentee-urls.txt"
                file_type = "absentee"
                self.file_type = 'absentee'
            elif load_sellerfinancing_urls:
                file_path = "/home/ubuntu/bizbuysell-sellerfinanced/EBITA/bizbuysell-sellerfinancing-urls.txt"
                file_type = "sellerfinancing"
                self.file_type = "sellerfinancing"
            else:
                file_path = "/home/ubuntu/bizbuysell-regular/EBITA/bizbuysell-urls.txt"
                file_type = "regular"
                self.file_type = "regular"                
        else:
            if load_absentee_urls:
                file_path = "/Users/vikas/builderspace/EBITA/bizbuysell-absentee-urls.txt"
                file_type = "absentee"
                self.file_type = 'absentee'
            elif load_sellerfinancing_urls:
                file_path = "/Users/vikas/builderspace/EBITA/bizbuysell-sellerfinancing-urls.txt"
                file_type = "sellerfinancing"
                self.file_type = "sellerfinancing"
            else:
                file_path = "/Users/vikas/builderspace/EBITA/bizbuysell-urls.txt"
                file_type = "regular"
                self.file_type = "regular"                

        # Running Local tests
        if isTest: 
            urls = get_input_urls_from_local_fs(file_path)
            for url in urls:
                url = url.strip()
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    custom_logger.info('Requesting Main URL: %s', url)
                    yield scrapy.Request(url, callback=self.parse, meta={'file_type': self.file_type})

        # Running version where file is read from S3
        else:
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
                        yield scrapy.Request(url, callback=self.parse, meta={'file_type': self.file_type})


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
        custom_logger.info('article_id: %s', article_id)

#        adid = article_id+"_BBS"
#        with open("/Users/vikas/builderspace/EBITA/files/"+key_file_name, 'a') as file:
#            file.write(adid + '\n')

        # Parse the HTML content using BeautifulSoup
        article_url = response.url
        businesses_title = response.meta.get("businesses_title")
        custom_logger.info('businesses_title: %s', businesses_title)
        scrapped_category = businesses_title
        custom_logger.info('scrapped_category: %s', scrapped_category)
        
        title = ""
        location = ""
        asking_price = ""

        # Title
        title = response.xpath("//span[@class='h3 hidden']/text()").get(default='NA').strip()

        # Location
        #location = response.xpath("//dl[@id='ctl00_ctl00_Content_ContentPlaceHolder1_wideProfile_listingDetails_dlDetailedInformation']/dd[1]/text()").get(default='NA').strip()
        
        location_xpath_query = "//div[@class='col-12 col-md-8 relative']/span[@class='f-l cs-800 flex-center g8 opacity-70']/text()"
        
        # Extracting text using the constructed XPath, stripping extra whitespace
        location = response.xpath(location_xpath_query).get(default='NA').strip()
        
        # Rent
        rent = response.xpath("//dt[contains(text(), 'Rent:')]/following-sibling::dd[1]/text()").get(default='NA').strip()

        # Asking Price
        asking_price = response.xpath("//span[contains(text(), 'Asking Price:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Cash Flow
        cash_flow = response.xpath("//span[contains(text(), 'Cash Flow:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Gross Revenue
        gross_revenue = response.xpath("//span[contains(text(), 'Gross Revenue:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # EBITDA
        ebitda = response.xpath("//span[contains(text(), 'EBITDA:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # FF&E
        ffe = response.xpath("//span[contains(text(), 'FF&E:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Inventory
        inventory = response.xpath("//span[contains(text(), 'Inventory:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Real Estate
        real_estate = response.xpath("//span[contains(text(), 'Real Estate:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Established
        established = response.xpath("//span[contains(text(), 'Established:')]/following-sibling::span/text()").get(default='NA').strip()
        
        # Business Listed By
        business_listed_by = response.xpath("//a[@id='ctl00_ctl00_Content_ContentPlaceHolder1_wideProfile_ctl03_ContactBrokerNameHyperLink']/text()").get(default='NA').strip()
        
        # Detailed Information
        '''
        details = response.xpath("//dl[@id='ctl00_ctl00_Content_ContentPlaceHolder1_wideProfile_listingDetails_dlDetailedInformation']")
        for dt, dd in zip(details.xpath('.//dt'), details.xpath('.//dd')):
            key = dt.xpath('text()').get(default='NA').strip().lower().replace(' ', '_').replace('&', 'and')
            value = dd.xpath('text()').get(default='NA').strip()
            listing[key] = value
        '''
        # Business Description
        raw_business_description = response.xpath("//div[@class='businessDescription f-m word-break']//text()").getall()
        cleaned_business_description = ' '.join([desc.strip() for desc in raw_business_description if desc.strip()])
        cleaned_business_description = cleaned_business_description.replace('\r', '').replace('\n', '')
        
        scraped_business_description_text = cleaned_business_description if cleaned_business_description else 'NA'
        ai_images_dict = {}

        generated_image_url = "https://publiclistingphotos.s3.amazonaws.com/no-photo.jpg"

        if (scraped_business_description_text and scraped_business_description_text != 'NA' and scraped_business_description_text != ""):
            business_description = generate_readable_description(scraped_business_description_text)

            ai_images_dict = generate_image_from_AI(business_description, article_id, businesses_title)            
        else:
            business_description = scraped_business_description_text

        if (business_description and business_description != 'NA' and business_description != ""):
            title = generate_readable_title_withAI(business_description)
        else:
            title = 'NA'

        # Listing Photos
        dynamic_dict = []
        dynamic_dict.append(ai_images_dict)

        listing_photos = response.xpath("//div[@id='slider']//img/@src").getall()
        if listing_photos:
            scrapped_images_dict = {}
            # Sizes you want to resize your image to
            sizes = [(851, 420), (526, 240), (146, 202), (411, 243), (265, 146)]
            s3_object_key = article_id+"_BBS_Scrapped.png"

            for index, scrapped_image_url in enumerate(listing_photos, start=2):
                for size in sizes:
                    resized_s3_url = resize_and_convert_image(scrapped_image_url, size, s3_object_key, article_url)
                    key = f"{size[0]}x{size[1]}"
                    scrapped_images_dict[key] = resized_s3_url

                dynamic_dict.append(scrapped_images_dict)

        # custom_logger.info('listing_photos: %s', listing_photos)

        # Attached Documents
        attached_documents = response.xpath("//div[@class='attachedFiles']//a/@href").getall()
        if not attached_documents:
            attached_documents = 'NA'
        # custom_logger.info('attached_documents: %s', attached_documents)
        

        # Using response.css() to extract asking price
        '''        
        asking_price_selector = response.css('.price.asking .normal::text').get()
        if asking_price_selector:
            asking_price = asking_price_selector.strip()
        else:
            asking_price = "NA"

        # Using response.css() to extract cash flow
        cash_flow_selector = response.css('.price help .normal::text').get()
        if cash_flow_selector:
            cash_flow = cash_flow_selector.strip()
        else:
            cash_flow = "NA"
        
        title = response.css(
            'h1.bfsTitle::text, h1#franchise-header::text').get().strip()
#        location = response.css(
#            'h2.gray::text, div.text-p1::text, div.initial-info-table-col:contains("Corporate Headquarters") p.franchise-details-label::text').get().strip()
#        asking_price = response.css(
#            'p.price.asking b:not(:has(*))::text, span.auction-details-label.font-regular.lime.tablet-block::text, div.initial-info-table-col:contains("Cash Required") p.franchise-details-label::text').get().strip()
        custom_logger.info('asking_price: %s', asking_price)
        
#        cash_flow = response.css(
#            'span.title:contains("Cash Flow:") + b::text').get()
        custom_logger.info('cash_flow: %s', cash_flow)
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

        business_listed_by = response.css('div.broker h4 span::text').get()
        '''
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
              
        broker = response.css('div.broker-card').get()

        alternate_broker = response.css('div.seller-container col-12').get()

        # Assuming 'broker' variable contains the updated HTML snippet with the broker-card information
        if broker:
            soup = BeautifulSoup(broker, 'html.parser')
            phone_link = soup.find('a', href=True, attrs={'class': 'gtm_tpn'})  # This looks for an <a> tag with class 'gtm_tpn'
            alternate_phone_link = soup.find('a', href=lambda href: href and href.startswith('tel:'))


            if phone_link and phone_link.has_attr('href'):
                phone_number = phone_link['href'].replace('tel:', '')  # Extracts and cleans the phone number
                # custom_logger.info('Broker Phone Number: %s', phone_number)
            elif alternate_phone_link:
                phone_number = alternate_phone_link['href'].replace('tel:', '').strip()
            else:
                phone_number = "Not Found"
                # custom_logger.info('Broker Phone Number not found.')

            broker_link = soup.find('a', href=True, attrs={'class': 'broker-name'})  # This looks for an <a> tag with class 'gtm_tpn'
            alternate_broker_link = soup.find('div', class_='broker-card')

            if broker_link and broker_link.has_attr('href'):
                broker_name = broker_link.text
                # custom_logger.info('Broker Name: %s', broker_name)
            elif alternate_broker_link:
                br_tag = alternate_broker_link.find('br')
                if br_tag and br_tag.next_sibling:
                    broker_name = br_tag.next_sibling.strip()

            else:
                broker_name = "Not Found"
                # custom_logger.info('broker name not found.')
        elif alternate_broker:
            soup = BeautifulSoup(alternate_broker, 'html.parser')
            # Extract the broker's name
            first_name = soup.find('div', class_='profile-first-name').get_text(strip=True)
            last_name = soup.find('div', class_='profile-last-name').get_text(strip=True)
            broker_name = f"{first_name} {last_name}"
            
            # Extract the phone number
            phone_link = soup.find('a', class_='profile-phone')
            phone_number = phone_link.get_text(strip=True) if phone_link else "Not Found"

        else:
            broker_name = "Not Found"
            phone_number = "Not Found"
        

        # Extracting image URLs from the ul#image-gallery container
#        listing_photos = response.css(
#            'ul#image-gallery img.image::attr(src), div.swiper-wrapper div img.swiper-image::attr(src)').getall()
        
        computed_category = (businesses_title[:-9].strip() if businesses_title.endswith(" For Sale") else businesses_title.strip()) if businesses_title else None
        custom_logger.info('computed_category: %s', computed_category)

        if computed_category == "Plumbing Businesses":
            computed_category = "Plumbing"

        if computed_category == "Accounting Businesses and Tax Practices":
            computed_category = "Accounting"

        if computed_category == "Pest Control Businesses":
            computed_category = "Pest control"

        if computed_category == "Landscaping and Yard Service Businesses":
            computed_category = "Landscaping"

        if computed_category == "Websites and Ecommerce Businesses":
            computed_category = "Ecommerce"
        
        if computed_category == "Cleaning Businesses":
            computed_category = "Cleaning"

        if computed_category == "Vending Machine Businesses":
            computed_category = "Vending"
        
        if computed_category == "Car Washes":
            computed_category = "Car Wash"

        if computed_category == "HVAC Businesses":
            computed_category = "HVAC"
        
        if computed_category == "Storage Facilities and Warehouses":
            computed_category = "Self Storage"

        computed_category = get_mapped_category(computed_category)

        load_absentee_urls = os.getenv('LOAD_ABSENTEE_URLS', 'false').lower() == 'true'
        load_sellerfinancing_urls = os.getenv('LOAD_SELLER_FINANCING_URLS', 'false').lower() == 'true'

        absenteeSeller = ""
        sellerfinancing = ""

        if load_absentee_urls:
            absenteeSeller = "absentee"
        elif load_sellerfinancing_urls:
            sellerfinancing = "yes"        

        # Check if the title length is 255 characters or less
        if len(title) <= 240:
            print("The title is within the 255 character limit.")            
        else:
            print("The title exceeds the 255 character limit.")
            # Truncate title to the first 50 characters
            title = title[:100]

        yield  {
            "businessOpportunity": {
                "ad_id":str(article_id)+"_BBS",
                "source": "BizBuySell",
                "article_url":article_url if article_url else None,
                "category":computed_category,
                "title": title,
                "location": location,
                "listing-photos": json.dumps(dynamic_dict),
                "attached-documents": json.dumps(attached_documents),
                "businessListedBy": business_listed_by.strip() if business_listed_by is not None else None,
                #"broker": broker,
                "broker-phone": phone_number,
                "broker-name": broker_name,
                "asking_price": asking_price,
                "cash_flow": cash_flow.strip() if cash_flow is not None else None,
                "rent": rent.strip() if rent is not None else None,
                "established": established.strip() if established is not None else None,
                "gross_revenue": gross_revenue.strip() if gross_revenue is not None else None,
                "scraped_business_description": scraped_business_description_text,
                "business_description": business_description,
                "generate_image_from_AI": generated_image_url,
                "EBITDA": ebitda,
                "FF&E": ffe,
                "inventory": inventory,
                "seller_financing": sellerfinancing,
                "owner_type": absenteeSeller,
                "detailedInformation": json.dumps({
                    "building_sf": building_sf.strip() if building_sf is not None else None,
                    "competition": competition.strip() if competition is not None else None,
                    "employees": employees.strip() if employees is not None else None,
                    "facilites": remove_special_characters(facilites.strip()) if facilites is not None else None,
                    "growth_expansion": growth_expansion.strip() if growth_expansion is not None else None,
                    "lease_expiration": lease_expiration.strip() if lease_expiration is not None else None,
                    "real_estate": real_estate.strip() if real_estate is not None else None,
                    "reason_for_selling": reason_for_selling.strip() if reason_for_selling is not None else None,
                    "support_training": support_training.strip() if support_training is not None else None,
                })
            }}

    def spider_closed(self, spider):
        custom_logger.info(f"Spider {spider.name} closed. Running post-spider command.")
#        rebuild_business_description_post_spider_command()