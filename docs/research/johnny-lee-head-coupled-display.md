# Research - Johnny Lee Head-Coupled Perspective Displays

## Source

Johnny Lee's Wii Remote head tracking demonstrations.

Topics researched:

* Head-coupled perspective
* Virtual window rendering
* Wii Remote infrared tracking
* Off-axis projection
* Motion parallax

## Why I Looked Into This

While developing the image-sequence rendering pipeline, a question arose:

"How do existing systems keep the monitor boundaries aligned with the rendered scene when the viewer moves?"

Research into Johnny Lee's head-coupled perspective demonstrations provided the answer and introduced the concept of off-axis projection.

## Summary

Johnny Lee demonstrated that a standard monitor can appear to function as a window into a virtual world.

By tracking the viewer's head position and adjusting the rendered perspective accordingly, the brain perceives depth beyond the physical boundaries of the display.

The monitor effectively becomes a virtual window.

## Core Idea

Traditional rendering assumes:

* Fixed viewer
* Fixed camera
* Symmetric projection

Johnny Lee's approach assumes:

* Moving viewer
* Dynamic projection
* Off-axis viewing frustum

The projection is recalculated so that rays extending from the viewer's eye pass through the screen boundaries.

## Why It Works

The human visual system uses motion parallax as a depth cue.

When the viewer moves:

* Near objects appear to move more.
* Distant objects appear to move less.

If the rendered scene updates correctly, the brain interprets the monitor as a window rather than a flat image.

## Similarities To This Project

### Head Tracking

Johnny Lee:

* Tracks viewer position.

This project:

* Uses webcam face tracking.

### Virtual Window

Johnny Lee:

* Treats the monitor as the projection plane.

This project:

* Models the monitor opening as the entrance to a virtual room.

### Perspective Rendering

Johnny Lee:

* Uses off-axis projection.

This project:

* Uses Blender camera shifts and custom projection logic.

## Differences From This Project

### Rendering Method

Johnny Lee:

* Real-time rendering.

This project:

* Pre-rendered image sequences.

### Tracking Method

Johnny Lee:

* Wii Remote infrared tracking.

This project:

* Webcam face detection and tracking.

### Performance Strategy

Johnny Lee:

* GPU renders every frame.

This project:

* Maps tracked head positions to pre-rendered viewpoints.

## Key Lessons

1. Moving the camera alone is not sufficient.
2. The screen must remain the projection plane.
3. Off-axis projection is essential.
4. Motion parallax is the primary visual cue.
5. Accurate physical measurements improve realism.

## Relevance To Future Development

Potential future improvements:

* Real-time rendering pipeline.
* Depth interpolation between viewpoints.
* Hybrid image-sequence and off-axis rendering.
* Multi-monitor support.
* True eye-position based projection.

## Impact On Project Direction

Initially the project was planned as a simple image-sequence wallpaper.

Research into Johnny Lee's work revealed that true head-coupled perspective requires off-axis projection.

This led directly to the development of the current Blender off-axis rendering system.

The project now more closely resembles a head-coupled perspective display than a conventional parallax wallpaper.
