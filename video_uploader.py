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

"""This module contains an example of how to upload video creatives to DCM
by using DCM Trafficking API

The module makes use of Python Google API client library, which is available
at https://developers.google.com/api-client-library/python/ You will need to
install them to be able to use this script.

Additionally, you will also need to place a copy of dfareporting_utils.py,
available on the DCM samples library at https://github.com/googleads/googleads-dfa-reporting-samples/tree/master/python/v2_7

You will also need retrying library, which is available under Apache 2.0
license (check NOTICE.txt for more information). Retrying is available at
https://pypi.python.org/pypi/retrying

The module makes use of OAuth 2.0 credentials to access DCM APIs. You
would need to place your credentials on a 'client_secrets.json' file in the
execution directory. You can follow the instructions available at
https://developers.google.com/doubleclick-advertisers/getting_started. In
order to perform the OAuth authentication from the command-line, you may need
to execute your script with the option '--noauth_local_webserver'
"""

import logging
import re
import dfareporting_utils
import time
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from retrying import retry

AD_NAME_PREFIX = "AD_"

# Configure logging
logger = logging.getLogger(__name__)
if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)

def clean_up_creative_name(name):
  return re.sub('[^0-9a-zA-Z\.=\-_]+', '_', name)

def _is_server_error(error):
  """Check whether an error is an internal server error.

  This function checks if an error is an internal server error (error 500).

  Args:
    error: Error object as raised by any method accessing server API.
  Returns:
    True if error is HttpError and is an internal server error (500). False
    otherwise.
  """
  result = False
  if isinstance(error, HttpError):
    #If it's a server error, retry
    if error.resp.status > 499 and error.resp.status < 600:
      logger.warning("Server error. Retrying...")
      result = True
    else:
      logger.error("Not server error. Not retrying")
  else:
    logger.error("Not server error. Not retrying")
  return result

@retry(
    wait_exponential_multiplier=1000,
    stop_max_delay=3600000,
    wait_exponential_max=20000,
    retry_on_exception=_is_server_error)
def _execute_with_retries(request):
  """Executes a request, retrying with exponential backup.

  Args:
    request: Request to be executed.

  Returns:
    Response from server.
  """
  return request.execute()

def process_args(argv, parent_argparser):
  """Process command line arguments.

  This method processes command-line arguments. It extracts arguments needed
  by Google API client and returns an object containing those arguments plus
  any other arguments that may have been defined by the invoking script in
  the parent_argparser. The result of this method can be later used to
  initialize an instance of VideoUploader.

  Args:
    argv: Command-line parameters.
    parent_argparser: an argparse.ArgumentParser instance with any user-defined
        command-line parameters

  Returns:
    Object with all command-line parameters. This object contains all the
    parameters defined in parent_argparser, plus the parameters
    needed/supported by Google API Client
  """
  return dfareporting_utils.get_arguments(
      argv, __doc__, parents=[parent_argparser])

