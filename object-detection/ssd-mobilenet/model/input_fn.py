"""Create the input data pipeline using tf.data"""

import tensorflow as tf

def _parse_function(filename, label):
    image_string = tf.read_file(filename)
    image_decoded = tf.image.decode_jpeg(image_string, channels=3)
    image = tf.image.convert_image_dtype(image_decoded, tf.float32)
    return image, label

def train_preprocess(image, label):
    image = tf.image.random_brightness(image, max_delta=32.0 / 255.0)
    image = tf.image.random_saturation(image, lower=0.5, upper=1.5)

    image = tf.clip_by_value(image, 0.0, 1.0)
    return image, label


def input_fn(is_training, filenames, labels, args):
    """Input functions for the Cones dataset."""

    num_samples = len(filenames)
    assert len(filenames) > 0, 'Datapoint not found'

    parse_fn = lambda f, l: _parse_function(f, l)
    # parse_fn = lambda f, l: train_preprocess(f, l)

    if is_training:
        dataset = (tf.data.Dataset.from_tensor_slices((tf.constant(filenames), tf.constant(labels)))
            .shuffle(num_samples)
            .map(parse_fn, num_parallel_calls=4)
            .batch(args.batch_size)
            .prefetch(1)
        )
    else:
        dataset = (tf.data.Dataset.from_tensor_slices((tf.constant(filenames), tf.constant(labels)))
               .map(parse_fn)
               .batch(args.batch_size)
               .prefetch(1)
        )


    # Create reinitializable iterator from dataset
    iterator = dataset.make_initializable_iterator()
    images, labels = iterator.get_next()
    iterator_init_op = iterator.initializer

    inputs = {'images': images, 'labels': labels, 'iterator_init_op': iterator_init_op}

    return inputs
