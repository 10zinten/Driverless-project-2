'Tran and validation data generator'

import os
import random
from copy import copy

import cv2
import numpy as np

from model.utils import get_filenames_and_labels

class Transform:
    def __init__(self, **kwargs):
        for arg, val in kwargs.items():
            setattr(self, arg, val)
        self.initialized = False

class ImageLoaderTransform(Transform):
    """
    load and image from the filename
    """
    def __call__(self, filename, label, gt):
        return cv2.imread(filename), label, gt

    def __repr__(self):
        return "ImageLoader Transform"

class BrightnessTransform(Transform):
    """
    Transforms the image brightness
    Parameters: delta
    """
    def __call__(self, data, label, gt):
        data = data.astype(np.float32)
        delta = random.randint(-self.delta, self.delta)
        data += delta
        data[data > 255] = 255
        data[data < 0] = 0
        data = data.astype(np.uint8)
        return data, label, gt

    def __repr__(self):
        return "Brightness Transform"

class ConstrastTransform(Transform):
    """
    Transform image constrast
    Parameters: lower, upper
    """
    def __call__(self, data, label, gt):
        data = data.astype(np.float32)
        delta = random.uniform(self.lower, self.upper)
        data *= delta
        data[data > 255] = 255
        data[data < 0] = 0
        data = data.astype(np.uint8)
        return data, label, gt

    def __repr__(self):
        return "Constrast Transform"

class HueTransform(Transform):
    """
    Transform hue
    Parameters: delta
    """
    def __call__(self, data, label, gt):
        data = cv2.cvtColor(data, cv2.COLOR_BGR2HSV)
        data = data.astype(np.float32)
        delta = random.randint(-self.delta, self.delta)
        data[0] += delta
        data[0][data[0] > 180] -= 180
        data[0][data[0] < 0] += 180
        data = data.astype(np.uint8)
        data = cv2.cvtColor(data, cv2.COLOR_HSV2BGR)
        return data, label, gt

    def __repr__(self):
        return "Hue Transform"

class SaturationTransform(Transform):
    """
    Transform saturation
    Parameters: lower, upper
    """
    def __call__(self, data, label, gt):
        data = cv2.cvtColor(data, cv2.COLOR_BGR2HSV)
        data = data.astype(np.float32)
        delta = random.uniform(self.lower, self.upper)
        data[1] *= delta
        data[1][data[1]>180] -= 180
        data[1][data[1]<0] +=180
        data = data.astype(np.uint8)
        data = cv2.cvtColor(data, cv2.COLOR_HSV2BGR)
        return data, label, gt

    def __repr__(self):
        return "Saturation Transform"

class ChannelsReorderTransform(Transform):
    def __call__(self, data, label, gt):
        channels = [0, 1, 2]
        random.shuffle(channels)
        return data[:, :, channels], label, gt

    def __repr__(self):
        return "Channels Reorder Transform"


class RandomTransform(Transform):
    """
    Call another transfrom with a given probability
    Parameters: prob, transform
    """
    def __call__(self, data, label, gt):
        p  = random.uniform(0, 1)
        if p < self.prob:
            return self.transform(data, label, gt)
        return data, label, gt

    def __repr__(self):
        return repr(self.transform)

class ComposeTransform(Transform):
    """
    call a bunch of transforms serially
    Parametes: transforms
    """
    def __call__(self, data, label, gt):
        args = (data, label, gt)
        for transform in self.transforms:
            args = transform(*args)
        return args

class TransformPickerTransform(Transform):
    """
    Call a randomly chosen transform from the list
    Parameters: transforms
    """
    def __call__(self, data, label, gt):
        self.pick = random.randint(0, len(self.transforms)-1)
        return self.transforms[self.pick](data, label, gt)

    def __repr__(self):
        return repr(self.transforms[self.pick])

def build_transforms(data):

    # Image distortions
    brightness = BrightnessTransform(delta=100)
    random_brightness = RandomTransform(prob=0.5, transform=brightness)

    constrast = ConstrastTransform(lower=0.5, upper=1.8)
    random_constrast = RandomTransform(prob=0.5, transform=constrast)

    hue = HueTransform(delta=100)
    random_hue = RandomTransform(prob=0.5, transform=hue)

    saturation = SaturationTransform(lower=0.5, upper=1.8)
    random_saturation = RandomTransform(prob=0.5, transform=saturation)

    channels_reorder = ChannelsReorderTransform()
    random_channels_reorder = RandomTransform(prob=0.5, transform=channels_reorder)

    # Compositions of image distortions
    distort_list = [
        random_constrast,
        random_hue,
        random_saturation,
    ]

    distort_1 = ComposeTransform(transforms=distort_list[:-1])
    distort_2 = ComposeTransform(transforms=distort_list[1:])
    distort_comp = [distort_1, distort_2]
    distort = TransformPickerTransform(transforms=distort_comp)

    if data == 'train':
        transforms = [
                ImageLoaderTransform(),
                random_brightness,
                distort,
                random_channels_reorder
            ]
    else:
        transforms = [
                ImageLoaderTransform()
            ]

    return transforms

class TrainingData:

    def __init__(self, image_dir, label_dir, param):
        train_filenames, train_labels = get_filenames_and_labels(image_dir, label_dir, 'train')
        nones = [None] * len(train_filenames)
        train_samples = list(zip(train_filenames, nones, train_labels))
        val_filenames, val_labels = get_filenames_and_labels(image_dir, label_dir, 'dev')
        nones = [None] * len(val_filenames)
        val_samples = list(zip(val_filenames, nones, val_labels))


        self.preset = None
        self.num_class = None
        self.train_tfs = build_transforms('train')
        self.val_tfs = build_transforms('val')
        self.train_generator  = self.__build_generator(train_samples, self.train_tfs)
        self.val_generator    = self.__build_generator(val_samples, self.val_tfs)
        self.num_train = None
        self.num_val = None
        self.train_samples = None
        self.val_samples = None

    def __build_generator(self, all_samples_, transforms):

        def run_transforms(sample):
            args = sample
            for transform in transforms:
                args = transform(*args)

            return args

        def process_samples(samples):
            images, labels, gt_boxes = [], [], []
            for sample in samples:
                image, label, gt = run_transforms(sample)
                images.append(image.astype(np.float32))
                labels.append(label)
                gt_boxes.append(gt)

            images = np.array(images, dtype=np.float32)

            return images, labels, gt_boxes


        def gen_batch(batch_size):
            all_samples = copy(all_samples_)
            random.shuffle(all_samples)

            for offset in range(0, len(all_samples), batch_size):
                samples = all_samples[offset: offset + batch_size]
                images, labels, gt_boxes = process_samples(samples)

                for transform in transforms:
                    print("[INFO] {} applied ... ok".format(transform))

                yield images, labels, gt_boxes

        return gen_batch