class VideoUploader(object):
  """Class to upload videos to DCM and activate them.

  This class provides methods to upload videos to DCM and create ads with
  geographic targeting with those videos associated.

  In order to use this class you must create an instance and then call
  initialize() before invoking any other method.

  The basic use case is the following:
    1. Construct object of this class
    2. Call initialize()
    3. Call new_video() for each video that you want to add. Store the returned
      ad ID for each invocation
    4. Call activate_all_ads() and pass the list of all ad IDs created by
      calling new_video() on step 3

  After adding a video, DCM takes some time to process and transcode the video
  file. You can't activate the ad until the video has been processed. By
  uploading all the videos first (step 3) and activating them afterwards
  (step 4) we are giving DCM time to transcode the videos while we upload other
  videos before proceeding to try to activate all of them. activate_all_ads()
  will try to activate all. The method atuomatically retries activation on
  those videos that cannot be activated on a first round. That way,
  if any of them fails because transcoding hasn't finished yet it has nother
  opportunities. Retries are done on an exponential back-off pattern.
  """

  def __init__(self, user_profile, advertiser_id, campaign_id, placement_id):
    """Constructor for VideoUploader.

    Args:
      user_profile: User profile ID to to log into DCM API.
        You must use a user profile that has write access to the advertiser
        under which you are going to add the new videos. You may get your user
        profile ID directly from DCM User Interface
      advertiser_id: ID of the advertiser under which you want to add the new
        videos
      campaign_id: ID of the campaign under which you want to add the new videos
      placement_id: ID of the placement under which you want to add the new
        videos
    """
    self._profile_id = user_profile
    self._campaign_id = campaign_id
    self._placement_id = placement_id
    self._advertiser_id = advertiser_id

  def initialize(self, flags):
    """Initialize this instance of VideoUploader.

    You must invoke this method before any other method on any instance of this
    class.

    Args:
      flags: result fo processing command line arguments. You must pass the
          output of process_args() method on this same module
    """
    self._service = dfareporting_utils.setup(flags)
    self._campaign = self._get_element_by_id('campaigns', self._campaign_id)

  
  def _upload_asset(self, asset_name, video_file):
    """Upload video asset.

    Before creating a new video creative on DCM, you need to upload the assets
    (actual video files). This method uploads the video file to DCM and gets
    the newly generated asset ID. You can later use this asset ID to associate
    the video asset to a new video creative on DCM.
    See https://support.google.com/dcm/answer/3312854?hl=en

    Args:
      asset_name: Name that will be used for the new video asset on DCM
      video_file: Video filename

    Returns:
      dfareporting#creativeAssetMetadata object with metadata about the newly
      created CreativeAsset (see DCM API documentation for more info)
    """
    # Construct the creative asset metadata
    creative_asset = {
        'assetIdentifier': {
            'name': asset_name,
            'type': "VIDEO"
        }
    }
    # Upload the asset and return the generated asset identifier
    logger.info("Uploading asset '%s'", asset_name)
    media = MediaFileUpload(video_file)
    if not media.mimetype():
      media = MediaFileUpload(video_file, 'application/octet-stream')
    response = self._service.creativeAssets().insert(
        advertiserId=self._advertiser_id,
        profileId=self._profile_id,
        media_body=media,
        body=creative_asset).execute()
    logger.info(
        "Asset uploaded. Name: '%s'",response['assetIdentifier']['name'])
    return response['assetIdentifier']


  def _add_video_creative(self, creative_desired_name, video_file, landing_url):
    """Create new video creative on DCM.

    This method creates a new video creative on DCM.

    Args:
      creative_desired_name: Name for the new creative. This might differ from
        the actual final name since DCM might introduce sequence digits to
        distinguish from already existing creatives.
      video_file: Video file name.
      landing_url: Landing URL for the newly added creative

    Returns:
      Dict object with 'creative_id' and 'creative_name' for the newly added
      creative

    Raises:
      HttpError: An error occured while sending requests to the server after
        a number of retries
    """
    # First, upload video to create new video asset
    asset_id = self._upload_asset(creative_desired_name, video_file)

    creative_name = asset_id['name']
    # Construct the creative structure with the new video asset linked
    creative = {
        'advertiserId': self._advertiser_id,
        'clickTags': [{
            'eventName': 'exit',
            'name': 'click_tag',
            'value': landing_url
        }],
        'creativeAssets': [{
            'assetIdentifier': asset_id,
            'role': 'PARENT_VIDEO',
            'active': 'true'},],
        'name': creative_name,
        'type': 'INSTREAM_VIDEO',
        'active': 'false'
    }

    # Send request to DCM to actually add the creative
    request = self._service.creatives().insert(
        profileId=self._profile_id, body=creative)
    response = _execute_with_retries(request)

    # Get the ID for the newly created creative
    creative_id = response['id']

    # Now, add the creative to the campaign
    association = {
        'creativeId': creative_id
    }
    request = self._service.campaignCreativeAssociations().insert(
        profileId=self._profile_id,
        campaignId=self._campaign_id, body=association)
    response = _execute_with_retries(request)

    return {'creative_id': int(creative_id), 'creative_name': creative_name}


  def _get_element_by_id(self, type_of_element, element_id):
    """Get DCM element by ID.

    This method retrives the object with the specified ID from the DCM API.

    Args:
      type_of_element: The type of element to be retrieved. Use 'ads',
        'creatives', 'campaigns', etc.
      element_id: ID of the element we want to retrieve

    Returns:
      Object of the type that was requested (see DCM API documentation for the
      different types of objects)

    Raises:
      Exception: If the exact number of found elements for that ID and type was
        not 1
    """
    # Invoke method for listing elements (access method is based on the type
    # of the elements we want to retrieve
    access_mehod = getattr(self._service, type_of_element)
    request = access_mehod().list(
        profileId=self._profile_id, ids=element_id)
    response = _execute_with_retries(request)

    # Check for number of elements found and return element
    if len(response[type_of_element]) != 1:
      raise Exception("Not one single {} with ID: {}".format(
          type_of_element, element_id))
    return response[type_of_element][0]


  def _assign_creative_to_placement(
      self, ad_name, creative_id, placement_id, target_zip, landing_url):
    """Assign creative to placement.

    This method assigns a creative to a placement. This assigment is done via an
    ad. Thus, this method effectively creates a new ad, assigns the creative to
    the ad, and the ad to the placement.

    This method also adds a geografic (ZIP code) targeting to the newly created
    ad, so that the ad is only shown to users located in that ZIP code.

    Args:
      ad_name: Name of the new ad to create to make the assigment
      creative_id: ID of the creative to be assigned
      placement_id: ID of the creative to be assigned
      target_zip: ZIP code where we want the newly created ad to be shown
      landing_url: Landing page for the ad-creative association

    Returns:
      Dict object with info about the newly created ad: 'ad_name' and 'ad_id'

    Raises:
      HttpError: An error occured while sending requests to the server after
        a number of retries
    """

    # Construct and save ad.
    creative_assignment = {
        'active': 'true',
        'creativeId': creative_id,
        'clickThroughUrl': {
          'defaultLandingPage': 'false',
          'customClickThroughUrl': landing_url
        }
    }
    creative_rotation = {
        'creativeAssignments': [creative_assignment],
        'type': 'CREATIVE_ROTATION_TYPE_RANDOM',
        'weightCalculationStrategy': 'WEIGHT_STRATEGY_EQUAL'
    }
    placement_assignment = {
        'active': 'true',
        'placementId': placement_id,
    }
    delivery_schedule = {
        'impressionRatio': '1',
        'priority': 'AD_PRIORITY_01'
    }

    # Ad definition
    # Current implementation supports only Geo targeting.
    # In order to add support for additional targetings, you should include
    # the targeting in the Ad descriptor here. See https://developers.google.com/doubleclick-advertisers/v3.0/ads
    # for details on how to specify other targeting criteria.
    ad = {
        'active': 'false',
        'campaignId': self._campaign_id,
        'creativeRotation': creative_rotation,
        'deliverySchedule': delivery_schedule,
        'endTime': '%sT00:00:00Z' % self._campaign['endDate'],
        'name': ad_name,
        'placementAssignments': [placement_assignment],
        'startTime': '%sT23:59:59Z' % time.strftime('%Y-%m-%d'),
        'type': 'AD_SERVING_STANDARD_AD',
        'advertiserId': self._advertiser_id,
        'geoTargeting': {
            "postalCodes": [
                {
                    "kind": "dfareporting#postalCode",
                    "id": target_zip,
                    "code": target_zip,
                    "countryCode": 'US',
                    "countryDartId": '256'
                  }
            ]
        }
    }
    request = self._service.ads().insert(profileId=self._profile_id, body=ad)

    # Execute request
    response = _execute_with_retries(request)

    # Get newly generated id and name and return them
    ad_id = int(response['id'])
    ad_name = response['name']

    return {'ad_name': ad_name, 'ad_id': ad_id}


  def new_video(self, creative_name, video_file, target_zip_code,
                   landing_url):
    """Add new video to DCM.

    This method creates adds a new video to DCM and sets all the necessary
    elements so that the video is served on the specified target location (ZIP
    code).

    After executing this method, your campaign will contain a new Ad with the
    provided video. The ad will be in paused state. You must activate the ad
    if you want the video to be served. You may use
    VideoUploader.activate_all_ads() method for that.

    Args:
      creative_name: Name for the new creative on DCM. You must use a string
        returned by the clean_up_creative_name() method on this module to
        ensure it is a valid name for a creative on DCM.
      video_file: Video filename.
      target_zip_code: ZIP code to which this video must be targeted. The video
        will only be shown to users who see the ad on that location.
      landing_url: Landing URL for the ad when showing this specific video.

    Returns:
      ID of the newly created ad.

    Raises:
      HttpError: An error occured while sending requests to the server after
        a number of retries
    """
    creative_info = self._add_video_creative(
        creative_name, video_file, landing_url)

    creative_id = creative_info['creative_id']
    creative_name = creative_info['creative_name']

    logger.info(
        "Added creative '%s' (ID: %d)",creative_name, creative_id)

    return self._assign_creative_to_placement(AD_NAME_PREFIX + creative_name,
        creative_id, self._placement_id, target_zip_code, landing_url)['ad_id']


  def _activate_ad(self, ad_id):
    """Activate one single ad.

    This method activates one single ad on DCM.

    Args:
      ad_id: ID of the ad to be activated.

    Returns:
      True if the ad is active after the execution. False if the ad could not
      be activated
    """
    active = False
    ad = self._get_element_by_id('ads', ad_id)
    if ad['active'] != 'true':
      creative_assignments = ad['creativeRotation']['creativeAssignments']
      if len(creative_assignments) != 1:
        logger.error("Cannot activate ad '%s'. It has %d assigments",
            ad_id, len(creative_assignments))
      else:
        creative_id = creative_assignments[0]['creativeId']
        creative = self._get_element_by_id('creatives', creative_id)
        try:
          creative['active'] = 'true'
          request = self._service.creatives().update(
                profileId = self._profile_id, body = creative)
          ad['active'] = 'true'
          request = self._service.ads().update(
              profileId = self._profile_id, body = ad)
          request.execute()
          active = True
        except:
          logger.warning("Couldn't activate ad ID '%s'. Skipping", ad_id)
    else:
      logger.info("Nothing to do because ad '%s' is already active", ad_id)
      active = True
    return active

  @retry(
    wait_exponential_multiplier=1000,
    stop_max_delay=7200000,
    wait_exponential_max=20000)
  def activate_all_ads(self, ad_ids, success_writer):
    """Activate a list of ad IDs.

    This method iterates through a list of ad ids to activate them all. The
    method execute a series of retries, so if an ad cannot be activated,
    activation is retried after a certain time (exponential back-off).

    Args:
      ad_ids: List of ad IDs to be activated.
      success_writer: csv writer. All ads that were successfully activated will
        be noted in this file

    Raises:
      Exception: If after all retries, not all ads could be activated, or
        if an unexpected Exception is raised while invoking DCM API
    """
    try:
      logger.info("Activating %d ads", len(ad_ids))
      for current_ad_id in ad_ids:
        if self._activate_ad(current_ad_id):
          ad_ids.remove(current_ad_id)
          success_writer.writerow([current_ad_id])
      if len(ad_ids) != 0:
        logger.info("Ads pending activation: %d", len(ad_ids))
        raise Exception("Not all ads were activated")
      logger.info("All ads activated")
    except Exception as e:
      logger.warning("Exception while activating ads: %s", e)
      raise
    except:
      logger.error("Unexpected exception while activating ads")
      raise


