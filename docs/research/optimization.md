# Research Notes - Playback Issues and Optimization Plan

## Context

The current prototype is able to display the rendered image sequence almost in real time based on face/head tracking input.

The lag is very small, only a few milliseconds, and is not very noticeable to the untrained eye. However, there are still a few important issues that need to be fixed before this prototype can scale properly.

The current system loads a large PNG image sequence into RAM and switches between frames based on the tracked face position. The prototype works, but the current method is not efficient enough for larger image counts, higher resolutions, or smoother view dependent rendering.

## Current Problems

### 1. High RAM Usage

The current prototype loads the full PNG image sequence into RAM.

Current observed memory usage:

    ~4.8 GB of PNG images loaded into RAM

This happens because PNG files are compressed on disk, but once they are loaded using OpenCV, they become raw pixel arrays in memory.

For example, a 1920 x 1080 image becomes:

    1920 x 1080 x 3 channels = 6,220,800 bytes
    ≈ 6 MB per image

So if the sequence has around 800 images:

    800 x 6 MB = ~4.8 GB

This matches the current RAM usage.

Loading every image into RAM works for a small prototype, but it does not scale well.

If the number of views increases, RAM usage will increase very quickly:

    1000 images ≈ 6 GB
    2000 images ≈ 12 GB
    3000 images ≈ 18 GB

This becomes impractical for normal systems.

It also makes the program heavier, slower to start, and harder to run on different machines.

### 2. Small Input-to-Display Lag

The prototype is almost real time, but there is still a tiny amount of lag.

The lag is only a few milliseconds and is not very noticeable to the untrained eye, but it is still present.

Possible sources of lag:

    - Webcam capture delay
    - Face detection processing time
    - Image index calculation
    - Image loading or switching
    - cv2.imshow display refresh delay

Even if each step only takes a little time, the total delay can become visible if the system is pushed harder.

For a normal image viewer, a few milliseconds do not matter much.

But for a face-tracked 3D wallpaper, the illusion depends on the image changing almost instantly with head movement.

Even small lag can make the effect feel slightly disconnected from the viewer's motion.

### 3. Y-Axis Motion Is Not Smooth Enough

The Y-axis movement does not feel as smooth as desired.

This is mainly because the image count along the horizontal viewing direction is still low.

If the horizontal angle range is large, but the number of rendered images is low, each image represents a relatively large angle step.

Example:

    Y angle range = -25° to +25°
    Total range = 50°
    Y views = 60
    Step size = 50 / 59 ≈ 0.85° per image

A step size of almost 1 degree per image can be visible, especially during slow head movement.

Horizontal head movement is more common and more noticeable than vertical movement.

The viewer usually moves left and right more than up and down.

Because of this, the horizontal/Y-axis image count should be higher than the vertical/Z-axis image count.

The system does not need equal image counts on both axes.

Bad idea:

    Y_VIEWS = 100
    Z_VIEWS = 100
    Total = 10,000 images

Better idea:

    Y_VIEWS = 121
    Z_VIEWS = 9
    Total = 1089 images

This gives smoother horizontal movement without exploding the total render count too much.

## Proposed Solutions

### Solution 1: Stop Loading All Images Into RAM

The first major optimization is to stop loading the entire image sequence at startup.

Current approach:

    images = []

    for path in image_paths:
        img = cv2.imread(path)
        images.append(img)

This loads every image into memory.

The better approach is to use a cache system that loads only the required images and nearby images.

## LRU Image Cache

### What Is an LRU Cache?

LRU means:

    Least Recently Used

An LRU cache keeps recently used images in memory and removes the least recently used image when the cache becomes too large.

For this project, it means:

    Only keep the current image and nearby/recently used images in RAM.
    Do not keep the full image sequence in RAM.

Example:

    Current image index = 250

    Keep in RAM:
    240 to 260

    Do not keep:
    0 to 239
    261 to 800

This massively reduces RAM usage while still allowing smooth playback.

### Why LRU Cache Fits This Project

The face-tracked wallpaper does not randomly jump across the full image sequence most of the time.

Head movement is usually continuous.

That means if the current image is index 250, the next image will probably be near 249, 250, or 251.

