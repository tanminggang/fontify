import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageFilter
import math

from data import PERCENTAGE_TO_CROP_SCAN_IMG, CROPPED_IMG_NAME


def crop_by_percentage(origin_im, percentage):
    width, height = origin_im.size
    left = int(percentage * width)
    upper = int(percentage * height)
    right = int((1 - percentage) * width)
    lower = int((1 - percentage) * height)
    im = origin_im.crop((left, upper, right, lower))
    return im



def _detect_circles(filepath):
    tempfile_name = "wait_for_detect.bmp"
    origin_im = Image.open(filepath)
    im_blurred = origin_im.filter(ImageFilter.GaussianBlur(radius=10))
    im_blurred.save(tempfile_name)

    img = cv2.imread(tempfile_name,0)
    img = cv2.medianBlur(img,5)
    circles = cv2.HoughCircles(img,cv2.cv.CV_HOUGH_GRADIENT,1,20,
                               param1=50,param2=30,minRadius=10,maxRadius=500)
    circles = np.uint16(np.around(circles))

    two_circles = []
    for i in circles[0,:]:
        two_circles.append((i[0], i[1], i[2]))

    top_circle = two_circles[0]
    bottom_circle = two_circles[1]
    if top_circle[1] > bottom_circle[1]: #[0] => width, [1] => height
        temp = bottom_circle
        bottom_circle = top_circle
        top_circle = temp

    return top_circle, bottom_circle


def _restore_if_tilt(filepath):
    top_circle, bottom_circle = _detect_circles(filepath)

    expected_K = 1207.0 / 995
    expected_angle = math.atan(expected_K)

    actual_K = float(bottom_circle[1] - top_circle[1]) / (bottom_circle[0] - top_circle[0])
    actual_angle = math.atan(actual_K)

    origin_im = Image.open(filepath)
    rotate_angle = (actual_angle - expected_angle) / math.pi * 180 + 0.25

    print "rotate: {} degrees".format(rotate_angle)

    rotated_im = origin_im.rotate(rotate_angle)
    restored_image_filename = "restored_image.bmp"
    rotated_im.save(restored_image_filename)

    return restored_image_filename


def trim(origin_im, blur=True,
         pre_percentage=PERCENTAGE_TO_CROP_SCAN_IMG, upper_lower_cut=True):
    im = crop_by_percentage(origin_im, pre_percentage)
    if blur:
        im_blurred = im.filter(ImageFilter.GaussianBlur(radius=2))
        bg = Image.new(im_blurred.mode, im_blurred.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im_blurred, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
    else:
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        bbox = diff.getbbox()
    if bbox:
        if upper_lower_cut:
            return im.crop(bbox)
        else:
            width, height = im.size
            bbox = list(bbox)
            bbox[0] = max(0, bbox[0] - int(width * 0.05))
            bbox[1] = 0
            bbox[2] = min(width, bbox[2] + int(width * 0.05))
            bbox[3] = height
            return im.crop(bbox)
    else:
        # raise Exception("Error while cropping image, there is no bounding box to crop")
        return im


def crop_whole(filepath):
    restored_filepath = _restore_if_tilt(filepath)
    top_circle, bottom_circle = _detect_circles(restored_filepath)

    im = Image.open(restored_filepath)
    # im = trim(im)
    im = im.crop((top_circle[0], top_circle[1], bottom_circle[0], bottom_circle[1]))

    trimmed_filepath = os.path.join(
        os.path.dirname(filepath),
        CROPPED_IMG_NAME
    )
    im.save(trimmed_filepath)
    return trimmed_filepath


def crop_char(filepath):
    im = Image.open(filepath)
    im = trim(im, blur=False, pre_percentage=0, upper_lower_cut=False)
    im.save(filepath)


# for MANUAL unit test
if __name__ == "__main__":
    import sys
    trimmed_filepath = crop_whole(sys.argv[1])
    im = Image.open(trimmed_filepath)
    print trimmed_filepath
