# -*- coding: utf-8 -*-
"""
Created on Wed Oct 27 09:00:27 2021

@author: rtapia
"""
from __functions__ import read_mtx, read_shape, create_geojson, get_traveltime, get_distance
import pandas as pd
import numpy as np
import networkx as nx
from itertools import islice, tee
import math
import sys, os
import time
import ast
import datetime as dt

# from  StartUp import *

#%% include B2C market to the conventional parcel assignment
'''
For both (delivery & pick-up), the C2C parcels are combined with the B2C market, to have the economy of scale
The B2C parcels are generated using the Parcel Demand module; 
First an origin is assigned (based on retail jobs). Next, the intermediate depots are found. Finally, the B2C parcels are splitted as well.
They are combined with the C2C market and fed into the Parcel Scheduling module.
'''
def actually_run_module(args):
    root    = args[0]
    varDict = args[1]
# TODO: Where to add the parcel lockers

    zones = read_shape(varDict['ZONES'])
    zones.index = zones['AREANR']
    nZones = len(zones)
    
    zoneDict  = dict(np.transpose(np.vstack( (np.arange(1,nZones+1), zones['AREANR']) )))
    zoneDict  = {int(a):int(b) for a,b in zoneDict.items()}
    invZoneDict = dict((v, k) for k, v in zoneDict.items()) 
    
    parcelNodesPath = varDict['PARCELNODES']
    parcelNodes = read_shape(parcelNodesPath, returnGeometry=False)
    parcelNodes.index   = parcelNodes['id'].astype(int)
    parcelNodes         = parcelNodes.sort_index()    
    
    for node in parcelNodes['id']:
        parcelNodes.loc[node,'SKIMNR'] = int(invZoneDict[parcelNodes.at[int(node),'AREANR']])
    parcelNodes['SKIMNR'] = parcelNodes['SKIMNR'].astype(int)
    
    ## Starts the connection
    parcels_tripsL2L = pd.read_csv(varDict['parcels_tripsL2L']); parcels_tripsL2L.index = parcels_tripsL2L['Parcel_ID']
    parcel_trips_L2L_delivery = pd.read_csv(varDict['parcel_trips_L2L_delivery'])
    parcel_trips_L2L_pickup =  pd.read_csv(varDict['parcel_trips_L2L_pickup'])
    parcel_HubSpoke        =  pd.read_csv(varDict['parcel_HubSpoke'])
  
    parcels_hubhub = parcels_tripsL2L[((parcels_tripsL2L['Network'] == 'conventional') & (parcels_tripsL2L['Type'] == 'consolidated'))]
    
    error=0
    parcels_hubhub.insert(3, 'DepotNumber', np.nan) #add depotnumer column
    for index, parcel in parcels_hubhub.iterrows(): #loop over parcels
        try:
            parcels_hubhub.at[index, 'DepotNumber'] = parcelNodes[((parcelNodes['CEP'] == parcel['CEP']) & (parcelNodes['AREANR'] == parcel['O_zone']))]['id'] #add depotnumer to each parcel
        except:
            parcels_hubhub.at[index, 'DepotNumber'] = parcelNodes[((parcelNodes['CEP'] == parcel['CEP']))]['id'].iloc[0] # Get first node as an exception
            error +=1
    parcels_hubhub.to_csv(f"{varDict['OUTPUTFOLDER']}ParcelDemand_Hub2Hub_{varDict['LABEL']}.csv", index=False)
    parcels_hubspoke_delivery = parcel_trips_L2L_delivery
   
    Gemeenten = varDict['Gemeenten_studyarea']
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
    
    Gemeenten = varDict['Gemeenten_studyarea']
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
    parcels_hubspoke_Hague.to_csv(f"{varDict['OUTPUTFOLDER']}ParcelDemand_{varDict['LABEL']}.csv", index=False)
    return ()

