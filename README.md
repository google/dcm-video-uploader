This project contains a reference implementation of a video uploading script for DCM.
The main puporse of the script is to traffic DCM campaigns with hundreds or thousands of videos,
each one targeted to a different location. The script uploads all the videos to DCM and creates
the campaign structure (Ads, creatives) under the provided DCM Placement.

The script can be easily adapted for other types of targeting by including it in the ad definition
(see `video_uploader.py:VideoUploader._assign_creative_to_placement()`).

The script processes a CSV file containing a description of a set of videos.
It uploads each video to DCM, creating a new Ad for each video. Each Ad
is targeted to a given geo location based on the information on the input CSV.
All Ads are created inside a single placement that is also taken as CLI
parameters.

## Dependencies installation

In order to install dependencies for the script, run
```
$ pip install -r requirements.txt
```

## Running the script

### Before first run
The script makes use of OAuth 2.0 credentials to access DCM APIs. You
would need to place your credentials on a 'client_secrets.json' file in the
execution directory. You can follow the instructions available at
https://developers.google.com/doubleclick-advertisers/getting_started. In
order to perform the OAuth authentication from the command-line, you may need
to execute the script with the option `--noauth_local_webserver`

### Execution
In order to run the script, use the following command:
```
$ python upload_videos.py [arguments]
```
You must provide, at least, the following arguments:
* `profile_id`: The ID of the DCM use profile to use. You will need a profile with
write access to the advertiser and campaign where you want to add the videos.
* `advertiser_id`: The ID of the advertiser to use. This is where all new video
creatives will be added.
* `campaign_id`: The ID of the campaign where the dynamic creative structure will be added
* `placement_id`: The ID of the DCM placement inside which ads will be created
* `creatives_list`: CSV file with one row per creative. The following columns are
expected in the file: *Filename*, *File URL*, *Creative name*, *ZIP*, *Landing URL*. *Filename*
column may be empty as long as *File URL* has a value. The rest of the columns are all required
* `success_file`: Output CSV with ads created. The script will write here the list of all
the ads that were successfully created
* `failure_file`: Output CSV with ads that could not be created. If for any reason any of the
ads could not be created, you will find the reason in this file


For a full description on how to execute the script, run
```
$ python upload_videos.py --help
```

## Files overview

A description of the main files part of the script follows


### upload_videos.py

This is the entry point for the CLI script. It contains the argument parsing and makes
use of `video_uploader.py` to actually perform video upload and trafficking

For more information, please check PyDocs in `upload_videos.py`

### video_uploader.py

This file contains an example implementation of a Python class
that helps with creating and activating targeted video ads in DCM.

For more information, please check PyDocs in `video_uploader.py`


