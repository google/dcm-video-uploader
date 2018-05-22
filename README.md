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

## Execution

For a full description on how to execute the script, run
```
python upload_videos.py --help
```
The script makes use of OAuth 2.0 credentials to access DCM APIs. You
would need to place your credentials on a 'client_secrets.json' file in the
execution directory. You can follow the instructions available at
https://developers.google.com/doubleclick-advertisers/getting_started. In
order to perform the OAuth authentication from the command-line, you may need
to execute the script with the option `--noauth_local_webserver`

## Main files

A description of the main files part of the script follows


### upload_videos.py

This is the entry point for the CLI script. It contains the argument parsing and makes
use of `video_uploader.py` to actually perform video upload and trafficking

For more information, please check PyDocs in `upload_videos.py`

### video_uploader.py

This file contains an example implementation of a Python class
that helps with creating and activating targeted video ads in DCM.

For more information, please check PyDocs in `video_uploader.py`