def generate_args(method):
    varDict = {}
   
    '''FOR ALL MODULES'''
    cwd = os.getcwd().replace(os.sep, '/')
    datapath = cwd.replace('Code', '')
    
    if method == 'from_file':   
            
        if sys.argv[0] == '':
            params_file = open(f'{datapath}/Input/Params_Conn_Market2Sched.txt')
            varDict['LABEL'	]			= 'FrancescoTest'			
            varDict['DATAPATH']			= datapath							
            varDict['INPUTFOLDER']		= f'{datapath}'+'/'+ 'Input' +'/' 				
            varDict['OUTPUTFOLDER']		= f'{datapath}'+'/'+ 'Output' +'/'				
            
            varDict['parcels_tripsL2L'] 		= varDict['INPUTFOLDER'] + 'ParcelDemand_ParcelTripsL2L_FrancescoTest.csv'
            varDict['parcel_trips_L2L_delivery']		= varDict['INPUTFOLDER'] + 'ParcelDemand_L2L_delivery_FrancescoTest.csv'
            varDict['parcel_trips_L2L_pickup']			= varDict['INPUTFOLDER'] + 		'ParcelDemand_L2L_pickup_FrancescoTest.csv'	
            varDict['parcel_HubSpoke']			= varDict['INPUTFOLDER'] + 		'ParcelDemand_ParcelHubSpoke_FrancescoTest.csv'	
          
            # varDict['SKIMTIME'] 		= varDict['INPUTFOLDER'] + sys.argv[6] #'skimTijd_new_REF.mtx' 		
            # varDict['SKIMDISTANCE']		= varDict['INPUTFOLDER'] + sys.argv[7] #'skimAfstand_new_REF.mtx'	
            varDict['ZONES']			= varDict['INPUTFOLDER'] + 'Zones_v4.shp' #'Zones_v4.shp'		
            # varDict['SEGS']				= varDict['INPUTFOLDER'] + sys.argv[9] #'SEGS2020.csv'				
            varDict['PARCELNODES']		= varDict['INPUTFOLDER'] + 'parcelNodes_v2.shp' #'parcelNodes_v2.shp'        

    
        else:  # This is the part for line cod execution
            locationparam = f'{datapath}' +'/'+ sys.argv[2] +'/' + sys.argv[4]
            params_file = open(locationparam)
            varDict['LABEL'	]			= sys.argv[1]				
            varDict['DATAPATH']			= datapath							
            varDict['INPUTFOLDER']		= f'{datapath}'+'/' + sys.argv[2] +'/' 				
            varDict['OUTPUTFOLDER']		= f'{datapath}'+'/' + sys.argv[3] +'/'			
            
            varDict['parcels_tripsL2L'] 		= varDict['INPUTFOLDER'] + sys.argv[5] #'skimTijd_new_REF.mtx' 		
            varDict['parcel_trips_L2L_delivery']		= varDict['INPUTFOLDER'] + sys.argv[6] #'skimAfstand_new_REF.mtx'	
            varDict['parcel_trips_L2L_pickup']			= varDict['INPUTFOLDER'] + sys.argv[7] #'Zones_v4.shp'				
            varDict['parcel_HubSpoke']			= varDict['INPUTFOLDER'] + 		 sys.argv[8]
            
            # varDict['SKIMTIME'] 		= varDict['INPUTFOLDER'] + sys.argv[6] #'skimTijd_new_REF.mtx' 		
            # varDict['SKIMDISTANCE']		= varDict['INPUTFOLDER'] + sys.argv[7] #'skimAfstand_new_REF.mtx'	
            varDict['ZONES']			= varDict['INPUTFOLDER'] + sys.argv[9] #'Zones_v4.shp'				
            # varDict['SEGS']				= varDict['INPUTFOLDER'] + sys.argv[9] #'SEGS2020.csv'				
            varDict['PARCELNODES']		= varDict['INPUTFOLDER'] + sys.argv[10] #'parcelNodes_v2.shp'
            # So it shuts up the warnings (remove when running in spyder)
            pd.options.mode.chained_assignment = None            
            
            
            
            
        for line in params_file:
            if len(line.split('=')) > 1:
                key, value = line.split('=')
                if len(value.split(';')) > 1:
                    # print(value)
                    value, dtype = value.split(';')
                    if len(dtype.split('#')) > 1: dtype, comment = dtype.split('#')
                    # Allow for spacebars around keys, values and dtypes
                    while key[0] == ' ' or key[0] == '\t': key = key[1:]
                    while key[-1] == ' ' or key[-1] == '\t': key = key[0:-1]
                    while value[0] == ' ' or value[0] == '\t': value = value[1:]
                    while value[-1] == ' ' or value[-1] == '\t': value = value[0:-1]
                    while dtype[0] == ' ' or dtype[0] == '\t': dtype = dtype[1:]
                    while dtype[-1] == ' ' or dtype[-1] == '\t': dtype = dtype[0:-1]
                    dtype = dtype.replace('\n',"")
                    # print(key, value, dtype)
                    if dtype == 'string': varDict[key] = str(value)
                    elif dtype == 'list': varDict[key] = ast.literal_eval(value)
                    elif dtype == 'int': varDict[key] = int(value)               
                    elif dtype == 'float': varDict[key] = float(value)               
                    elif dtype == 'bool': varDict[key] = eval(value)               
                    elif dtype == 'variable': varDict[key] = globals()[value]
                    elif dtype == 'eval': varDict[key] = eval(value)


            
            
    elif method == 'from_code':
        print('Generating args from code')
        varDict['RUN_DEMAND_MODULE']            = False
        varDict['CROWDSHIPPING_NETWORK']        = True
        varDict['COMBINE_DELIVERY_PICKUP_TOUR'] = True
        varDict['HYPERCONNECTED_NETWORK']       = True
        
        varDict['LABEL']                = 'C2C'
        varDict['DATAPATH']             = datapath + '/'
        varDict['INPUTFOLDER']          = varDict['DATAPATH']+'Input/'
        varDict['OUTPUTFOLDER']         = varDict['DATAPATH']+'Output/'
        # varDict['PARAMFOLDER']	        = f'{datapath}Parameters/Mass-GT/'
        
        varDict['SKIMTIME']             = varDict['INPUTFOLDER'] + 'skimTijd_new_REF.mtx'
        varDict['SKIMDISTANCE']         = varDict['INPUTFOLDER'] + 'skimAfstand_new_REF.mtx'
        varDict['ZONES']                = varDict['INPUTFOLDER'] + 'Zones_v4.shp'
        varDict['SEGS']                 = varDict['INPUTFOLDER'] + 'SEGS2020.csv'
        varDict['PARCELNODES']          = varDict['INPUTFOLDER'] + 'parcelNodes_v2.shp'
        varDict['CEP_SHARES']           = varDict['INPUTFOLDER'] + 'CEPshares.csv'
        varDict['Pax_Trips']            = varDict['INPUTFOLDER'] + 'trips.csv'
        
       
        # Hague
        varDict['Gemeenten_CS']         = ["sGravenhage", "Zoetermeer", "Midden_Delfland"]
        varDict['SCORE_ALPHAS']         = [0, 0, 0.1, 1]
        varDict['SCORE_COSTS']          = [0.2, .02, .02, 0,0] # tour_based, consolidated, hub, cs_trans, #interCEP_cost
        varDict['CONSOLIDATED_MAXLOAD'] = 500
        
        '''FOR PARCEL DEMAND MODULE'''
        # Changed parameters to C2X ACM post&pakketmonitor2020 20.8M parcels 
        varDict['PARCELS_PER_HH_C2C']   = 20.8 / 250 / 8.0 # M parcels / days / M HHs 
        varDict['PARCELS_PER_HH_B2C']   = 0.195
        varDict['PARCELS_PER_HH']       = varDict['PARCELS_PER_HH_C2C'] + varDict['PARCELS_PER_HH_B2C']
        varDict['PARCELS_PER_EMPL']     = 0
        varDict['Local2Local']          = 0.04
        varDict['CS_cust_willingness']  = 0.05 # Willingess to SEND a parcel by CS
        varDict['PARCELS_MAXLOAD']	    = 180												
        varDict['PARCELS_DROPTIME' ]    = 120												
        varDict['PARCELS_SUCCESS_B2C']   = 0.75											
        varDict['PARCELS_SUCCESS_B2B' ]  = 0.95											
        varDict['PARCELS_GROWTHFREIGHT'] = 1.0										

    
    args = ['', varDict]
    return args, varDict


method = 'from_file' #either from_file or from_code

args, varDict = generate_args(method)


actually_run_module(args)

print("Connection Market 2 Scheduling done")
