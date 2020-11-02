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

```
$ python3 -m venv env
$ pip install -r requirements.txt
$ pip install pytest
```

