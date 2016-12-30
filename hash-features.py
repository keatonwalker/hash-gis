"""Hash it up."""
import arcpy
import hashlib
import numpy
import os
from time import time
from operator import itemgetter
import cProfile
import sys
import csv
from time import strftime


uniqueRunNum = strftime("%Y%m%d_%H%M%S")


def _writeOidsToCsv(filePath, oidList):
    with open(filePath, 'w') as output:
        output.write('id\n')
        for id in oidList:
            output.write(str(id) + '\n')


def getHashValuesFromWKB(featureClass, hashField):
    """Hash the well known binary of each shape."""
    with arcpy.da.UpdateCursor(featureClass, ['SHAPE@WKB', hashField]) as cursor:
        for row in cursor:
            wkb = row[0]
            hashTest = hashlib.md5(wkb)
            row[1] = hashTest.hexdigest()
            cursor.updateRow(row)


def hashCompareWkb(feature1, feature2):
    """Hash the well known binary of each shape."""
    hashLookup = {}
    feature2NotFound = []
    with arcpy.da.SearchCursor(feature1, ['OID@', 'SHAPE@WKB']) as cursor:
        for row in cursor:
            oid, wkb = row
            if wkb is None:
                continue
            hasher = hashlib.md5(wkb)
            hexDigest = hasher.hexdigest()
            if hexDigest not in hashLookup:
                hashLookup[hexDigest] = [oid, 0]
            else:
                print 'WTF!!! Duplicate hash OID: {}'.format(oid)

    with arcpy.da.SearchCursor(feature2, ['OID@', 'SHAPE@WKB']) as cursor:
        for row in cursor:
            oid, wkb = row
            if wkb is None:
                continue
            hasher = hashlib.md5(wkb)
            hexDigest = hasher.hexdigest()
            if hexDigest not in hashLookup:
                feature2NotFound.append(oid)
            else:
                hashLookup[hexDigest][1] += 1
    feature1NotFound = [x[0] for x in hashLookup.values() if x[1] == 0]
    duplicateMatches = [x[0] for x in hashLookup.values() if x[1] > 1]
    found = [x[0] for x in hashLookup.values() if x[1] == 1]
    print
    print 'f1 not found:      {}'.format(len(feature1NotFound))
    print 'f2 not found:      {}'.format(len(feature2NotFound))
    print 'duplicate matches: {}'.format(len(duplicateMatches))
    print 'matched oids:      {}'.format(len(found))
    print
    # _writeOidsToCsv(r'C:\GisWork\temp\hashOther\feature1' + uniqueRunNum + '.csv',
    #                 feature1NotFound)
    # _writeOidsToCsv(r'C:\GisWork\temp\hashOther\feature2' + uniqueRunNum + '.csv',
    #                 feature2NotFound)


def hashAllFields(featureClass):
    """Hash the attributes of each feature."""
    hasher = hashlib.md5()
    fields = [f.name for f in arcpy.ListFields(featureClass) if not f.name.lower().startswith('shape')]
    fields.remove('OBJECTID')
    fields.sort()
    fields.append('OID@')
    rowList = None
    with arcpy.da.SearchCursor(featureClass, fields) as cursor:
        # print cursor.fields
        # for row in cursor:
        #     strR = [str(x) for x in row[:-1]]
        #     s = "".join(strR)
        #     hasher.update(s)
        rowList = sorted(cursor, key=itemgetter(len(fields) - 1))
    for row in rowList:
        strR = [str(x) for x in row[:-1]]
        s = "".join(strR)
        hasher.update(s)

    print hasher.hexdigest()


def getFeatureHash(featureClass):
    """Hash each feature."""
    oidHashes = {}
    with arcpy.da.SearchCursor(featureClass, ['*', 'SHAPE@WKB', 'OID@']) as cursor:
        for row in cursor:
            hasher = hashlib.md5()
            strR = [str(x) for x in row[:-2]]
            hasher.update(b''.join(strR))
            if row[-2] is not None:
                hasher.update(row[-2])

            oidHashes[row[-1]] = hasher.hexdigest()
    return oidHashes


