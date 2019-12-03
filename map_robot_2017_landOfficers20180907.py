# ArcPy.Mapping Module
# Map_Robot_v2017_inset
#
# land officer mapping tool
# zooms into file number of interest
# populates some info in text fields on map template
# new version has an inset map to show details of a selected parcel
# the main map ("Layers") will show the entire tenure to better show where
# it is on the land base
#
# October 2013
#
# Changes in layout for PMV
# layout also means text updater needed updating because they removed some fields
# and added others
#
#
# ------------------------------------------------------------------------
''' --------------------------------------------------------------
    Date Started:    October 25, 2012
    Author:          Denis Potvin

    lost track of modifications.
    this latest version:
    - cleaned up some code
    - mxd should have only Direct connect to BCGW
    - fixed where clause1  for the client name

    --------------------------------------------------------------'''


import arcpy, math, getpass, sys, re, os, textwrap
'''
# for accessing XTools toolbox
if arcpy.GetInstallInfo("desktop")["Version"] == '10.1':
    toolboxPath = r'E:\sw_nt\DataEast\XToolsPro 10.1\Toolbox\XTOOLS PRO.tbx'   # new ver of Xtools for 10.1
else:
    toolboxPath = r'E:\sw_nt\DataEast\XToolsPro 10.2\Toolbox\XTOOLS PRO.tbx'   # old ver of Xtools for 10.0
arcpy.AddToolbox(toolboxPath)
arcpy.gp.toolbox = toolboxPath
'''
#print "arg0 = " + sys.argv[0]



