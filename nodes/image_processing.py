#!/usr/bin/python

import cv_bridge
import cv2
import numpy as np
import numpy.lib

bridge = cv_bridge.CvBridge()

def patch_normalise(image, patch_size):
	patch_half_size = [(p-1)/2 for p in patch_size]
	height, width = image.shape
	out = np.zeros(image.shape, dtype=float)
	with np.errstate(divide='ignore', invalid='ignore'):
		for y in range(height):
			for x in range(width):
				patch = image[	max(0, y-patch_half_size[1]):min(height, y+1+patch_half_size[1]),
								max(0, x-patch_half_size[0]):min(width, x+1+patch_half_size[0])]

				mu, stdev = mean_stdev_fast(patch)
				out[y,x] = (image[y,x] - mu) / stdev

	out[np.isnan(out)] = 0.0
	out[out < -1.0] = -1.0
	out[out > 1.0] = 1.0
	return out

def patch_normalise_patch(image, patch_size):
	patch_half_size = [(p-1)/2 for p in patch_size]
	height, width = image.shape
	out = np.zeros(image.shape, dtype=float)

	nrows = image.shape[0] - patch_size[0] + 1
	ncols = image.shape[1] - patch_size[1] + 1
	patches = get_patches(image, patch_size)
	mus, stds = mean_stdev_fast(patches, 0)

	with np.errstate(divide='ignore', invalid='ignore'):
		for y in range(height):
			for x in range(width):
				if x < patch_half_size[1] or y < patch_half_size[0] or width-x <= patch_half_size[1] or height-y <= patch_half_size[0]:
					patch = image[	max(0, y-patch_half_size[1]):min(height, y+1+patch_half_size[1]),
									max(0, x-patch_half_size[0]):min(width, x+1+patch_half_size[0])]
					mu, stdev = mean_stdev_fast(patch)
					out[y,x] = (image[y,x] - mu) / stdev

		yr = (patch_half_size[1], patch_half_size[1]+nrows)
		xr = (patch_half_size[0], patch_half_size[0]+ncols)
		out[yr[0]:yr[1], xr[0]:xr[1]] = (image[yr[0]:yr[1], xr[0]:xr[1]] - mus.reshape(nrows, ncols)) / stds.reshape(nrows, ncols)

	out[np.isnan(out)] = 0.0
	out[out < -1.0] = -1.0
	out[out > 1.0] = 1.0
	return out

def patch_normalise_pad(image, patch_size):
	patch_half_size = [(p-1)/2 for p in patch_size]
	height, width = image.shape

	image_pad = np.pad(np.float64(image), patch_half_size, 'constant', constant_values=np.nan)

	nrows = image.shape[0]
	ncols = image.shape[1]
	patches = get_patches(image_pad, patch_size)
	mus = np.nanmean(patches, 0)
	stds = np.nanstd(patches, 0)

	with np.errstate(divide='ignore', invalid='ignore'):
		out = (image - mus.reshape(nrows, ncols)) / stds.reshape(nrows, ncols)

	out[np.isnan(out)] = 0.0
	out[out < -1.0] = -1.0
	out[out > 1.0] = 1.0
	return out

def grayscale(image):
	return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def patch_normalise_msg(msg, patch_size, compressed=False, resize=None):
	if compressed:
		image = compressed_msg_to_image(msg)
	else:
		image = msg_to_image(msg)
	if resize is not None:
		image = cv2.resize(image, resize, interpolation=cv2.INTER_NEAREST)
	return patch_normalise_pad(grayscale(image), patch_size)

def msg_to_image(msg):
	try:
		image = bridge.imgmsg_to_cv2(msg)
	except cv_bridge.CvBridgeError as e:
		print(e)
		return
	return image

def compressed_msg_to_image(msg):
	try:
		image = bridge.compressed_imgmsg_to_cv2(msg)
	except cv_bridge.CvBridgeError as e:
		print(e)
		return
	return image

def get_patches(image, patch_size):
	nrows = image.shape[0] - patch_size[0] + 1
	ncols = image.shape[1] - patch_size[1] + 1
	return numpy.lib.stride_tricks.as_strided(image, patch_size + (nrows, ncols), image.strides + image.strides).reshape(patch_size[0]*patch_size[1],-1)

def mean_stdev_fast(array, axis=None):
	mu = np.mean(array, axis)
	sigma = np.sqrt(((array - mu)**2).mean(axis))
	return mu, sigma

def scan_horizontal_SAD_match(image, template, step_size=1):
	positions = range(0,image.shape[1]-template.shape[1],step_size)
	differences = [0] * len(positions)
	for i,pos in enumerate(positions):
		differences[i] = np.mean(np.abs(image[:,pos:pos+template.shape[1]] - template))
	index = np.argmin(differences)
	return positions[index], differences[index]

def scan_horizontal_SAD_match_pad(image, template, step_size=1):
	image_pad = np.pad(image, ((0,),(template.shape[1]-1,)), 'constant', constant_values=np.nan)
	positions = range(0,image.shape[1],step_size)
	differences = [0] * len(positions)
	for i,pos in enumerate(positions):
		differences[i] = np.nanmean(np.abs(image_pad[:,pos:pos+template.shape[1]] - template))
	index = np.argmin(differences)
	return positions[index]-(template.shape[1]-1), differences[index]

def scan_horizontal_SAD_match_patches(image, template):
	patches = get_patches(image, template.shape)
	differences = np.mean(np.abs(patches - template.ravel().reshape(-1,1)), 0)
	index = np.argmin(differences)
	return index, differences[index]

if __name__ == "__main__":
	np.random.seed(0)
	img = np.random.randint(0,256,(180,320), dtype=np.uint8)
	norm = patch_normalise_pad(img, (17,17))
	# cv2.imshow('img',img)
	# cv2.imshow('norm',norm)
	# cv2.waitKey()

	template_pos = 66
	template = img[:,template_pos:template_pos+140]
	template_norm = patch_normalise_pad(template, (17,17))

	import time
	t = time.time()
	print(scan_horizontal_SAD_match(norm, template_norm))
	print('%fs' % (time.time() - t))