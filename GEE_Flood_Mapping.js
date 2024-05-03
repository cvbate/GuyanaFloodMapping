// Title: Google Earth Engine Flood Mapping
// Description: This file uses a simple thresholding method to identify floods.
// How to use: 1. Copy and paste this entire script into https://code.earthengine.google.com/
//             2. Import your area of interest as an asset and add it to your script.
//             3. Change the dates on lines 22 and 23 to match the desired time period.
//             4. Run the script and take a look at your newly created flood polygon!


//visualize Rupununi Wetlands

Map.addLayer(aoi, {}, 'aoi') //import your area of interest as an asset and add it to the map

//import the satalite image collection

var collection = ee.ImageCollection("COPERNICUS/S1_GRD")
.filterBounds(aoi)
.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
.select('VV') //selects VV band

//filter the before and after flood imagery

var before = collection.filterDate("2023-09-06", "2023-09-18").mosaic() //change dates as needed
var after = collection.filterDate("2023-11-05", "2023-11-17").mosaic() //change dates as needed

//clip the before and after iamges to area of interest

var before_clip = before.clip(aoi)
var after_clip = after.clip(aoi)

//apply smoothening filter

var before_s = before_clip.focal_median(30, "circle", "meters")
var after_s = after_clip.focal_median(30, "circle", "meters")

//calculate difference

var difference = after_s.subtract(before_s)

//apply threshold

var flood_extent = difference.lt(-3)
var flood = flood_extent.updateMask(flood_extent)

//display maps

Map.addLayer(before_clip, {min: -30, max: 0}, "Before Flood")
Map.addLayer(after_clip, {min: -30, max: 0}, "After Flood")
Map.addLayer(difference, {} , "Difference")
Map.addLayer(flood, {}, "flood")

//export image

Export.image.toDrive({
  image : flood.float(),
  description: "flood",
  scale: 10,
  maxPixels: 1e13,
  region: aoi,
  crs: "EPSG: 4326"
})