def hashAllVertices(featureClass):
    """Explode to points."""
    hasher = hashlib.md5()
    cursorTime = time()
    with arcpy.da.SearchCursor(featureClass,
                               ['SHAPE@X', 'SHAPE@Y'],
                               explode_to_points=True) as cursor:
        print 'cur time {}'.format(time() - cursorTime)
        for row in cursor:
            if row[0] is not None:
                hasher.update(str(round(row[0], 4)))
                hasher.update(str(round(row[1], 4)))

    print hasher.hexdigest()


def hashAllVerticesNumPy(featureClass):
    """Explode to points."""
    hasher = hashlib.md5()
    # arrayTime = time()
    xyArray = arcpy.da.FeatureClassToNumPyArray(featureClass,
                                                ('SHAPE@X', 'SHAPE@Y'),
                                                explode_to_points=True,
                                                skip_nulls=True)
    # print '{}'.format(time() - arrayTime)
    xyArray = numpy.around(xyArray.view(numpy.float64), 4)
    xyArray.sort()
    byteArray = xyArray.view(numpy.uint8)
    hasher.update(byteArray)
    print hasher.hexdigest()


def verticeSymDiff(featureClass):
    xys1 = arcpy.da.FeatureClassToNumPyArray(featureClass,
                                             ('SHAPE@X', 'SHAPE@Y'),
                                             explode_to_points=True,
                                             skip_nulls=True)
    numpy.around(xys1.view(numpy.float64), 4, xys1.view(numpy.float64))
    xys2 = arcpy.da.FeatureClassToNumPyArray(featureClass,
                                             ('SHAPE@X', 'SHAPE@Y'),
                                             explode_to_points=True,
                                             skip_nulls=True)
    numpy.around(xys2.view(numpy.float64), 4, xys2.view(numpy.float64))

    # xyArray = numpy.append(xyArray,
    #                        numpy.array([(1313.131313, 445454.454545), (224242424.24242, 56565.56565)],
    #                                    dtype=[('SHAPE@X', '<f8'), ('SHAPE@Y', '<f8')]))

    print xyArray.shape
    print xyArray2.shape
    # a1 = numpy.around(xyArray.view(numpy.float64), 4)
    # a2 = numpy.around(xyArray2.view(numpy.float64), 4)
    diff = numpy.setdiff1d(xyArray, xyArray2)
    print diff


def numpyTesting(featureClass):
    xys1 = arcpy.da.FeatureClassToNumPyArray(featureClass,
                                             ('SHAPE@X', 'SHAPE@Y'),
                                             explode_to_points=True,
                                             skip_nulls=True)
    numpy.around(xys1.view(numpy.float64), 4, xys1.view(numpy.float64))

    print xys1
    print xys1[xys1[:,1].argsort()]
    print xys1


def findDeletableNullGeometries(featureClass, oidList):


if __name__ == '__main__':
    # gdb = r'Database Connections\Connection to sgid.agrc.utah.gov.sde'
    # featureClass = os.path.join(gdb, 'SGID10.CADASTRE.Parcels_SaltLake')
    # otherGDB = r'C:\GisWork\temp\HashTest.gdb'
    # copyFC = os.path.join(otherGDB, 'SL_Full')
    # arcpy.CopyFeatures_management(featureClass, copyFC)
    # print featureClass

    # feature2 = r'C:\GisWork\temp\HashTest.gdb\SL_Full_shptogdb'
    # feature2 = os.path.join(r'Database Connections\Connection to sgid.agrc.utah.gov.sde', 'SGID10.CADASTRE.Parcels_SaltLake')
    # feature1 = r'C:\GisWork\temp\HashTest.gdb\SL_Full'
    # arcpy.CopyFeatures_management(feature1, feature2)

    # pr = cProfile.Profile()
    # pr.enable()
    # hashCompareWkb(feature1, feature2)
    # pr.create_stats()
    # pr.print_stats('cumulative')

    featureClass = r'C:\GisWork\temp\HashTest.gdb\OneParcel'
    numpyTesting(featureClass)