So it makes sense to keep nearby frames ready.

LRU works well because it automatically keeps recently accessed images and removes older unused ones.

### Why Not Load Everything?

Loading everything gives the fastest switching once loaded, but it uses too much RAM.

Advantages:

    - Very fast image switching
    - Simple code
    - No disk reads during playback

Disadvantages:

    - Huge RAM usage
    - Slow startup
    - Does not scale with higher image counts
    - Bad for machines with less memory
    - Makes future larger renders impractical

Because the current sequence already uses around 4.8 GB RAM, loading everything is not a good long-term solution.

### Why Not Load From Disk Every Frame?

Another option is to load the image from disk only when needed.

Example:

    img = cv2.imread(image_paths[index])

Advantages:

    - Very low RAM usage
    - Simple logic

Disadvantages:

    - Causes stutter
    - Disk reads are slower than RAM access
    - PNG decoding every frame is expensive
    - Bad for real-time playback

This is not good for a face-tracked display because every head movement could trigger a disk read.

The result would be inconsistent frame timing and visible micro-stutters.

### Why Not Convert Everything to Video Immediately?

A video file would reduce disk size and may be easier to stream.

However, this project does not behave exactly like a normal video.

In a normal video, frames are played sequentially:

    1, 2, 3, 4, 5, 6...

In this project, frames are selected based on head position:

    250, 251, 250, 249, 252, 260...

This means the system needs random access to views.

Video codecs are not always good for random access because they often depend on previous and future frames.

Advantages of video:

    - Smaller file size
    - Better disk storage efficiency
    - Common playback format

Disadvantages:

    - Random frame access can be slower
    - Compression may reduce image quality
    - More complicated indexing
    - Not ideal for 2D grid view selection

Video may be useful in the future, but it is not the best next step for this prototype.

### Why Not Use OpenGL or GPU Textures Immediately?

A GPU texture system would eventually be better for performance.

The image sequence could be uploaded to GPU memory and displayed using OpenGL, DirectX, Vulkan, Unity, Unreal, or a wallpaper-engine-style system.

Advantages:

    - Very fast display
    - Better frame timing
    - Better interpolation possibilities
    - More professional rendering pipeline

Disadvantages:

    - More complex
    - Requires learning a graphics pipeline
    - More difficult to debug
    - Too early for the current prototype stage

The current prototype still needs simple testing and logic validation.

So OpenCV plus caching is better for now.

GPU rendering can be a future upgrade once the mapping and image sequence system are stable.

## LRU Cache Implementation Idea

A simple LRU cache can be built using Python's OrderedDict.

    from collections import OrderedDict
    import cv2

    class ImageCache:
        def __init__(self, image_paths, max_cache_size=40):
            self.image_paths = image_paths
            self.max_cache_size = max_cache_size
            self.cache = OrderedDict()

        def get(self, index):
            index = max(0, min(index, len(self.image_paths) - 1))

            if index in self.cache:
                self.cache.move_to_end(index)
                return self.cache[index]

            img = cv2.imread(self.image_paths[index])

            if img is None:
                raise FileNotFoundError(f"Could not load image: {self.image_paths[index]}")

            self.cache[index] = img
            self.cache.move_to_end(index)

            if len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)

            return img

Usage:

    cache = ImageCache(image_paths, max_cache_size=40)

    img = cache.get(image_index)
    cv2.imshow("3D Wallpaper", img)

This reduces RAM usage because only a limited number of images are stored at once.

## Preloading Nearby Images

A basic LRU cache loads images only when they are requested.

This is better than loading everything, but it can still cause a small stutter the first time a new image is loaded.

To reduce this, nearby images can be preloaded.

Example:

    def preload_around(cache, center_index, radius=8):
        start = max(0, center_index - radius)
        end = min(len(cache.image_paths), center_index + radius + 1)

        for i in range(start, end):
            cache.get(i)

Usage:

    img = cache.get(index)
    preload_around(cache, index, radius=8)
    cv2.imshow("3D Wallpaper", img)

This keeps the current image and nearby frames ready.

Possible issue:

    If preloading happens inside the main loop, it may still block the display slightly.

