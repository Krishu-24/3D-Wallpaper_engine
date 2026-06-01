# Session 1 -  april 1, 2026

## Objective

- Perform an initial test of OpenCV face detection using the Haar Cascade classifier and evaluate its suitability for real time face tracking (check for frame rate and accuracy).

## Work Done

- Implemented face detection using OpenCV's Haar Cascade classifier.
- Created three separate display windows for analysis:
    1. Original color video feed with face detection overlay.
    2. Grayscale video feed with face detection overlay to evaluate tracking performance.
    3. Cropped face-only view to observe tracking boundaries and face positioning.
- Tested OpenCV drawing and image processing functions required for future tracking and visualization tasks.
## Findings
- Face detection operated at acceptable frame rates with minimal latency.
- Estimated user distance from the camera can be inferred from the size of the detected face bounding box: ```python cv2.rectangle(img, (x, y), (x+w, y+h), (255,255,0), 5, 2) ``` As the face moves closer to the camera, the bounding box dimensions increase proportionally.

## Problems

- Tracking reliability decreases significantly when the face is rotated away from a frontal view.
- Detection is frequently lost as soon as the face approaches the edge of the camera frame.
- Haar Cascade detection appears limited for handling even small head rotations.

## Next Steps

- map an image sequence to the tracked face using the coordinates of the rectangle.
