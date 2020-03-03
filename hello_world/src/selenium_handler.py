import logging
from src.selenium_scraper import scrape_sites

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    return scrape_sites(event)

if __name__ == '__main__':
    lambda_handler(None, None)