A future improvement would be to preload nearby images in a background thread.

## Solution 2: Smooth the Input Index

The current index may be changing too directly based on face position.

If the face coordinate changes slightly, the displayed image index may also jump.

This can create visible stepping or jitter.

Instead of directly using:

    display_index = target_index

Use smoothing:

    smoothed_index = smoothed_index + (target_index - smoothed_index) * 0.3
    display_index = round(smoothed_index)

This makes image changes softer.

### Why Use Index Smoothing?

Index smoothing helps reduce sudden jumps caused by:

    - Small face detection noise
    - Tiny coordinate changes
    - Webcam tracking jitter
    - Low number of rendered views

It makes the displayed view feel more stable.

### Smoothing Strength

A good starting value:

    0.2 to 0.35

Example:

    SMOOTHING = 0.3

Higher smoothing:

    - Smoother motion
    - More delay

Lower smoothing:

    - More responsive
    - More jitter

For this project, smoothing should be used carefully because too much smoothing will add noticeable lag.

## Solution 3: Use Float-Based Indexing

Instead of converting the mapped value directly to an integer, keep it as a float.

Bad approach:

    image_index = int(mapped_value)

Better approach:

    float_index = mapped_value

Then split it into:

    index_a = int(float_index)
    index_b = min(index_a + 1, num_images - 1)
    t = float_index - index_a

This allows interpolation or blending between two nearby images.

## Solution 4: Blend Between Adjacent Images

To reduce visible stepping, the program can blend between two neighboring rendered views.

Example:

    float_index = 40.3

    index_a = 40
    index_b = 41
    t = 0.3

Then the displayed image becomes:

    70% image 40
    30% image 41

OpenCV code:

    display = cv2.addWeighted(img_a, 1 - t, img_b, t, 0)

Full example:

    base_index = int(smoothed_index)
    next_index = min(base_index + 1, num_images - 1)
    t = smoothed_index - base_index

    img_a = cache.get(base_index)
    img_b = cache.get(next_index)

    display = cv2.addWeighted(img_a, 1 - t, img_b, t, 0)

### Why Blending Helps

If the image count is low, the display jumps from one rendered view to another.

Blending creates intermediate-looking frames without actually rendering more images.

This can make motion feel smoother.

### Downside of Blending

Blending can cause slight ghosting.

This happens because two different perspective views are being mixed together.

If the angle difference between images is small, the ghosting may not be very noticeable.

If the angle difference is large, blending may look blurry or doubled.

Blending is useful for the prototype, but it is not a perfect replacement for rendering more views.

## Solution 5: Increase Y-Axis Render Count

The most accurate way to make Y-axis movement smoother is to render more horizontal views.

Current issue:

    Y-axis image count is too low.

Recommended next test:

    Y_VIEWS = 121
    Z_VIEWS = 9

Total images:

    121 x 9 = 1089 images

This keeps the vertical count low while improving the more important horizontal direction.

A later higher-quality test:

    Y_VIEWS = 181
    Z_VIEWS = 11

Total images:

    181 x 11 = 1991 images

This would be smoother, but it also increases render time, storage, and possible RAM usage.

With LRU caching, the RAM problem becomes manageable even with higher image counts.

## Why Y Views Should Be Higher Than Z Views

The viewer usually moves more horizontally than vertically.

Horizontal motion is also more noticeable for a screen-based 3D illusion.

So the image sequence should prioritize Y-axis smoothness.

Recommended structure:

    High Y view count
    Lower Z view count

Example:

    Y_VIEWS = 121
    Z_VIEWS = 9

Avoid:

    Y_VIEWS = 100
    Z_VIEWS = 100

because that creates too many total images and wastes renders on vertical motion that is less important.

## Solution Comparison

### Full RAM Loading

Description:

    Load every image into RAM at startup.

Pros:

    - Fastest access after loading
    - Simple to implement
    - No disk reads during playback

Cons:

    - Huge RAM usage
    - Slow startup
    - Does not scale
    - Bad for larger render counts
    - Already using around 4.8 GB RAM

Verdict:

    Good for a very early prototype, but not suitable anymore.

### Disk Loading Every Frame