class myMXD(object):
    ''' creates a class to take in tenure stage, file number, parcel numbers, dimensions
        inset map will zoom into the parcel, main map will zoom to entire extent
        scale will be rounded off, a bunch of text fields will auto populate
        and the world will be a better place
        '''

    mapDoc = "CURRENT"     # Map Document Object
    #mapDoc = r'W:\srm\sry\Local\projlib\2014-15\Auth_Lands_PMV\mxds\MapRobot2014.mxd'   # !!! for PMV batch maps
    mainDF = None          # main data frame object
    detailDF = None        # detail inset map data frame object
    mainDefQry = None      # definition query for main map
    detailDefQry = None    # definition query for detail inset map
    fileStage = None       # tenure stage (Application, Tenure, Inventory,
    fileNum = None
    intridSID = None
    dims = None
    bcgw    = r'Database Connections\BCGW.sde'



    mxd = None
    insetLocation = None



    def __init__(self, fileStage, fileNum, intridSID, dims, insetLoc):
        self.mxd = arcpy.mapping.MapDocument(self.mapDoc)



        self.mainDF = arcpy.mapping.ListDataFrames(self.mxd, "Layers")[0]
        self.detailDF = arcpy.mapping.ListDataFrames(self.mxd,"InsetDetail")[0]

        print (self.mainDF.name)
        print (self.detailDF.name)
        self.insetLocation = insetLoc

        # Defn query to filter out the other tenures/parcels.
        # replace is to change ; to , for the SQL "IN" statement to work properly
        # !!! CHANGE THIS PART FOR PMV MASS PRODUCTION MAPPING !!!
        self.detailDefQry = "CROWN_LANDS_FILE = '" + fileNum + "' and TENURE_STAGE = '" + fileStage + "' AND INTRID_SID in (" + intridSID.replace(";",",") + ")"
        #self.detailDefQry = "\"CROWN_LANDS_FILE\" = '" + fileNum + "'"
        #self.detailDefQry = "CROWN_LANDS_FILE = '" + str(fileNum) + "'"   # mass production mapping - only wanted the file num and nothing else

        if insetLoc == "None":
            self.mainDefQry = self.detailDefQry   # no inset, both queries same
        else:
            self.mainDefQry = "CROWN_LANDS_FILE = '" + fileNum + "' and TENURE_STAGE = '"+ fileStage + "'"
            #self.mainDefQry = "CROWN_LANDS_FILE = '" + str(fileNum) + "'"   # for mass production mapping for PMV


        self.fileNum = fileNum   # file number of interest

        # moving the inset Data frame to the desired location
        posX, posY = self.insetPlace(insetLoc)  # calling module to get X,Y
        self.detailDF.elementPositionX = posX
        self.detailDF.elementPositionY = posY

        arcpy.RefreshActiveView()


    # ----------------------------------------------------------------------
    # insetPlace returns the X,Y location of the anchor point for the
    # data frame depending on where the user wants to see the inset map

    def insetPlace(self, insetLoc):
        # potential anchor points for bottom Left of your inset map
        minX = 0.725
        minY = 2.95
        maxX = 4.775
        maxY = 6.75
        noX = 9   # no inset map - move off the layout
        noY = 8   # no inset map - move off the layout

        # creating a dictionary to hold the possible locations of
        # where the inset map would be
        # inset map location is anchored to bottom left of the data frame
        myDict = {"None": [noX,noY],
                  "Bottom Left": [minX, minY],
                  "Bottom Right": [maxX, minY],
                  "Top Left": [minX, maxY],
                  "Top Right": [maxX, maxY]  }

        codeList = myDict.keys()   # get the keys
        for itm in codeList:
            #arcpy.AddMessage("checking out inset map placement: " + str(itm))
            myLine = myDict[itm]   # storing the selected list from the dictionary
            if insetLoc == itm:
                locX = myLine[0]   # 1st item in the list
                locY = myLine[1]   # 2nd item in the list
                break

        return locX, locY   # for location of inset map

    # ----------------------------------------------------------------------
    # insetPlace returns the X,Y location of the anchor point for the
    # data frame depending on where the user wants to see the inset map

    def dataFrameFilter(self, df, defQry, insetmap):
        # get layer object
        arcpy.AddMessage("beginning layer filter of data frame" + df.name)
        arcpy.AddMessage(defQry)
        lyr = arcpy.mapping.ListLayers(self.mxd, "Tantalis Files", df)[0]
        arcpy.AddMessage(lyr.name)
        arcpy.AddMessage("defined the lyr for Tantalis Files?")

        # ARGH! REMEMBER TO CLEAR DEFINITION QUERY FIRST
        # otherwise there'll be nothing to query if it's the 2nd time !
        lyr.definitionQuery = ""

        # Do selection and zoom in
        print ('defQry:', defQry)
        defQry = defQry.strip()
        defQry = str(defQry)
        #print '1 selected count', arcpy.GetCount_management(lyr)
        arcpy.SelectLayerByAttribute_management(lyr,"CLEAR_SELECTION")
        #print '2 selected count', arcpy.GetCount_management(lyr)

        #arcpy.RefreshActiveView()
        #print '3 selected count', arcpy.GetCount_management(lyr)

        arcpy.SelectLayerByAttribute_management(lyr,"NEW_SELECTION", defQry)
        self.SelectedSetChecker(lyr)   # check for no polys or zero area

        df.zoomToSelectedFeatures()
        arcpy.AddMessage("zoomed to my selected feature! ")
        arcpy.SelectLayerByAttribute_management(lyr,"CLEAR_SELECTION")

        lyr.definitionQuery = defQry   # filter the layer to just the ones you want

        # main map, tiny polygon, and no inset, then zoom out
        if df.name == "Layers" and df.scale < 10000 and insetmap <> "None":
            df.scale = 10000
        else:  # otherwise do the scale rounding as per routine
            df.scale = self.scalefixer(df.scale)


    # ----------------------------------------------------------------------
    # scaleFixer will round up the scale
    # to the nearest 1000 or 10000
    def scalefixer(self, currScale):
        if currScale > 10000:
            fixit = 4
        else:
            fixit = 3
        fixneg = fixit * -1
        newScale = math.ceil(currScale*10**fixneg)*10**fixit
        return newScale

    # ----------------------------------------------------------------------
    def doDimensions(self, dFrame, lyr):
        # Set Up Stuff
        tmpDrive = "T:"
        tmpFGDBname = "\\tmpfgdb_" + getpass.getuser() + ".gdb"
        tmpFGDB = tmpDrive + tmpFGDBname
        dimFC = tmpFGDB + "\\DimensionsFC"
        tmpFC1 = tmpDrive + "\\tmpFC1.shp"
        #tmpFC2 = tmpFGDB + "\\tmpFC2"

        # Create a new temp FGDB if it doesn't already exist
        if not arcpy.Exists(tmpFGDB):
            arcpy.AddMessage("creating new " + tmpFGDB)
            arcpy.CreateFileGDB_management(tmpDrive, tmpFGDBname)
        else:
            # if FGDB exists, then remove all the old layers
            arcpy.AddMessage("Deleting old dimensions feature class if exists")
            delList = [dimFC, tmpFC1]
            for feat in delList:
                self.delLayer(feat)
            arcpy.AddMessage("finished deleting old temp feature classes")

        arcpy.AddMessage("converting polygon to polyline")

        arcpy.PolygonToLine_management(lyr, tmpFC1,"IGNORE_NEIGHBORS")
        #dimLayer = arcpy.mapping.Layer(dimFC) # create layer object from dimFC feat class
        arcpy.SplitLine_management(tmpFC1, dimFC)

        arcpy.AddMessage("Splitting up the lines of polyline layer")

        mainLyr = arcpy.mapping.ListLayers(self.mxd, "Dimensions", self.mainDF)[0]
        detailLyr = arcpy.mapping.ListLayers(self.mxd, "iDimensions", self.detailDF)[0]

        arcpy.AddMessage("updating the dimensions layer")

        # changing the dimensions layer source to the new one
        mainLyr.replaceDataSource(tmpFGDB, "FILEGDB_WORKSPACE", "DimensionsFC")
        detailLyr.replaceDataSource(tmpFGDB, "FILEGDB_WORKSPACE", "DimensionsFC")

        arcpy.AddMessage(tmpFGDB + " is my temp fgdb name")
        arcpy.AddMessage("Dimensions data source changed: ")
        #arcpy.AddMessage(upLyr.dataSource)

        # !!! turning off the dimensions lyr on the main data frame if dimensions was already used on the inset map
        # !!! otherwise dimensions is turned on for both... not ideal.
        if dFrame == self.detailDF:
            arcpy.AddMessage("inset measurements only")
            mainLyr.visible = False
            detailLyr.visible = True
            arcpy.AddMessage("main: " + str(mainLyr.visible))
        else:
            arcpy.AddMessage("main map measurements only")
            mainLyr.visible = True
            detailLyr.visible = False
            arcpy.AddMessage("main: " + str(mainLyr.visible))


        arcpy.RefreshActiveView()


        return lyr

    # ----------------------------------------------------------------------
    def delLayer(self,fc):
        if arcpy.Exists(fc):
            arcpy.AddMessage("Deleting old feature : " + fc)
            arcpy.Delete_management(fc)
        return # go back go waaaay bck

    # ------------------------------------------------------------------------
    # ---- SELECTED SET CHECKER ----
    #     check to see if selected set has > 0 features
    #     if yes then check to ensure the area of the polygons is <> 0

    def SelectedSetChecker(self, lyr):
        # counting rows in my selected set
        rowcount = int(arcpy.GetCount_management(lyr).getOutput(0))
        arcpy.AddMessage(str(rowcount) + " rows in selected lyr")
        if rowcount == 0:
            arcpy.AddError("The file you chose: " + str(self.fileNum) + "(" + str(self.fileStage) + ") - has zero polygons")
            raise ValueError, "Sorry, does not exist in the BCGW"
        else:
            # check for zero area
            rows = arcpy.SearchCursor(lyr)  # going thru the precinct lyr
            row = rows.next()
            sumarea = 0

            while row:
                #Bruce Rea commented out the following line and replaced with Hectares area field
                #tmp = row.getValue("SHAPE.AREA")
                #tmp = row.getValue("TENURE_AREA_IN_HECTARES")
                tmp = row.getValue("FEATURE_AREA_SQM")
                if tmp == None:
                    tmp = 0
                sumarea = sumarea + tmp
                row = rows.next()
            if sumarea == 0:
                arcpy.AddError("The file you chose: " + str(self.fileNum) + " (" + str(self.fileStage) + ") - has zero area")
                raise ValueError, "Check Tantalis to see if a shape has been entered"

            del row, rows, rowcount
        return
        # ---- END OF MODULE: SELECTED SET CHECKER ----

    def splitLineOnSpaces2(self,inString,maxLineBreak):
        # https://docs.python.org/2/library/textwrap.html
        arcpy.AddMessage("Splitting up the line string")
        lineList = textwrap.wrap(inString, width=maxLineBreak)
        return lineList

    # ----------------------------------------------------------------------
    # updates the text fields on the map

    def txtUpdater(self, lyr):
        arcpy.AddMessage("resetting variable values")
        tantarea = 0
        rows = arcpy.SearchCursor(lyr)
        row = rows.next()
        arcpy.AddMessage("starting get value statements")
        purpose = row.getValue("TENURE_PURPOSE")
        subpurpose = row.getValue("TENURE_SUBPURPOSE")
        tentype = row.getValue("TENURE_TYPE")
        subtype = row.getValue("TENURE_SUBTYPE")
        tantarea = row.getValue("TENURE_AREA_IN_HECTARES")
        dispID = row.getValue("DISPOSITION_TRANSACTION_SID")
        legdesc = row.getValue("TENURE_LEGAL_DESCRIPTION")
        arcpy.AddMessage(legdesc)


        # calling Netherton's script to add carriage returns to the mega long legal description
        # first arg is the legal descr, second is the max line length
        #
        lineList = []
        maxlen = 88    # max line length on the map for legal descr
        if legdesc is not None:
            if len(legdesc) > maxlen:
                # split the legal description into lines no longer than max len
                #lineList = self.splitLineOnSpaces(legdesc, maxlen)
                lineList = self.splitLineOnSpaces2(legdesc, maxlen)
            else:
                # legal description fits on one line
                lineList.append(legdesc)

            #arcpy.AddMessage(lineList)
            arcpy.AddMessage("subliminal messaging here")
            # join the split line using a carrage return
            if len(lineList) > 11:
                arcpy.AddMessage("creating a text file for the long legal desc")
                #folder = r"\\spatialfiles.bcgov\work\srm\sry\Workarea\land_officers\PMV\legalDescr"
                folder = r"W:\srm\sry\Workarea\land_officers\map_robot_2017\LongLegalDescr"
                legfile = folder + r"\legal_descr_" + self.fileNum + ".txt"
                filehand = open(legfile, "w")
                filehand.write(legdesc)
                filehand.close()
                arcpy.AddMessage("completed text file writing")
                lineList[11] = '(Truncated due to length. See next page for full legal description.)'
                lineList = lineList[:12]
                arcpy.AddMessage("truncated the extra long for the map")
        var = '\n'.join(lineList)
            #arcpy.AddMessage(var)


        arcpy.AddMessage("finished a whole bunch of getValue statements")
        if tantarea == None:
            tantarea = 0
            arcpy.AddMessage("...!!! WARNING - one of  your shapes has zero area according to Tantalis")
        dispID = row.getValue("DISPOSITION_TRANSACTION_SID")

        # Adding up tenure area in hectares if there's more than one polygon
        row = rows.next()
        while row:
            tmp = row.getValue("TENURE_AREA_IN_HECTARES")
            if tmp == None:
                tmp = 0
                arcpy.AddMessage("...WARNING - one of  your shapes has zero area according to Tantalis")
            tantarea = tantarea + tmp
            row = rows.next()

        arcpy.AddMessage('updating text fields')
        for elm in arcpy.mapping.ListLayoutElements(self.mxd, "TEXT_ELEMENT"):
            if elm.name == "txtFileNo":
                arcpy.AddMessage('getting file num')
                elm.text = "File No: " + str(self.fileNum)
            elif elm.name == 'txtClient':
                elm.text = self.ClientName(dispID)  # >>> Calling Module to get Client name
                #arcpy.AddMessage("skipping client name?")
            elif elm.name == 'txtPurpose':
                elm.text = str(purpose)
            elif elm.name == 'txtSubPurpose':
                elm.text = str(subpurpose)
            elif elm.name == 'txtType':
                elm.text = str(tentype)
            elif elm.name == 'txtSubType':
                elm.text = str(subtype)
            elif elm.name == 'txtMapsheets':
                elm.text = self.mapsheetoverlay(lyr) # >>> Calling Module Mapsheet overlay
            elif elm.name == 'txtTantalisArea':
                if tentype == 'LICENCE':
                    elm.text = 'Area: ' + str(round(tantarea, 2)) + ' ha +/-'
                else:
                    elm.text = 'Area: ' + str(round(tantarea, 2)) + ' ha'  # removed "Tantalis" prefix to "Area"
            elif elm.name == 'txtDispNo':
                elm.text = 'Disposition No: ' + str(dispID)
            elif elm.name == 'txtLegalDescr1':
                if legdesc is None:
                    elm.text = "No legal description"
                else:
                    elm.text = var

        del row, rows
        return

    # ------------------------------------------------------------------------
    # ---- MODULE: Mapsheet overlay procedure ----
    def mapsheetoverlay(self, lyr):

        mapsheets = ''     # resetting the variable for mapsheets

        map20k = self.bcgw + '\\WHSE_BASEMAPPING.BCGS_20K_GRID'  # mapsheet layer from BCGW

        self.delLayer("map20klyr")

        arcpy.MakeFeatureLayer_management (map20k, "map20klyr")
        # doing the overlay
        arcpy.AddMessage('checking for 20k mapsheet overlaps')
        arcpy.SelectLayerByLocation_management ("map20klyr", "INTERSECT", lyr)
        # going thru the selected map20k lyr features
        rows = arcpy.SearchCursor("map20klyr")
        row = rows.next()
        mapsheets = row.getValue("MAP_TILE_DISPLAY_NAME")
        arcpy.AddMessage(mapsheets)
        row = rows.next()
        while row:
            mapsheets = mapsheets + ", " + row.getValue("MAP_TILE_DISPLAY_NAME")
            arcpy.AddMessage(mapsheets)
            row = rows.next()

        self.delLayer("map20klyr")

        del rows, row

        return mapsheets
        # ------------------------------------------------------------------------
        # --- MODULE: Getting Client Name from BCGW tables ---

    def ClientName(self, dispID):
        # the query table exists in memory
        # do the query and spit out the client name
        # the two tables we need to join
        arcpy.AddMessage("Obtaining Client Information")
        arcpy.AddMessage("Please Stand by...")

        tmpDrive = "T:"
        tmpFGDBname = "\\tmpfgdb_" + getpass.getuser() + ".gdb"
        tmpFGDB = tmpDrive + tmpFGDBname
        dimFC = tmpFGDB + "\\DimensionsFC"
        if not arcpy.Exists(tmpFGDB):
            arcpy.AddMessage("creating new " + tmpFGDB)
            arcpy.CreateFileGDB_management(tmpDrive, tmpFGDBname)

        tmplist = ["t1View", "t2View"]
        for tmpX in tmplist:
            self.delLayer(tmpX)
            arcpy.AddMessage("Please Stand by...part 2")

        t1  = self.bcgw + '\\WHSE_TANTALIS.TA_TENANTS'   # gobetween table
        t2  = self.bcgw + '\\WHSE_TANTALIS.TA_INTERESTED_PARTIES'

        tmpT1 = tmpFGDB + "\\tmpT1"
        tmpT2 = tmpFGDB + "\\tmpT2"

        # fields for joining the tables
        t1Field     = 'DISPOSITION_TRANSACTION_SID'
        joinField   = 'INTERESTED_PARTY_SID'
        contField   = 'PRIMARY_CONTACT_YRN'

        # only pulling out client identified as "Primary Contact"
        # editing out and trying AddFieldDelimiters
        # http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-functions/addfielddelimiters.htm
        # whereClause = t1Field + " = " + str(dispID) + " AND \"PRIMARY_CONTACT_YRN\" = \'Y\'"
        wcList = [t1Field, contField]
        wc1 = arcpy.AddFieldDelimiters(self.bcgw, t1Field)
        wc2 = arcpy.AddFieldDelimiters(self.bcgw, contField)
        whereClause =  "({0} = {1}) AND ({2} = '{3}')".format(wc1, str(dispID), wc2, 'Y')

        arcpy.AddMessage(whereClause)
        legal =  'LEGAL_NAME'   # field names in the TA_INTERESTED_PARTIES table
        first =  'FIRST_NAME'
        last  =  'LAST_NAME'
        txtClientName = 'Interest Holder: '  # resetting txtClientName

        # doing a selected set to just show me the Disposition)
        #arcpy.CopyRows_management(t1, tmpT1)  !!! removed Sep 1
        #arcpy.MakeTableView_management (tmpT1, "t1View", wc1)
        where1 = "({0} = {1})".format(wc1, str(dispID))
        arcpy.AddMessage('using where1 clause')
        arcpy.AddMessage(where1)
        # arcpy.MakeTableView_management (tmpT1, "t1View", where1) !!! changed Sep 1
        arcpy.MakeTableView_management (t1, "t1View", where1)

        arcpy.AddMessage("created t1View")
        #arcpy.AddMessage("using " + whereClause)
        #tmp2 = fieldLister("t1View")
        result = int(arcpy.GetCount_management("t1View").getOutput(0))
        arcpy.AddMessage("rows: " + str(result))

        rows = arcpy.SearchCursor("t1View")
        row = rows.next()
        t1IPSID = str(row.getValue(joinField))
        #arcpy.AddMessage(t1IPSID + ' is the INTERESTED_PARTY_SID')
        whereClause2 = joinField + ' = ' + t1IPSID
        #arcpy.CopyRows_management(t2, tmpT2)   #!!!  removed Sep 1
        # arcpy.MakeTableView_management(tmpT2, "t2View", whereClause2) # !!! changed Sep 1
        arcpy.MakeTableView_management(t2, "t2View", whereClause2)
        arcpy.AddMessage("created t2View")
        #arcpy.AddMessage("using " + whereClause2)
        #tmp2 = fieldLister("t2View")
        result = int(arcpy.GetCount_management("t2View").getOutput(0))
        arcpy.AddMessage("rows: " + str(result))

        rows = arcpy.SearchCursor("t2View")
        row = rows.next()

        lgl = str(row.getValue(legal))
        fst = str(row.getValue(first))
        lst = str(row.getValue(last))
        arcpy.AddMessage("first try: " + lgl)

        # if legal name is null, make txtClientName = first + last names
        if lgl == "None":
            arcpy.AddMessage('no LEGAL_NAME value')
            txtClientName = txtClientName +  fst + " " + lst
            arcpy.AddMessage('using individual first, last name: ' + txtClientName)
        else:
            txtClientName = txtClientName + lgl

        # cleaning up variables from memory
        del row, rows, t1, t2, tmpX, lgl, fst, lst, whereClause2, whereClause
        print ('cleaning up temp client tables')
        self.delLayer(tmpT2)
        self.delLayer(tmpT1)

        return txtClientName

    def MakeTheDamnPDF(self, outfile):

        arcpy.RefreshActiveView()

        # make PDF file here

        #pdffolder = r"\\spatialfiles.bcgov\work\srm\sry\Workarea\land_officers\PMV\maps"
        #pdfpath = pdffolder + "\\" + str(obj.fileNum) + ".pdf"

        if os.path.exists(outfile):
            os.remove(outfile)
            arcpy.AddMessage("Killed old PDF file")

        #Create the file

        arcpy.mapping.ExportToPDF(self.mxd, outfile )
        arcpy.AddMessage("created new PDF file for " + self.fileNum)

