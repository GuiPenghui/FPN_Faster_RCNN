# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import
import sys
sys.path.append('../')
import os
import math
import json
import numpy as np
import tensorflow as tf
import skimage.io
from config import TCTConfig

tf.app.flags.DEFINE_string('DATA_dir', None, 'the root of data dir')
tf.app.flags.DEFINE_string('save_dir',  '/home/data/tfrecords/',
                           'the absolutize path to save the converted tfrecord files')
tf.app.flags.DEFINE_string('dataset_name', 'tct', 'the name of dataset')
tf.app.flags.DEFINE_string('dataset_class', 'train', 'train, val, test')

FLAGS = tf.app.flags.FLAGS


def view_bar(message, num, total):
    rate = num / total
    rate_num = int(rate * 40)
    rate_nums = math.ceil(rate * 100)
    r = '\r%s:[%s%s]%d%%\t%d/%d' % (message, ">" * rate_num, " " * (40 - rate_num), rate_nums, num, total,)
    sys.stdout.write(r)
    sys.stdout.flush()


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def read_json_gtbox_and_label(image_item, data):

    """
    :param image_item: the record of single image
    :param data: the data load by json
    :return: a list contains gt boxes and labels, shape is [num_of_gtboxes, 5],
           and has [xmin, ymin, xmax, ymax, label] in a per row
    """
    config = TCTConfig()
    img_width = image_item["width"]
    img_height = image_item["height"]
    image_id = image_item["id"]
    category = data["categories"]
    box_list = []
    for bbox_item in data["annotations"]:
        temp_box = []
        if bbox_item["image_id"] == image_id:
            x1, y1, len_x, len_y = bbox_item["bbox"]
            x2 = x1 + len_x - 1
            y2 = y1 + len_y - 1
            temp_box.extend([x1, y1, x2, y2])
            ## change the object category id
            for category_item in category:
                if category_item["id"] == bbox_item["category_id"]:
                    label = config.NAME_TO_LABEL[category_item["name"]]
                    temp_box.append(label)
            assert len(temp_box) == 5
            box_list.append(temp_box)
    gtbox_label = np.array(box_list, dtype=np.int32)
    
    if np.shape(gtbox_label)[0] != 0:            
        xmin, ymin, xmax, ymax, label = gtbox_label[:, 0], gtbox_label[:, 1], gtbox_label[:, 2], gtbox_label[:, 3], gtbox_label[:, 4]
        gtbox_label = np.transpose(np.stack([ymin, xmin, ymax, xmax, label], axis=0))  # [ymin, xmin, ymax, xmax, label]

    return img_height, img_width, gtbox_label


def convert_json_to_tfrecord():

    json_path = os.path.join(FLAGS.DATA_dir, "annotations", FLAGS.dataset_class+'.json')
    Image_path = os.path.join(FLAGS.DATA_dir, "images", FLAGS.dataset_class)
    save_path = os.path.join(FLAGS.save_dir,  FLAGS.dataset_name, FLAGS.dataset_class+ '.tfrecord')
    mkdir(os.path.join(FLAGS.save_dir, FLAGS.dataset_name))

    # writer_options = tf.python_io.TFRecordOptions(tf.python_io.TFRecordCompressionType.ZLIB)
    # writer = tf.python_io.TFRecordWriter(path=save_path, options=writer_options)
    writer = tf.python_io.TFRecordWriter(path=save_path)
    with open(json_path, "r") as f:
        data = f.read()
        data = json.loads(data)
        total_len = len(data["images"])
        for count, item in enumerate(data["images"]):
            img_name = item["file_name"]
            img_height, img_width, gtbox_label = read_json_gtbox_and_label(item, data)
            if np.shape(gtbox_label)[0] == 0:
                continue
            # img = np.array(Image.open(img_path))
            image_path = os.path.join(Image_path, img_name)
            img = skimage.io.imread(image_path)

            feature = tf.train.Features(feature={
                # maybe do not need encode() in linux
                'img_name': _bytes_feature(img_name.encode()),
                'img_height': _int64_feature(img_height),
                'img_width': _int64_feature(img_width),
                'img': _bytes_feature(img.tostring()),
                'gtboxes_and_label': _bytes_feature(gtbox_label.tostring())
            })

            example = tf.train.Example(features=feature)

            writer.write(example.SerializeToString())

            view_bar('Conversion progress', count + 1, total_len)

    print('\nConversion is complete!')


if __name__ == '__main__':
    # xml_path = '../data/dataset/VOCdevkit/VOC2007/Annotations/000005.xml'
    # read_xml_gtbox_and_label(xml_path)

    convert_json_to_tfrecord()
