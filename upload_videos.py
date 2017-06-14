# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is not an official Google product
"""This script uploads videos to DCM and sets geo-targeting from a CSV file

This script processes a CSV file containing a description of a set of videos.
It uploads each video to DCM, creating a new Ad for each video. Each Ad
is targeted to a given geo location based on the information on the input CSV.
All Ads are created inside a single placement that is also taken as CLI
parameters.

The script makes use of Python Google API client libraries, which is available
at https://developers.google.com/api-client-library/python/ You will need to
install them to be able to use this script.

Additionally, you will also need to place a copy of dfareporting_utils.py,
available on the DCM samples library at https://github.com/googleads/googleads-dfa-reporting-samples/tree/master/python/v2_7

The script makes use of OAuth 2.0 credentials to access DCM APIs. You
would need to place your credentials on a 'client_secrets.json' file in the
execution directory. You can follow the instructions available at
https://developers.google.com/doubleclick-advertisers/getting_started. In
order to perform the OAuth authentication from the command-line, you may need
to execute the script with the option '--noauth_local_webserver'

For a description of all the arguments please execute the script with
the argument --help
"""

import sys
import argparse
import csv
import subprocess
import os
import logging
import video_uploader

COLUMN_FILENAME = 'Filename'
COLUMN_FILE_URL = 'File URL'
COLUMN_CREATIVE_NAME = 'Creative name'
COLUMN_TARGET_ZIP_CODE = 'ZIP'
COLUMN_LANDING_URL = 'Landing URL'

VIDEO_FILE_EXTENSION = '.mp4'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up arguments
argparser = argparse.ArgumentParser(
    add_help=False,
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
argparser.add_argument(
    'profile_id', type=int,
    help=('The ID of the DCM use profile to use. You will need a profile with '
    'write access to the advertiser and campaign where you want to add the '
    'videos'))
argparser.add_argument(
    'advertiser_id', type=int,
    help=('The ID of the advertiser to use. This is where all new video '
          'creatives will be added'))
argparser.add_argument(
    'campaign_id', type=int,
    help="The ID of the campaign where the dynamic creative structure will be "
    "added")
argparser.add_argument(
    'placement_id', type=int,
    help="The ID of the DCM placement inside which ads will "
    "be created")
argparser.add_argument(
    'creatives_list', type=str,
    help=("CSV file with one row per creative. The following columns are "
    "expected in the file: 'Filename', 'File URL', 'Creative name', 'ZIP', "
    "'Landing URL'. 'Filename' column may be empty as long as 'File URL' "
    " has a value. The rest of the columns are all required"))
argparser.add_argument(
    'success_file', type=str,
    help="Output CSV with ads created. The script will write here the list "
    "of all the ads that were successfully created")
argparser.add_argument(
    'failure_file', type=str,
    help="Output CSV with ads that could not be created. If for any reason "
    "any of the ads could not be created, you will find the "
    "reason in this file")

def download_file(url, target_file):
  """Download file from URL.

  This method downloads file from a URL. It uses wget in a separate process,
  so it's able to cope with redirects.

  Args:
    url: Source URL from which we want to download the file.
    target_file: Target filename

  Raises:
    Exception: if wget exited with error code (!=0)
  """
  #Have to use this since I'm getting problems with SSL
  FNULL = open(os.devnull, 'w')
  if subprocess.call(["wget", url, "-O", target_file],
                  stdout=FNULL, stderr=subprocess.STDOUT):
    raise Exception("Error while downloading file")


def process_row(row, uploader, failure_writer):
  """Process row (e.g.: dict as returned by CSV) and add video to DCM.

  This method processes a row, which is a dict as returned by a CSVReader. It
  will extract the information about a video contained in that row (name,
  target ZIP code, video file/video URL, landing page), and add the video to
  DCM as new creative.

  After executing this method, if video could be added successfully, a new
  ad will be present on DCM, with the video as associated creative, and with
  the appropriate ZIP code targeting. The ad will not be active yet, though.

  Args:
    row: dict containing information about one video. Can be the row as output
      from a CSVReader.
    uploader: Instance of VideoUploader to be used to do the trafficking on DCM.
    failure_writer: Information about videos that could not be added will be
      added to this CSVWriter.

  Returns:
    ID of the newly created ad on DCM if the operation suceeded. None otherwise.
  """
  # Initialize return variable
  created_ad_id = None
  # Load new video metadata from row
  creative_name = row[COLUMN_CREATIVE_NAME] + VIDEO_FILE_EXTENSION
  video_file = row.get(COLUMN_FILENAME, None)
  target_zip_code = "%05d" % (int(row[COLUMN_TARGET_ZIP_CODE]))
  landing_url = row[COLUMN_LANDING_URL]
  # Remove forbidden characters from new creative name
  creative_name = video_uploader.clean_up_creative_name(creative_name)
  logger.info("Processing creative '%s'", creative_name)


  video_downloaded = False
  try:
    # Download video file if it wasn't provided in the metadata
    if not video_file:
      video_downloaded = True
      video_url = row[COLUMN_FILE_URL]
      video_file = creative_name
      logger.info("Downloading video on URL '%s'", video_url)
      download_file(video_url, video_file)
      logger.info("Video file downloaded")
    logger.info("Adding element: '%s', '%s', '%s', '%s'",
        creative_name, video_file, target_zip_code, landing_url)

    # Invoke VideoUploader to actually traffic new video and ad into DCM
    created_ad_id = uploader.new_video(creative_name, video_file,
                        target_zip_code, landing_url)
  except Exception as e:
    logger.error("Exception while processing row: '%s'. Exception: %s", row, e)
    # If video could not be added, log it to failure_writer. We do not propagate
    # the exception to let the script continue with the next video
    failure_writer.writerow(
        [creative_name, target_zip_code, video_file, landing_url,
         "{}".format(e)])
  finally:
    if video_downloaded:
      # Remove video vile if it was downloaded by this method
      os.remove(video_file)

  return created_ad_id


def open_csv(filename, mode):
  """Open a csv file in proper mode depending on Python verion"""
  mode = mode + 'b' if sys.version_info[0] == 2 else mode
  return open(filename, mode)


def main(argv):
  """Main function

  Args:
    argv: Command-line arguments
  """
  # Retrieve command line arguments.
  flags = video_uploader.process_args(argv, argparser)

  profile_id = flags.profile_id
  campaign_id = flags.campaign_id
  placement_id = flags.placement_id
  advertiser_id = flags.advertiser_id
  creatives_list = flags.creatives_list
  success_file = flags.success_file
  failure_file = flags.failure_file

  # Create and initialize VideoUploader
  uploader = video_uploader.VideoUploader(
      profile_id, advertiser_id, campaign_id, placement_id)
  uploader.initialize(flags)

  new_ads = []

  # Open and process CSV file with all videos to be uploaded
  with open(creatives_list) as csvfile, \
    open_csv(success_file, 'w') as success_csv, \
    open_csv(failure_file, 'w') as failure_csv:

    # Create CSV readers and writers
    reader = csv.DictReader(csvfile)
    success_writer = csv.writer(success_csv)
    failure_writer = csv.writer(failure_csv)

    for row in reader:
      new_ad_id = process_row(row, uploader, failure_writer)
      # If ad could be created, add its ID to the list of created ads
      if new_ad_id:
        new_ads.append(new_ad_id)

    # Activate all newly created ads
    logger.info("Activating ads...")
    uploader.activate_all_ads(new_ads, success_writer)



if __name__ == '__main__':
  main(sys.argv)
