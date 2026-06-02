# Session 03 - Off-Axis Projection and Virtual Window Rendering

## Objective

Create a virtual scene that behaves like a room behind the monitor rather than a traditional 3D render displayed on a screen.

The goal is to eventually map head position from webcam face tracking to rendered viewpoints, creating the illusion that the monitor is a window into a virtual environment.

## Work Done

### Physical Monitor Modeling

Measured the monitor dimensions and created a virtual room using real-world scale.

Coordinate system used:

* X = depth
* Y = width
* Z = height

Room dimensions:

* Depth = 50 cm
* Width = 33 cm
* Height = 20.7 cm

The room was positioned so that the front opening lies on the X = 0 plane.

### Camera Calibration

Configured render resolution to match the monitor aspect ratio.

Positioned the camera at approximately 45.8 cm from the screen plane and adjusted it until the room opening completely filled the camera frame.

Observation:

The room opening must fill the entire render frame. Any visible space outside the opening immediately breaks the illusion.

### Room Construction

* Deleted the front face of the box.
* Flipped normals inward.
* Added materials and basic room geometry.
* Created an environment visible through the opening.

### Investigation of Viewpoint Rendering

Initially attempted to simulate head movement by translating a standard Blender camera.

Test:

* Move camera left and right.
* Render different viewpoints.

Result:

The room opening no longer remained aligned with the render boundaries.

The camera began revealing empty space outside the room.

Conclusion:

A standard perspective camera is insufficient for creating a head-coupled window effect.

### Key Discovery

At first it seemed obvious that moving the camera left and right would simulate a moving viewer.

This assumption turned out to be incorrect.

Testing revealed that a standard perspective camera exposes empty space outside the room and breaks the window illusion. This led to the discovery of off-axis projection.

### Discovery of Off-Axis Projection

Research led to the concept of asymmetric viewing frustums.

Instead of moving only the camera, the projection itself must change based on viewer position.

This allows:

* Fixed screen opening
* Moving eye position
* Consistent alignment between monitor edges and render boundaries

### Blender Script Development

Developed a Blender Python script to:

* Position a virtual eye
* Calculate projection offsets
* Apply camera shift values
* Simulate off-axis projection

Several iterations were required due to:

* Blender unit conversion issues
* Camera shift behaviour
* Sensor fit configuration differences
* Incorrect vertical projection scaling

### Unexpected Finding

A significant amount of time was spent debugging vertical frustum correction.

Horizontal correction worked almost immediately, while vertical correction required several iterations before a stable solution was found.

### Current Status

Successfully achieved:

* Horizontal viewpoint movement
* Vertical viewpoint movement
* Room opening remains pinned to render boundaries

This establishes a working off axis rendering system suitable for future image sequence generation.

## Key Findings

1. Moving a normal camera is not equivalent to moving the viewer.
2. The monitor opening must define the projection window.
3. Off axis projection is required for convincing head-coupled perspective.
4. Real-world monitor measurements simplify calibration.
5. Blender camera shift can be used to approximate off-axis projection behaviour.

## Problems Encountered

* Camera movement exposed empty space outside the room.
* Incorrect assumptions regarding symmetric camera frustums.
* Multiple failed attempts to correct vertical projection behaviour.
* Unit mismatch between Blender UI and Blender Python.

## Outcome

A functioning off axis camera system was implemented.

The virtual room behaves as a fixed window while the virtual eye position changes horizontally and vertically.

This is the most significant rendering milestone achieved so far.

## Next Steps

* Automate image sequence generation.
* Determine optimal number of rendered viewpoints.
* Integrate webcam face tracking.
* Map face position to viewpoint coordinates.
* Investigate render interpolation techniques.
