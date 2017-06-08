# video_uploader.py

video_uploader.py contains an example implementation of a Python class
that helps with creating and activating targeted video ads in DCM.

For more information, please check PyDocs in video_uploader.py

# upload_videos.py

This script uploads videos to DCM and sets geo-targeting from a CSV file

This script processes a CSV file containing a description of a set of videos.
It uploads each video to DCM, creating a new Ad for each video. Each Ad
is targeted to a given geo location based on the information on the input CSV.
All Ads are created inside a single placement that is also taken as CLI
parameters.

The script makes use of OAuth 2.0 credentials to access DCM APIs. You
would need to place your credentials on a 'client_secrets.json' file in the
execution directory. You can follow the instructions available at
https://developers.google.com/doubleclick-advertisers/getting_started. In
order to perform the OAuth authentication from the command-line, you may need
to execute the script with the option '--noauth_local_webserver'

For a description of all the arguments please execute the script with
the argument --help

# Dependencies installation


```
$ make
```
