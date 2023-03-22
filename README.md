# Connector market-2-tour

## Installation

The `requirements.txt` and `Pipenv` files are provided for the setup of an environment where the module can be installed. The package includes a `setup.py` file and it can be therefore installed with a `pip install .` when we are at the same working directory as the `setup.py` file. For testing purposes, one can also install the package in editable mode `pip install -e .`.

After the install is completed, an executable `mkt2tour` will be available to the user.

Furthermore, a `Dockerfile` is provided so that the user can package the parcel generation model. To build the image the following command must be issued from the project's root directory:

```
docker build -t parcelmkt-2-parceltour:latest .
```

## Usage

```
$ mkt2tour -h
usage: mkt2tour [-h] [-v] [--flog] [-e ENV] parcels_tripsL2L parcel_trips_L2L_delivery parcel_trips_L2L_pickup parcel_HubSpoke ZONES PARCELNODES OUTDIR

mkt2tour connector

positional arguments:
  parcels_tripsL2L      The path of the parcel trips file (csv)
  parcel_trips_L2L_delivery
                        The path of the parcel delivery file (csv)
  parcel_trips_L2L_pickup
                        The path of the parcel pickup file (csv)
  parcel_HubSpoke       The path of the parcel hubspoke file (csv)
  ZONES                 The path of the area shape file (shp)
  PARCELNODES           The path of the parcel nodes file (shp)
  OUTDIR                The output directory

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbosity       Increase output verbosity (default: 0)
  --flog                Stores logs to file (default: False)
  -e ENV, --env ENV     Defines the path of the environment file (default: None)
```

Furthermore, the following parameters must be provided as environment variables either from the environment itself or through a dotenv file that is specified with the `--env <path-to-dotenv>` optional command line argument. An example of the `.env` file and some values is presented below.

```
# array of strings
Gemeenten_studyarea=sGravenhage
```

## Execution

```
mkt2tour -vvv --env .env \
    sample-data/input/ParcelDemand_ParcelTrips.csv \
    sample-data/input/ParcelDemand_HS_delivery.csv \
    sample-data/input/ParcelDemand_HS_pickup.csv \
    sample-data/input/ParcelDemand_ParcelHubSpoke.csv \
    sample-data/input/Zones_v4.zip \
    sample-data/input/parcelNodes_v2Cycloon.zip \
    sample-data/output/
```

```
docker run --rm \
  -v $PWD/sample-data:/data \
  --env-file .env \
  parcelmkt-2-parceltour:latest \
  /data/input/ParcelDemand_ParcelTrips.csv \
  /data/input/ParcelDemand_HS_delivery.csv \
  /data/input/ParcelDemand_HS_pickup.csv \
  /data/input/ParcelDemand_ParcelHubSpoke.csv \
  /data/input/Zones_v4.zip \
  /data/input/parcelNodes_v2.zip \
  /data/output/
```
