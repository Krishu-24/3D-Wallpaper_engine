# Journal: Keyframe-Based Render Automation

## Date

June 2, 2026

## Project

3D Wallpaper Engine / View-Dependent Rendering

## Session Objective

The objective of this session was to create a Blender automation workflow where the required camera views are generated using a script instead of manually setting up each render.

The final goal was to make the rendering process almost a one-click job. Once the script is run, Blender should automatically set all important parameters, generate the required keyframes, prepare the render animation, and then the user only has to click Render Animation.

---

## Background

For the 3D wallpaper project, the scene needs to be rendered from multiple viewing angles. These renders will later be used as an image sequence that changes based on the viewer’s face or eye position.

Initially, the process seemed like it would require manually moving the camera and rendering every angle one by one. This would be too slow, repetitive, and difficult to manage.

So the goal became:

> Create a script that automatically generates all required viewing angles as animation keyframes and sets up the scene for rendering.

---

## Problem We Started With

The render workflow originally required too much manual setup.

For the view-dependent wallpaper project, we needed multiple rendered images from different viewing angles. Manually positioning the camera, changing the angle, adjusting render settings, and exporting every frame one by one would be slow and error-prone.

The main problem was that the rendering process had to be repeatable. If the scene changed, or if the number of required views changed, doing everything manually again would waste a lot of time.

The main requirement was:

> Generate a controlled image sequence from different viewing angles so it can later be mapped to the viewer’s head position.

This meant the render setup needed to be based on parameters instead of manual camera placement.

---

## Stage 1: Understanding the Render Requirement

The first stage was understanding what the render sequence actually needed.

Since the final project depends on view-dependent rendering, we needed multiple images of the same 3D scene from different camera or viewing positions.

The important values identified were:

- Screen width in centimeters
- Screen height in centimeters
- Viewer distance from the screen
- Number of horizontal views
- Number of vertical views
- Horizontal angle range
- Vertical angle range
- Camera name
- Output folder

This helped convert the problem from a manual rendering task into a parameter-based system.

Instead of thinking:

> Move the camera manually and render many times.

The workflow became:

> Define the view range and let the script generate all the frames automatically.

This stage was important because it made the render system easier to control and easier to change later.

---

## Stage 2: Defining View Angles

The next stage was setting up controlled angle ranges for the views.

The horizontal viewing angle range was defined using:

```python
Y_ANGLE_MIN = -25
Y_ANGLE_MAX = 25
```

The vertical viewing angle range was defined using:

```python
Z_ANGLE_MIN = -10
Z_ANGLE_MAX = 10
```

The number of views was also controlled through variables:

```python
Y_VIEWS = 60
Z_VIEWS = 9
```

This means the script generates:

```python
60 * 9 = 540 frames
```

Each frame represents a different viewing position.

This was an important stage because it made the render sequence scalable. If smoother movement is needed later, the number of views can be increased. If faster testing is needed, the number of views can be reduced.

The number of views now depends only on input parameters, not on manual camera work.

---

## Stage 3: Automating Scene and Camera Setup

The script was then made responsible for setting up the Blender scene automatically.

The camera is selected using its name:

```python
CAMERA_NAME = "Camera.001"
```

Then the script gets the camera object and sets it as the active scene camera:

```python
cam = bpy.data.objects[CAMERA_NAME]
scene.camera = cam
```

The camera type is also set automatically:

```python
cam.data.type = "PERSP"
```

This makes the script more reliable because it does not depend on the camera being manually selected or correctly configured before rendering.

The script also sets the frame range:

```python
scene.frame_start = 1
scene.frame_end = Y_VIEWS * Z_VIEWS
```

So the number of frames in the animation is automatically based on the number of generated views.

This means that if the view count changes, the timeline updates automatically too.

---

## Stage 4: Generating Keyframes Automatically

The main breakthrough of the session was generating keyframes automatically.

Instead of rendering each camera position manually, the script generates a complete animation timeline.

Each frame in the timeline corresponds to one camera or view position.

The script loops through the horizontal and vertical view counts, calculates the required view for each frame, and inserts keyframes for the camera.

This turns the Blender animation timeline into a structured view sequence.

The advantage of this approach is that Blender’s normal Render Animation button can be used to render the entire image sequence.

So the render process changes from:

1. Move camera manually.
2. Render one image.
3. Move camera again.
4. Render another image.
5. Repeat many times.

To:

1. Run the script.
2. Click Render Animation.
3. Blender renders the full sequence automatically.

This was the stage where the workflow became much more practical.

---

## Stage 5: Automatic Output Folder Setup

The script also sets up the output folder for the rendered image sequence.