# -------------------------------------------



print ('__name__ is', __name__)

if __name__ == '__main__':

    ten_stage = sys.argv[1]
    file_num  = sys.argv[2]
    intrid_sid = sys.argv[3]
    dimensions = sys.argv[4]
    inset_map = sys.argv[5]



    try:

        # making my MXD object here, should start the __init__ sequence
        obj = myMXD(ten_stage, file_num, intrid_sid, dimensions, inset_map)

        if inset_map == "None":
            arcpy.AddMessage("no inset map")
            # just draw the main data frame
            obj.dataFrameFilter(obj.mainDF, obj.mainDefQry, inset_map)
            tantlyr = arcpy.mapping.ListLayers(obj.mxd, "Tantalis Files", obj.mainDF)[0]
            obj.txtUpdater(tantlyr)
            if dimensions == 'YES':
                obj.doDimensions(obj.mainDF, tantlyr)
            else:
                # turn off the dimensions lyr
                arcpy.AddMessage("turning off the dim lyr ")
        else:
            arcpy.AddMessage("inset map set to " + str(inset_map))
            # do both main and inset data frames
            obj.dataFrameFilter(obj.mainDF, obj.mainDefQry, inset_map)
            obj.dataFrameFilter(obj.detailDF, obj.detailDefQry, inset_map)
            tantlyr = arcpy.mapping.ListLayers(obj.mxd, "Tantalis Files", obj.detailDF)[0]
            obj.txtUpdater(tantlyr)
            if dimensions == 'YES':
                obj.doDimensions(obj.detailDF, tantlyr)

        # make PDF file here

        #pdffolder = r"\\spatialfiles.bcgov\work\srm\sry\Workarea\land_officers\PMV\maps"
        '''
        pdffolder = r"W:\srm\sry\Workarea\land_officers\PMV\maps"
        pdfpath = pdffolder + "\\" + str(obj.fileNum) + ".pdf"
        arcpy.AddMessage("pdfpath is " + pdfpath)
        obj.MakeTheDamnPDF(pdfpath)
        '''

    except Exception, e:
        arcpy.AddMessage(str(e))

    arcpy.RefreshActiveView()
    arcpy.AddMessage("!!! this is the end !!!")