# Session 2 – April 1, 2026

## Objective

* Create the first working prototype that maps face position to a rendered image sequence.
* Verify that real time face tracking can be used to drive perspective changes in a rendered scene.

## Work Done

* Used OpenCV Haar Cascade face detection to obtain real time face coordinates.
* Measured the usable horizontal tracking range of the webcam feed.
* Loaded a rendered image sequence into memory for fast runtime access.
* Implemented a mapping function that converts the detected face position into an image sequence index.
* Added bounds checking to prevent invalid image indices.
* Connected face tracking directly to image sequence display, creating the first working perspective shift prototype.
* Tested image switching responsiveness and visual smoothness using a 50 frame render sequence.
* Investigated image display issues and identified Windows display scaling as the cause of incorrect OpenCV rendering behavior.
* created a file to test the window size and image scaling

## Findings

* The tracked face position spans approximately 0–500 units along the horizontal axis with the current setup.
* The mapping function

  `image_index = int((x / 500) * (num_images - 1))`

  then reverseing the array successfully converts face position into a corresponding rendered frame.
* Preloading images into memory provides near instant image switching and is suitable for current sequence sizes.
* A 50 frame image sequence already produces smooth perspective transitions.
* Increasing the number of rendered frames should improve realism and reduce visible stepping between viewpoints.
* The current proof of concept demonstrates that face tracking can successfully control viewpoint selection in real time.

## Problems

* Face detection introduces small variations in position, causing occasional frame jitter.
* Current implementation only supports horizontal (1D) movement.
* Rendered perspective does not yet correspond to real world viewing geometry.
* Larger image sequences will increase memory usage.
* The test scene is too simple to accurately judge depth perception and realism.

## Next Steps

* Create configurable parameters for:

  * Camera field of view (FOV)
  * Rendered scene FOV
  * Number of images in the sequence
* Develop a mapping function that relates camera FOV to rendered viewing angles.
* Determine how head position and viewing distance affect the required rendered perspective.
* Stabilize tracked X and Y coordinates to reduce frame jitter.
* Expand the system from a 1D horizontal mapping to a 2D X-Y mapping.
* Design a more suitable test scene, such as a cube enclosed within a box, to better evaluate perceived depth.
* Display the rendered output in fullscreen mode to improve immersion and depth illusion.