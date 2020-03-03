import time
import os
import shutil
import uuid
import boto3
import logging
import zipfile
logger = logging.getLogger()
logger.setLevel(logging.INFO)
import tempfile
from os import mkdir

import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# save over to S3, store information to return at end of function

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logger.error(e)
        return False
    return True

def lambda_handler(event, context):

    def is_empty(any_structure):
        if any_structure:
            # print('Structure is not empty.')
            return False
        else:
            # print('Structure is empty.')
            return True


    logger.info("-----Create Folders-----")

    tmp_folder = '/tmp/{}'.format(uuid.uuid4())

    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    if not os.path.exists(tmp_folder + '/user-data'):
        os.makedirs(tmp_folder + '/user-data')

    download_dir = tmp_folder + '/download-data/'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    logger.info("----/Create Folders-----")



    logger.info("-----Setup and run Selenium-----")

    options = webdriver.ChromeOptions()

    driver_path = './bin/chromedriver'
    options.binary_location = './bin/headless-chromium'

    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')

    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280x1696')
    options.add_argument('--user-data-dir={}'.format(tmp_folder + '/user-data'))
    options.add_argument('--hide-scrollbars')
    options.add_argument('--enable-logging')
    options.add_argument('--log-level=0')
    #options.add_argument('--v=99') - CAUSES AN ERROR
    options.add_argument('--data-path={}'.format(tmp_folder + '/data-path'))
    #options.add_argument('--ignore-certificate-errors')
    options.add_argument('--homedir={}'.format(tmp_folder))
    options.add_argument('--disk-cache-dir={}'.format(tmp_folder + '/cache-dir'))
    #options.add_argument(
    #    'user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

    prefs = {"profile.default_content_settings.popups": 0,
             "download.prompt_for_download": False,
             "safebrowsing_for_trusted_sources_enabled": False,
             "safebrowsing.enabled": False,
             "download.default_directory": download_dir,
             "directory_upgrade": True}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(driver_path, chrome_options=options)

    logger.info("----/Setup and run Selenium-----")


    logger.info("----Change download folder-----")

    # function to take care of downloading file
    def enable_download_headless(browser, download_dir):
        browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
        params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
        browser.execute("send_command", params)

    enable_download_headless(driver, download_dir)

    logger.info("---/Change download folder-----")


    logger.info("---- Start Scraping -----")

    #data = json.loads(open('/docs/commands.json').read())
    data = event
    logger.info(data)
    delay = 3
    short_delay = 1

    try:

        zip_list = []

        for k, v in data["selenium_commands"].items():

            logger.info("------start loop--------------------------------")

            date_time = time.strftime("%Y-%m-%d_%H.%M.%S")
            tmp_path = tempfile.mkdtemp()
            tmp_path_slash = tmp_path + os.sep
            tmp_path_screenshots = os.path.join(tmp_path_slash + "screenshots" + os.sep)
            mkdir(tmp_path_screenshots)
            tmp_path_pagesource = os.path.join(tmp_path_slash + "pagesource" + os.sep)
            mkdir(tmp_path_pagesource)
            tmp_path_download = os.path.join(tmp_path_slash + "download" + os.sep)
            mkdir(tmp_path_download)

            step = v["step"]
            send_keys_to_elements = v["send_keys_to_elements"]
            perform_download = v["perform_download"]
            prepend_to_name = v["prepend_to_name"]
            final_click = v["final_click"]
            css_button = v["css_button"]
            urls = v["urls"]
            save_page_source = v["save_page_source"]

            # 0. Start building a log response object;
            logger.info("   ---step---   ")
            logger.info(k)
            logger.info(step)
            logger.info("   --/step---   ")

            # 1. Try and get url - if fails, log
            logger.info("   ---urls---   ")
            logger.info(urls)
            try:
                driver.get(urls)
                time.sleep(delay)
            except:
                pass
                # break out of for loop
                # respond with failure
                logger.warning("unable to connect to " + urls)
                continue


            logger.info("   --/urls---   ")

            # if succesful, send all send Keys. If fails, log (and get screenshot), but continue
            # loop through all send_keys
            logger.info("   ---send_keys---   ")
            try:
                if send_keys_to_elements and isinstance(send_keys_to_elements, dict):

                    for sendK, sendV in send_keys_to_elements.items():
                        logger.debug("find element: " + sendV["value"])
                        elem = driver.find_element_by_css_selector(sendV["value"])

                        logger.debug("clear element: " + sendV["value"])
                        elem.clear()

                        logger.debug("send key to element: " + sendV["value"])
                        elem.send_keys(sendV["send_key"])

                    if final_click == "SEND_KEYS-ENTER":
                        elem.send_keys(Keys.RETURN)
                        time.sleep(delay)
                        driver.get_screenshot_as_file(
                            tmp_path_screenshots +
                            "step-" +
                            step +
                            "send_keys[PostSend]-" +
                            time.strftime("%Y%m%d-%H%M%S") +
                            ".png"
                        )
            except:
                pass
                # break out of for loop
                # respond with failure
                logger.warning("unable to send keys for " + urls)
                continue


            logger.info("   --/send_keys---   ")

            # trigger the button clicks if any present, in the order they are present in the json
            logger.info("   ---css_buttons---   ")
            if css_button and isinstance(css_button, dict):

                for cssK, cssV in css_button.items():
                    logger.info(cssV["buttonCSS"])
                    try:
                        button = driver.find_element_by_css_selector(cssV["buttonCSS"])
                    except:
                        logger.warning("Cannot find element: " + cssV["buttonCSS"])
                    else:
                        button.click()
                        time.sleep(short_delay)
                        driver.get_screenshot_as_file(
                            tmp_path_screenshots +
                            "css_button_" +
                            step +
                            "-" +
                            time.strftime("%Y%m%d-%H%M%S") +
                            ".png"
                        )
            else:
                logger.info("css button empty")

            logger.info("   --/css_buttons---   ")


            # trigger final button click
            logger.info("   ---final_click---   ")
            if final_click != "SEND_KEYS-ENTER":
                if final_click != "":

                    try:
                        button = driver.find_element_by_css_selector(final_click)
                        driver.get_screenshot_as_file(
                            tmp_path_screenshots +
                            "final_click_" +
                            step +
                            "-" +
                            time.strftime("%Y%m%d-%H%M%S") +
                            ".png"
                        )
                    except:
                        logger.warning("ERROR - unable to click final click")
                        logger.warning("Cannot find element: " + final_click)
                    else:
                        button.click()
                        time.sleep(delay)
                        driver.get_screenshot_as_file(
                            tmp_path_screenshots +
                            "final_click_" +
                            step + "-" +
                            time.strftime("%Y%m%d-%H%M%S") +
                            ".png"
                        )

                        # Move and rename the downloaded file(s)
                        if perform_download:
                            if os.path.isdir(download_dir):
                                files = os.listdir(download_dir)

                                if files:
                                    for f in files:
                                        shutil.move(download_dir + f, tmp_path_download)
                                        os.rename(tmp_path_download + f,
                                                  tmp_path_download + prepend_to_name + f)
                                else:
                                    logger.warning("No files downloaded")
                            else:
                                logger.warning(download_dir + " - Directory does not exist; no files will be saved")

                else:
                    logger.info("final click empty")
            else:
                logger.info("no final click triggered as enter used in send_keys_to_elements process")

            if perform_download:
                pass

            logger.info("   --/final_click---   ")

            # get entire page source
            if save_page_source:
                html_str = driver.page_source
                Html_file = open(tmp_path_pagesource + step + "-" + date_time + ".html", "w")
                Html_file.write(html_str)

                Html_file.close()

            #zip files

            def zipdir(path, ziph):
                base_dir = os.path.basename(os.path.normpath(path))

                # ziph is zipfile handle
                for root, dirs, files in os.walk(path, topdown=True):
                    logger.info(root)
                    logger.info(dirs)
                    for file in files:
                        sub_folder = root.split(base_dir)
                        if sub_folder[1] == "":
                            ziph.write(os.path.join(root, file), arcname = file)
                        else:
                            ziph.write(os.path.join(root, file), arcname = os.path.join(sub_folder[1], file))

            zip_name = prepend_to_name + date_time + ".zip"
            zip_location = "/tmp/" + zip_name
            zipf = zipfile.ZipFile(zip_location, 'w', zipfile.ZIP_DEFLATED)
            zipdir(tmp_path, zipf)
            zipf.close()

            bucket_name = "campsite-s3"
            s3 = boto3.client('s3')

            s3.upload_file(zip_location, bucket_name, zip_name)

            #if zip file available, else provide error information
            if True:
                s3_location = "https://" + bucket_name + ".s3-us-west-2.amazonaws.com/" + zip_name
                zip_list.append([step, s3_location, bucket_name, zip_name])
            else:
                pass

            logger.info("-----/next loop---------------------------------")
    except Exception as e:
        logger.error(e)
    finally:

        result_to_send = {'processing_results':zip_list}


    print(zip_list)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": json.dumps(result_to_send)
        })
    }

    logging.info("----- Cleanup -----")

    driver.close()

if __name__ == '__main__':
    lambda_handler(None, None)