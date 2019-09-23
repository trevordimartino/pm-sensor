# PM Sensing with an SDS011


### Quickstart `pipenv` and `python 3.7+` installed
1. In the main project directory run `pipenv install` (see `Pipfile` for dependency list)
1. Put the path to your Firebase admin key file into the `GOOGLE_APPLICATION_CREDENTIALS` environment variable
    * If you need an admin key, sign up for a free Firebase account and start a new project with a `firestore` back end
    * Go to the Firebase project settings and, under the *Service accounts* tab, generate a new private Firebase Admin key (with Edit Project permissions)
    * Save the key file (JSON format is great) in a suitable location
1. Update `log_to_firestore.py` script with proper device location
    * You can `ls /dev` before and after plugging in the sensor to find the `tty*` device path it mounts to
1. Run `pipenv run python log_to_firestore.py` to log a few readings to your firestore instance
