"""Processing module
"""

from os.path import join
from time import time
from logging import getLogger

import pandas as pd
import numpy as np

from .utils import read_shape

logger = getLogger("gen2mkt.proc")

def run_model(cfg):
    start_time = time()

    logger.info('Importing data...')

    zones = read_shape(cfg['ZONES'])
    zones.index = zones['AREANR']
    nZones = len(zones)

    zoneDict  = dict(np.transpose(np.vstack( (np.arange(1,nZones+1), zones['AREANR']) )))
    zoneDict  = {int(a):int(b) for a,b in zoneDict.items()}
    invZoneDict = dict((v, k) for k, v in zoneDict.items()) 

    parcelNodes = read_shape(cfg['PARCELNODES'], returnGeometry=False)
    parcelNodes.index = parcelNodes['id'].astype(int)
    parcelNodes = parcelNodes.sort_index()    

    for node in parcelNodes['id']:
        parcelNodes.loc[node,'SKIMNR'] = int(invZoneDict[parcelNodes.at[int(node),'AREANR']])
    parcelNodes['SKIMNR'] = parcelNodes['SKIMNR'].astype(int)
    
    parcels_tripsL2L = pd.read_csv(cfg['parcels_tripsL2L']); parcels_tripsL2L.index = parcels_tripsL2L['Parcel_ID']
    parcel_trips_L2L_delivery = pd.read_csv(cfg['parcel_trips_L2L_delivery'])
    parcel_trips_L2L_pickup =  pd.read_csv(cfg['parcel_trips_L2L_pickup'])
    parcel_HubSpoke        =  pd.read_csv(cfg['parcel_HubSpoke'])
    parcels_hubhub = parcels_tripsL2L[((parcels_tripsL2L['Network'] == 'conventional') & (parcels_tripsL2L['Type'] == 'consolidated'))]

    error=0
    parcels_hubhub.insert(3, 'DepotNumber', np.nan) #add depotnumer column
    for index, parcel in parcels_hubhub.iterrows(): #loop over parcels
        try:
            parcels_hubhub.at[index, 'DepotNumber'] = parcelNodes[((parcelNodes['CEP'] == parcel['CEP']) & (parcelNodes['AREANR'] == parcel['O_zone']))]['id'] #add depotnumer to each parcel
        except:
            parcels_hubhub.at[index, 'DepotNumber'] = parcelNodes[((parcelNodes['CEP'] == parcel['CEP']))]['id'].iloc[0] # Get first node as an exception
            error +=1
    parcels_hubhub.to_csv(join(cfg['OUTDIR'], "ParcelDemand_Hub2Hub.csv"), index=False)
    parcels_hubspoke_delivery = parcel_trips_L2L_delivery

    Gemeenten = cfg['Gemeenten_studyarea']
    if len(Gemeenten) > 1:  # If there are more than 1 gemente in the list
        parcels_hubspoke_deliveryIter = pd.DataFrame(columns = parcels_hubspoke_delivery.columns)
    
        for Geemente in Gemeenten:
            if type (Geemente) != list: # If there the cities are NOT connected (that is every geemente is separated from the next)
                ParcelTemp = parcels_hubspoke_delivery[parcels_hubspoke_delivery['D_zone'].isin(zones['AREANR'][zones['GEMEENTEN']==Geemente])] #only take parcels picked-up in the study area
                parcels_hubspoke_deliveryIter = parcels_hubspoke_deliveryIter.append(ParcelTemp)
            else:
                ParcelTemp = parcels_hubspoke_delivery[parcels_hubspoke_delivery['D_zone'].isin(zones['AREANR'][zones['GEMEENTEN'].isin(Geemente)])]
                parcels_hubspoke_deliveryIter = parcels_hubspoke_deliveryIter.append(ParcelTemp)
        parcels_hubspoke_delivery = parcels_hubspoke_deliveryIter
    else:    # print(len(ParceltobeL2L))
        if type (Gemeenten[0]) == list:
            Geemente = Gemeenten [0]
        else:
            Geemente = Gemeenten
        parcels_hubspoke_delivery = parcels_hubspoke_delivery[parcels_hubspoke_delivery['D_zone'].isin(zones['AREANR'][zones['GEMEENTEN'].isin(Geemente)])] #only take parcels picked-up in the study area

    parcel_HubSpoke['Network']='conventional'
    parcel_HubSpoke['Type']='tour-based'

    cols =  ['Parcel_ID', 'O_zone', 'D_zone', 'DepotNumber', 'CEP', 'VEHTYPE', 'Network', 'Type']    
    parcel_HubSpoke = parcel_HubSpoke[cols]
    parcels_hubspoke_delivery = parcels_hubspoke_delivery.append(parcel_HubSpoke)
    parcels_hubspoke_delivery = parcels_hubspoke_delivery.drop(['Network', 'Type'], axis=1)
    parcels_hubspoke_delivery['Task'] = ['Delivery'] * len(parcels_hubspoke_delivery)

    parcels_hubspoke_pickup = parcel_trips_L2L_pickup
    parcels_hubspoke_pickup['Task'] = ['PickUp'] * len(parcels_hubspoke_pickup)

    Gemeenten = cfg['Gemeenten_studyarea']
    if len(Gemeenten) > 1:  # If there are more than 1 gemente in the list
        parcels_hubspoke_pickupIter = pd.DataFrame(columns = parcels_hubspoke_pickup.columns)
        for Geemente in Gemeenten:
            if type (Geemente) != list: # If there the cities are NOT connected (that is every geemente is separated from the next)
                ParcelTemp = parcels_hubspoke_pickup[parcels_hubspoke_pickup['O_zone'].isin(zones['AREANR'][zones['GEMEENTEN']==Geemente])] #only take parcels picked-up in the study area
                parcels_hubspoke_pickupIter = parcels_hubspoke_pickupIter.append(ParcelTemp)
            else:
                ParcelTemp = parcels_hubspoke_pickup[parcels_hubspoke_pickup['O_zone'].isin(zones['AREANR'][zones['GEMEENTEN'].isin(Geemente)])]
                parcels_hubspoke_pickupIter = parcels_hubspoke_pickupIter.append(ParcelTemp)
        parcels_hubspoke_pickup = parcels_hubspoke_pickupIter
    else:    # print(len(ParceltobeL2L))
        if type (Gemeenten[0]) == list:
            Geemente = Gemeenten [0]
        else:
            Geemente = Gemeenten
        parcels_hubspoke_pickup = parcels_hubspoke_pickup[parcels_hubspoke_pickup['O_zone'].isin(zones['AREANR'][zones['GEMEENTEN'].isin(Geemente)])] #only take parcels picked-up in the study area
    
    parcels_hubspoke_pickup = parcels_hubspoke_pickup.append(parcel_trips_L2L_pickup, ignore_index=True,sort=False)
    parcels_hubspoke_pickup = parcels_hubspoke_pickup.drop(['Network', 'Type'], axis=1)
    
    parcels_hubspoke_pickup = parcels_hubspoke_pickup.rename(columns={'O_zone': 'D_zone', 'D_zone': 'O_zone'}) #Scheduling module only works originating from depots
    parcels_hubspoke_pickup['DepotNumber'] = (parcels_hubspoke_pickup['DepotNumber']+1000).astype(int)
    parcels_hubspoke_pickup = parcels_hubspoke_pickup.drop_duplicates()
    
    parcels_hubspoke_Hague = parcels_hubspoke_delivery.append(parcels_hubspoke_pickup, ignore_index=True, sort=False)
    parcels_hubspoke_Hague.to_csv(join(cfg['OUTDIR'], "ParcelDemand.csv"), index=False)
