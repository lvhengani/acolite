## def metadata_parse
## parses landsat metadata to get parameters for processing
## written by Quinten Vanhellemont, RBINS
## 2017-04-13
## modifications: (QV) 2017-06-15 changed band removal
##                2018-07-18 (QV) changed acolite import name

def metadata_parse(bundle):
    import dateutil.parser
    from acolite.shared import distance_se
    from acolite.landsat import metadata_read
    from acolite.landsat import bundle_test
    from acolite.ac import f0_sensor

    bundle_files = bundle_test(bundle)
    metafile = bundle_files['MTL']['path']
    mdata = metadata_read(metafile)

    metadata = {}

    metadata["SATELLITE"] = mdata['PRODUCT_METADATA']['SPACECRAFT_ID'].strip('"')
    metadata["SENSOR"] = mdata['PRODUCT_METADATA']['SENSOR_ID'].strip('"')

    if 'IMAGE_ATTRIBUTES' in mdata.keys():
        metadata['NEW_STYLE']=True
        metadata['AZI'] = float(mdata['IMAGE_ATTRIBUTES']['SUN_AZIMUTH'])
        metadata['THS'] = 90. - float(mdata['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])
        metadata['THV'] = 0.
        #metadata['THV'] = 3.5
        metadata['SCENE'] = mdata['METADATA_FILE_INFO']['LANDSAT_SCENE_ID']
        if 'LANDSAT_PRODUCT_ID' in mdata['METADATA_FILE_INFO'].keys(): metadata['PRODUCT'] = mdata['METADATA_FILE_INFO']['LANDSAT_PRODUCT_ID']

        metadata['PROCESSING_DATE'] = mdata['METADATA_FILE_INFO']['FILE_DATE']
        metadata['ISODATE'] = '{}T{}Z'.format(mdata['PRODUCT_METADATA']['DATE_ACQUIRED'].strip('"'),mdata['PRODUCT_METADATA']['SCENE_CENTER_TIME'].strip('"'))

        ### get projection info
        metadata["PATH"] = mdata['PRODUCT_METADATA']['WRS_PATH'].strip('"')
        metadata["ROW"] = mdata['PRODUCT_METADATA']['WRS_ROW'].strip('"')
        metadata["DIMS"] = [int(mdata['PRODUCT_METADATA']['REFLECTIVE_SAMPLES'].strip('"')),
                        int(mdata['PRODUCT_METADATA']['REFLECTIVE_LINES'].strip('"'))]

        tags = ['CORNER_LL_PROJECTION_X_PRODUCT', 'CORNER_LL_PROJECTION_Y_PRODUCT',
                'CORNER_LR_PROJECTION_X_PRODUCT', 'CORNER_LR_PROJECTION_Y_PRODUCT',
                'CORNER_UL_PROJECTION_X_PRODUCT', 'CORNER_UL_PROJECTION_Y_PRODUCT',
                'CORNER_UR_PROJECTION_X_PRODUCT', 'CORNER_UR_PROJECTION_Y_PRODUCT']
        for tag in tags: metadata[tag] = float(mdata['PRODUCT_METADATA'][tag])

        tags = ['CORNER_LL_LAT_PRODUCT', 'CORNER_LL_LON_PRODUCT',
                'CORNER_LR_LAT_PRODUCT', 'CORNER_LR_LON_PRODUCT',
                'CORNER_UL_LAT_PRODUCT', 'CORNER_UL_LON_PRODUCT',
                'CORNER_UR_LAT_PRODUCT', 'CORNER_UR_LON_PRODUCT']
        for tag in tags: metadata[tag] = float(mdata['PRODUCT_METADATA'][tag])

        ## get rescaling
        bands = set()
        for key in mdata['RADIOMETRIC_RESCALING'].keys():
            metadata[key] = float(mdata['RADIOMETRIC_RESCALING'][key])
            if 'REFLECTANCE' in key: bands.add(key.split('_')[3]) ## add optical bands to list
            if 'RADIANCE' in key: bands.add(key.split('_')[3]) ## add optical bands to list
    else:
        metadata['NEW_STYLE']=False
        metadata['SENSOR'] = mdata['PRODUCT_METADATA']['SENSOR_ID']
        spacecraft = mdata['PRODUCT_METADATA']['SPACECRAFT_ID']
        if spacecraft == 'Landsat5': metadata["SATELLITE"]='LANDSAT_5'
        if spacecraft == 'Landsat7': metadata["SATELLITE"]='LANDSAT_7'
        metadata['AZI'] = float(mdata['PRODUCT_PARAMETERS']['SUN_AZIMUTH'])
        metadata['THS'] = 90. - float(mdata['PRODUCT_PARAMETERS']['SUN_ELEVATION'])
        metadata['THV'] = 0.
        metadata['SCENE'] = mdata['PRODUCT_METADATA']['METADATA_L1_FILE_NAME']

        metadata['PROCESSING_DATE'] = mdata['METADATA_FILE_INFO']['PRODUCT_CREATION_TIME']
        metadata['ISODATE'] = '{}T{}Z'.format(mdata['PRODUCT_METADATA']['ACQUISITION_DATE'].strip('"'),mdata['PRODUCT_METADATA']['SCENE_CENTER_SCAN_TIME'].strip('"'))

        ### get projection info
        metadata["PATH"] = mdata['PRODUCT_METADATA']['WRS_PATH'].strip('"')
        metadata["ROW"] = mdata['PRODUCT_METADATA']['STARTING_ROW'].strip('"')
        metadata["DIMS"] = [int(mdata['PRODUCT_METADATA']['PRODUCT_SAMPLES_REF'].strip('"')),
                        int(mdata['PRODUCT_METADATA']['PRODUCT_LINES_REF'].strip('"'))]
        tags = ["PRODUCT_UL_CORNER_LAT","PRODUCT_UL_CORNER_LON",
                "PRODUCT_UR_CORNER_LAT","PRODUCT_UR_CORNER_LON",
                "PRODUCT_LL_CORNER_LAT","PRODUCT_LL_CORNER_LON",
                "PRODUCT_LR_CORNER_LAT","PRODUCT_LR_CORNER_LON",
                "PRODUCT_UL_CORNER_MAPX","PRODUCT_UL_CORNER_MAPY",
                "PRODUCT_UR_CORNER_MAPX","PRODUCT_UR_CORNER_MAPY",
                "PRODUCT_LL_CORNER_MAPX","PRODUCT_LL_CORNER_MAPY",
                "PRODUCT_LR_CORNER_MAPX","PRODUCT_LR_CORNER_MAPY"]
        for tag in tags: metadata[tag] = float(mdata['PRODUCT_METADATA'][tag])

        ## get rescaling
        bands = set()
        for key in mdata['MIN_MAX_RADIANCE'].keys():
            metadata[key] = float(mdata['MIN_MAX_RADIANCE'][key])
            bands.add(key[-1]) ## add optical bands to list
        for key in mdata['MIN_MAX_PIXEL_VALUE'].keys():
            metadata[key] = float(mdata['MIN_MAX_PIXEL_VALUE'][key])
        print(bands)

    ### common things
    metadata["TIME"] = dateutil.parser.parse(''.join([metadata["ISODATE"]]))
    metadata["DOY"] = metadata["TIME"].strftime('%j')
    metadata["SE_DISTANCE"] = distance_se(metadata['DOY'])
    for key in mdata['PROJECTION_PARAMETERS'].keys():
        metadata[key] = mdata['PROJECTION_PARAMETERS'][key]

    ## set up bands
    metadata['BANDS']=list(bands)
    metadata['BANDS'].sort()

    metadata['BAND_NAMES'] = metadata['BANDS']

    ## some sensor specific config
    if metadata["SATELLITE"] == 'LANDSAT_8':
        ## get TIRS for L8
        for key in mdata['TIRS_THERMAL_CONSTANTS'].keys():
            metadata[key] = float(mdata['TIRS_THERMAL_CONSTANTS'][key])
        ## bands to remove
        remove_bands = ['8','9','10','11'] ## pan cirrus thermal x2
        for rb in remove_bands:
            if rb in metadata['BANDS']: metadata['BANDS'].remove(rb)

        #metadata['BANDS'].remove('8') ## remove Pan band
        #metadata['BANDS'].remove('9') ## remove Cirrus band
        #metadata['BANDS'].remove('10') ## remove Thermal band
        #metadata['BANDS'].remove('11') ## remove Thermal band
        metadata['SATELLITE_SENSOR'] = 'L8_OLI'
        #metadata['RGB_BANDS']= {'rhot':{'blue':'rhot_483','green':'rhot_561','red':'rhot_655'},
        #                        'rhos':{'blue':'rhos_483','green':'rhos_561','red':'rhos_655'}}
        metadata['RGB_BANDS']= [483,561,655]
        metadata['WAVES']= [443,483,561,655,865,1609,2201]
    
        ## some defaults here - probably not used any more
        metadata['BANDS_REDNIR'] = ['4','5']
        metadata['BANDS_VIS'] = ['1','2','3','4']
        metadata['BANDS_NIR'] = ['5','6','7']
        metadata['BANDS_BESTFIT'] = ['6','7']
        #metadata['BANDS_ALL'] = ['1','2','3','4','5','6','7','9','10','11']
        metadata['BANDS_ALL'] = ['1','2','3','4','5','6','7','9','10','11']
        metadata['BANDS_PAN'] = ['8']
        metadata['BANDS_CIRRUS'] = ['9']
        metadata['BANDS_THERMAL'] = ['10','11']
        metadata['BAND_NAMES_ALL'] = ['1','2','3','4','5','6','7','9','10','11']
        metadata['WAVES_ALL']= [443,483,561,655,865,1609,2201,1375,10900,11500]

    if metadata["SATELLITE"] == 'LANDSAT_5':
        #metadata['BANDS'].remove('6') ## remove Thermal band
        remove_bands = ['6'] ## thermal
        for rb in remove_bands:
            if rb in metadata['BANDS']: metadata['BANDS'].remove(rb)
        metadata['SATELLITE_SENSOR'] = 'L5_TM' if metadata['SENSOR'] == 'TM' else 'L5_MSS'
        #metadata['RGB_BANDS']= {'rhot':{'blue':'rhot_486','green':'rhot_571','red':'rhot_660'},
        #                        'rhos':{'blue':'rhos_486','green':'rhos_571','red':'rhos_660'}}
        metadata['RGB_BANDS']= [486,571,660]
        metadata['WAVES']= [486, 571, 660, 839, 1678, 2217]

        ## some defaults here - probably not used any more
        metadata['BANDS_REDNIR'] = ['3','4']
        metadata['BANDS_VIS'] = ['1','2','3']
        metadata['BANDS_NIR'] = ['4','5','7']
        metadata['BANDS_BESTFIT'] = ['5','7']
        metadata['BANDS_ALL'] = ['1','2','3','4','5','6','7']
        metadata['BANDS_PAN'] = []
        metadata['BANDS_CIRRUS'] = []
        metadata['BANDS_THERMAL'] = ['6']
        metadata['BAND_NAMES_ALL'] = ['1','2','3','4','5','6','7']
        metadata['WAVES_ALL']= [486, 571, 660, 839, 1678, 10000, 2217]

    if metadata["SATELLITE"] == 'LANDSAT_7':
        #metadata['BANDS'].remove('6') ## remove Thermal band
        #metadata['BANDS'].remove('8') ## remove Pan band
        remove_bands = ['6','8'] ## thermal pan
        for rb in remove_bands:
            if rb in metadata['BANDS']: metadata['BANDS'].remove(rb)
        metadata['SATELLITE_SENSOR'] = 'L7_ETM'
        #metadata['RGB_BANDS']= {'rhot':{'blue':'rhot_479','green':'rhot_561','red':'rhot_661'},
        #                        'rhos':{'blue':'rhos_479','green':'rhos_561','red':'rhos_661'}}
        metadata['RGB_BANDS']= [479,561,661]
        metadata['WAVES']= [479, 561, 661, 835, 1650, 2208]

        ## some defaults here - probably not used any more
        metadata['BANDS_REDNIR'] = ['3','4']
        metadata['BANDS_VIS'] = ['1','2','3']
        metadata['BANDS_NIR'] = ['4','5','7']
        metadata['BANDS_BESTFIT'] = ['5','7']
        metadata['BANDS_ALL'] = ['1','2','3','4','5','6','7']
        metadata['BANDS_PAN'] = ['8']
        metadata['BANDS_CIRRUS'] = []
        metadata['BANDS_THERMAL'] = ['6']
        metadata['BAND_NAMES_ALL'] = ['1','2','3','4','5','6','7']
        metadata['WAVES_ALL']= [479, 561, 661, 835, 1650, 10000, 2208]

    ## make F0 for bands
    f0 = f0_sensor(metadata['SATELLITE_SENSOR'])
    for band in f0.keys():
        metadata['B{}_F0'.format(band)] = f0[band]

    ## get FILE names for bands and test if they exist in the bundle    
    for par in mdata['PRODUCT_METADATA']:
        if 'FILE_NAME' in par:
                fname = mdata['PRODUCT_METADATA'][par]
#                print(fname)
                exists = False
                for file in bundle_files:
#                    print(bundle_files[file]['fname'])
                    if bundle_files[file]['fname'] == fname:
                        exists = True
                        metadata[file] = bundle_files[file]['path']

    return(metadata)
