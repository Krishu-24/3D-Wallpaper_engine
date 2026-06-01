import cv2 
import os

images =[]
folder = r"C:\Users\Arnav Sinha\Desktop\krishu\codes_projects\3D_Wallpaper_engine\assets\cube\test_cube_imageseq50_1"
image_start = 1
num_images = 50
for i in range(num_images):
    frame=i+image_start
    path = os.path.join(folder,f"{frame:04d}.png")
    img=cv2.imread(path)
    images.append(img)
images.reverse()

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)
# capture frames from a camera
cap = cv2.VideoCapture(0)

# loop runs if capturing has been initialized.
while 1: 

    # reads frames from a camera
    ret, cam_f = cap.read() 

    # convert to gray scale of each frames
    gray = cv2.cvtColor(cam_f, cv2.COLOR_BGR2GRAY)

    # Detects faces of different sizes in the input image
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x,y,w,h) in faces:
        # To draw a rectangle in a face 
        cv2.rectangle(gray,(x,y),(x+w,y+h),(255,255,0),5,2)
        #roi_gray = gray[y:y+h, x:x+w]# slices array(2d array for grayscale) for eye detection
        # Detects eyes of different sizes in the input image
        #eyes = eye_cascade.detectMultiScale(roi_gray) 
        image_index=int((x/500)*(num_images-1))
        image_index=max(0,min(num_images-1,image_index))
        # Display an image in a window
        cv2.namedWindow("wallpaper", cv2.WINDOW_AUTOSIZE)
        small = cv2.resize(images[image_index], (960, 540))
        cv2.imshow('wallpaper', small)
        #To draw a rectangle in eyes
        #for (ex,ey,ew,eh) in eyes:
           #cv2.rectangle(roi_color,(ex,ey),(ex+ew,ey+eh),(0,127,255),2)
        print(images[0].shape)
        
        

    # Wait for Esc key to stop
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

# Close the window
cap.release()

# De-allocate any associated memory usage
cv2.destroyAllWindows()