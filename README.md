# ⚠️ Update, Feb 2025 

As of Firefox 128, all releases are fully managed in Mozilla Central. We are archiving this Github repository as of Feb 7, 2025. Please refer to our [Wiki announcement](https://github.com/mozilla-mobile/firefox-android/wiki#upcoming-migration-to-mozilla-central) for more context.



# RelBot
__Stefan Arentz, October 2020__

Small toolbox of scripts to automate a bunch of things we now mostly do manually:

 - Update Android-Components to new GeckoView (Beta) releases
 - Creating Android-Components Releases
 - Pulling a new Android-Components release into Fenix

Work in progress.

### Running with Docker

```
$ docker build -t relbot .
$ docker run -it --rm relbot ...command...
```

### Development

```sh
python3 -m venv env
source env/bin/activate
pip install --require-hashes -r requirements/dev.txt
pre-commit install --install-hooks
```

### Testing

Testing runs against GitHub repositories.
You will quickly run into its rate limiting.
This can be avoided by using a Personal Access Token.

Go to <https://github.com/settings/tokens> and create a new token (no additional scopes necessary).
Set it in your shell:

```
export GITHUB_TOKEN=<the generated token>
```

You can then run the tests:

```
pytest
```

Note: testing might fail due to changing upstream repositories.


### Update dependencies

```
maintenance/pin.sh
```

Then review and commit the changes. Create a new pull requests.
