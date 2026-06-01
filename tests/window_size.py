import cv2

img = cv2.imread(r"C:\Users\Arnav Sinha\Desktop\krishu\codes_projects\3D_Wallpaper_engine\assets\cube\test_cube_imageseq50_1\0001.png")

small = cv2.resize(img, (960, 540))
cv2.imshow("test", small)
cv2.waitKey(0)
cv2.destroyAllWindows()