Description:

    Read image files from disk whenever the index changes.

Pros:

    - Very low RAM usage
    - Simple to implement

Cons:

    - Slow
    - Causes stutters
    - PNG decoding every frame is expensive
    - Bad for real-time movement

Verdict:

    Not suitable for this project.

### LRU Cache

Description:

    Keep only recently used and nearby images in RAM.

Pros:

    - Much lower RAM usage
    - Still fast for nearby image switching
    - Works well with continuous head movement
    - Simple enough for current prototype
    - Scales better than full RAM loading

Cons:

    - First access to uncached image may stutter
    - Needs cache management logic
    - May need background preloading later

Verdict:

    Best current solution.

This is the best balance between simplicity, speed, and memory efficiency.

### LRU Cache With Nearby Preloading

Description:

    Use an LRU cache, but also preload frames around the current index.

Pros:

    - Lower RAM than full loading
    - Reduces stutter
    - Better real-time feel
    - Takes advantage of predictable head movement

Cons:

    - More code
    - If done in the main loop, preloading can still block
    - Best version may require threading

Verdict:

    Best near-term upgrade after basic LRU cache.

### Adjacent Image Blending

Description:

    Blend between two neighboring views using the fractional image index.

Pros:

    - Makes motion smoother
    - Reduces visible stepping
    - Avoids needing many more renders immediately
    - Easy to test with OpenCV

Cons:

    - Can create ghosting
    - Not physically perfect
    - Works best only when angle gaps are small

Verdict:

    Very useful for smoothing the current prototype.

Should be tested before rendering a much larger sequence.

### More Y-Axis Renders

Description:

    Increase the number of horizontal rendered views.

Pros:

    - Most accurate solution
    - Reduces angular step size
    - Improves real parallax smoothness
    - Better than artificial smoothing

Cons:

    - More render time
    - More disk storage
    - More total images
    - More indexing complexity

Verdict:

    Necessary for final quality, but should be combined with caching.

Recommended next test:

    Y_VIEWS = 121
    Z_VIEWS = 9

### Video-Based Playback

Description:

    Convert the image sequence into a video and access frames from it.

Pros:

    - Smaller storage size
    - Common media format
    - Efficient sequential playback

Cons:

    - Not ideal for random frame access
    - Video codecs often depend on nearby frames
    - Harder to map a 2D view grid
    - May reduce image quality

Verdict:

    Not the best solution right now.

Maybe useful later for storage or previewing, but not ideal for real-time random-access view selection.

### OpenGL or GPU Texture System

Description:

    Use GPU rendering instead of OpenCV image display.

Pros:

    - Very fast rendering
    - Better frame timing
    - More professional display system
    - Better suited for final wallpaper engine

Cons:

    - More complex
    - Requires new rendering pipeline
    - Harder to debug
    - Too early for the current prototype stage

Verdict:

    Good future direction, but not the next immediate step.

## Recommended Fix Order

### Step 1: Add Index Smoothing

This is the easiest improvement.

It should reduce visible jitter and harsh stepping.

Example:

    smoothed_index = smoothed_index + (target_index - smoothed_index) * 0.3
    display_index = round(smoothed_index)

### Step 2: Use Float-Based Indexing

Instead of immediately rounding the mapped value, preserve the decimal part.

Example:

    float_index = mapped_value

This allows blending between views.

### Step 3: Add Adjacent Image Blending

Use the fractional part of the index to blend between two neighboring images.

Example:

    base_index = int(smoothed_index)
    next_index = min(base_index + 1, num_images - 1)
    t = smoothed_index - base_index

    img_a = cache.get(base_index)
    img_b = cache.get(next_index)

    display = cv2.addWeighted(img_a, 1 - t, img_b, t, 0)

This should make the Y-axis movement feel smoother without immediately rendering a larger sequence.

### Step 4: Replace Full RAM Loading With LRU Cache

Stop loading all images at startup.

Use an LRU image cache with a limited size.

Recommended starting cache size:

    40 to 80 images

This should reduce memory usage heavily while keeping playback responsive.

### Step 5: Add Nearby Preloading

Once the basic cache works, preload nearby images around the current index.