The output folder is defined as:

```python
OUTPUT_FOLDER = "//renders/off_axis_sequence"
```

The script converts this Blender-relative path into an absolute path:

```python
output_dir = bpy.path.abspath(OUTPUT_FOLDER)
```

Then it creates the folder if it does not already exist:

```python
os.makedirs(output_dir, exist_ok=True)
```

This prevents errors where the render fails because the output directory is missing.

The render filepath is then set automatically:

```python
scene.render.filepath = os.path.join(output_dir, "view_")
```

This means Blender will save the rendered frames in the correct folder with the prefix `view_`.

This stage made the rendering process cleaner because the output path no longer needs to be manually selected every time.

---

## Stage 6: Automatic Render Settings

The script also sets the render image format automatically.

The format is set to PNG:

```python
scene.render.image_settings.file_format = "PNG"
```

PNG is useful because it is lossless and works well for image sequences.

By setting this in the script, the render output does not depend on whatever format was previously selected in Blender.

This helps make the workflow repeatable and less error-prone.

The script now controls both the animation setup and the output settings.

---

## Stage 7: Turning the Render Sequence Into an Animation

A key realization was that the image sequence could be treated as an animation.

Each frame in Blender does not need to represent time in the usual sense. Instead, each frame can represent a different viewing angle.

This means:

- Frame 1 can represent the first view.
- Middle frames can represent center or intermediate views.
- Final frames can represent the last view.
- Vertical and horizontal views can be combined into a grid of frames.

This approach allows Blender’s animation system to handle the render sequence naturally.

Instead of writing a separate export system for every image, the script prepares the animation timeline and lets Blender render the frames normally.

---

## Stage 8: Making Rendering a One-Click Job

After the script prepares the scene, the final workflow becomes very simple.

The final workflow is:

1. Open the Blender file.
2. Run the keyframe generation script.
3. Click Render Animation.
4. Blender renders the full image sequence automatically.

The script now handles:

- Camera selection
- Camera setup
- Frame range setup
- Horizontal view count
- Vertical view count
- Angle range setup
- Output folder creation
- Render filepath setup
- Image format setup
- Keyframe generation
- Render sequence preparation

This makes the rendering process almost a one-click job after running the setup script.

The only manual step left is starting the animation render.

---

## Final Outcome

By the end of this stage, the rendering workflow became much more automated.

The script now automatically sets all the important parameters needed for rendering the animation and generates the camera keyframes required for the full image sequence.

This means there is no need to manually move the camera or render every angle separately.

The final result is a structured render animation where each frame represents a specific viewing angle.

Once the script is run, Blender is ready to render the complete image sequence with minimal manual work.

The major outcome was that the render setup became repeatable. If the number of views, angle range, camera, or output folder needs to change, those values can be changed in the script instead of manually editing the scene.

---

## Key Learning

This session showed that automation is very important for the view-dependent wallpaper project.

Instead of treating each render as a separate manual task, the scene can be converted into an animation where every frame represents a different camera view.

This makes the workflow:

- Faster
- More repeatable
- Easier to debug
- Easier to scale
- Better suited for future face-tracking integration

The biggest improvement was realizing that the render sequence can be generated using Blender’s keyframe system and then rendered normally using Render Animation.

This also makes the workflow easier to expand later. More views, different angle ranges, and different output folders can be handled by changing script parameters.

---

## Current Status

The keyframe generation script is now able to automatically prepare the render animation.

Once the script is run, Blender automatically sets the frame range, output folder, image format, camera setup, and keyframes.

The rendering stage is now mostly automated.

The project has reached the point where the render animation can be prepared through code and rendered using Blender’s Render Animation button.

---

## Next Steps

- Test the generated image sequence.
- Check whether the horizontal viewing angles feel natural.
- Check whether the vertical viewing angles are useful or need adjustment.
- Test the output sequence with the face-tracking script.
- Map face position to the correct rendered frame.
- Tune the number of views based on smoothness and render time.
- Reduce the number of views for quick testing if render time becomes too high.
- Increase the number of views later if smoother motion is needed.
- Document the final script parameters in the project README.
- Save the script in the correct project folder.
- Commit the script and journal once the output sequence is verified.
- Use this render sequence as the base for the image-mapping part of the project.

---

## Notes

This script is an important step because it connects the Blender rendering stage with the future real-time display stage.

The rendered frames generated from this script will later be used by the face-tracking program. The face-tracking script will detect the viewer’s position and choose the correct rendered image from the sequence.

So this stage prepares the visual data needed for the next part of the project.

The keyframe generation script does not just save time. It also makes the entire rendering pipeline more consistent and reliable.
````
