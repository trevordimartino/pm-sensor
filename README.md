# PM Sensing with an SDS011
A sensor object for use with the SDS011 particulate matter sensor, with a demo script that takes measurements and uploads them to Google Firebase.  Written in Python 3.7, but will likely work with any Python version >3.

### Quickstart
1. In the main project directory run `pipenv install` (see `Pipfile` for dependency list)
1. Put the path to your Firebase admin key file into the `GOOGLE_APP_CREDS_PATH` variable at the top of `log_to_firestore.py`
    * If you need an admin key, sign up for a free Firebase account and start a new project with a `firestore` back end
    * Go to the Firebase project settings and, under the *Service accounts* tab, generate a new private Firebase Admin key (with Edit Project permissions)
    * Save the key file (JSON format is great) in a suitable location
1. Update `log_to_firestore.py` script with proper device location
    * You can `ls /dev` before and after plugging in the sensor to find the `/dev/tty*` device path it mounts to
1. Run `pipenv run python log_to_firestore.py` to log a few readings to your firestore instance

If you want to change how often readings are taken, update the `WORK_PERIOD` variable at the top of `log_to_firestore.py`