Recommended starting preload radius:

    8 to 12 images

This should reduce first-access stutter.

### Step 6: Render More Y Views

After the software side is improved, test a higher Y view count.

Recommended next render:

    Y_VIEWS = 121
    Z_VIEWS = 9

Later high-quality test:

    Y_VIEWS = 181
    Z_VIEWS = 11

## Future Solutions

### 1. Background Preloading Thread

Instead of preloading nearby images inside the main display loop, a separate thread can load nearby images in the background.

This would prevent image loading from blocking the display.

Possible structure:

    Main thread:
    - Capture webcam
    - Track face
    - Calculate image index
    - Display image

    Background thread:
    - Preload nearby image indices
    - Manage cache

This would make playback smoother and reduce micro-stutters.

### 2. Better Face Tracking

Currently, face detection can introduce small delays and jitter.

Future options:

    - Detect face every few frames instead of every frame
    - Track face position between detections
    - Use a smoother tracker
    - Use MediaPipe Face Mesh or another lightweight tracker
    - Use eye position instead of face rectangle center

Eye tracking may eventually give better perspective mapping than full face tracking.

### 3. Better Display Backend

OpenCV is good for prototyping, but it may not be ideal for the final wallpaper.

Future display options:

    - PyQt
    - Pygame
    - OpenGL
    - DirectX
    - Vulkan
    - Unity
    - Unreal Engine
    - Wallpaper Engine style implementation

A proper graphics backend would give better display control and frame timing.

### 4. GPU Texture Array

A future optimized version could upload the views to GPU memory and sample them directly.

This could allow:

    - Faster switching
    - Better interpolation
    - Smoother rendering
    - Lower CPU load

This is not needed yet, but it could become important for a final version.

### 5. Rendered View Grid Optimization

Instead of rendering equal view counts in both directions, the render grid should be optimized based on real viewing behavior.

Likely final structure:

    More horizontal views
    Fewer vertical views
    Possibly non-linear angle spacing

Non-linear spacing could be useful because head movement near the center may need more precision than extreme angles.

Example future idea:

    Dense views near 0°
    Fewer views near the edges

### 6. Adaptive Quality

The system could adapt quality based on performance.

Example:

    If tracking is stable:
    - Use blending
    - Use high-quality views

    If movement is fast:
    - Skip blending
    - Display nearest cached frame

    If cache miss occurs:
    - Temporarily show nearest cached frame

This would make the system feel more responsive even under load.

## Current Best Technical Direction

The best current direction is:

    Use OpenCV for now.
    Stop loading the full sequence into RAM.
    Add an LRU image cache.
    Add smoothing to the mapped image index.
    Use float-based indexing.
    Blend adjacent images to reduce stepping.
    Increase Y-axis render count later.

This keeps the project simple while solving the biggest current problems.

## Planned Prototype Upgrade

### Prototype 02 Goals

    - Reduce RAM usage
    - Improve Y-axis smoothness
    - Reduce visible stepping
    - Keep display close to real time
    - Avoid overcomplicating the rendering system too early

### Prototype 02 Features

    - LRU image cache
    - Optional nearby preload
    - Smoothed face coordinate or image index
    - Float-based image index calculation
    - Adjacent image blending
    - Separate Y and Z indexing logic

## Notes on Render Count

The number of views should be selected based on angle step size.

For horizontal motion:

    50° range with 60 views ≈ 0.85° per step
    50° range with 121 views ≈ 0.42° per step
    50° range with 181 views ≈ 0.28° per step

A good target for smooth motion is probably:

    0.25° to 0.5° per horizontal image step

This means 121 to 181 Y views is a reasonable next target.

## Final Decision

The next focus should be software-side optimization before rendering a much larger sequence.

Immediate next steps:

    1. Add image index smoothing
    2. Add float-based indexing
    3. Add adjacent-frame blending
    4. Replace full RAM loading with LRU cache
    5. Add nearby preloading
    6. Then test a higher Y view render

This should address the current issues without making the system unnecessarily complex too early.

## Possible Commit Message

    git commit -m "Document playback optimization research and prototype issues"

Alternative:

    git commit -m "Add research notes for image caching and smooth view playback"