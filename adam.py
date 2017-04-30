# -*- coding: utf-8 -*-

from __future__ import division
import cifar10, cifar10_input
import tensorflow as tf
import numpy as np
from datetime import datetime
import time
max_steps = 10000
batch_size = 128
data_dir = '/tmp/cifar10_data/cifar-10-batches-bin'

def variable_with_weight_loss(shape, stddev, w1):
    var = tf.Variable(tf.truncated_normal(shape, stddev = stddev))
    if w1 is not None:
        weight_loss = tf.multiply(tf.nn.l2_loss(var), w1, name = 'weight_loss')
        tf.add_to_collection('losses', weight_loss)
    return var
    
cifar10.maybe_download_and_extract()
images_train, labels_train = cifar10_input.distorted_inputs(data_dir = data_dir, batch_size = batch_size)
images_test, labels_test = cifar10_input.inputs(eval_data = True, data_dir = data_dir, batch_size = batch_size)
image_holder = tf.placeholder(tf.float32, [batch_size, 24, 24, 3])
label_holder = tf.placeholder(tf.int32, [batch_size])

weight1 = variable_with_weight_loss(shape = [5, 5, 3, 64], stddev = 5e-2, w1 = 0.0)
kernel1 = tf.nn.conv2d(image_holder, weight1, [1, 1, 1, 1], padding = 'SAME')
bias1 = tf.Variable(tf.constant(0.0, shape = [64]))
conv1 = tf.nn.relu(tf.nn.bias_add(kernel1, bias1))
pool1 = tf.nn.max_pool(conv1, ksize = [1, 3, 3, 1], strides = [1, 2, 2, 1], padding = 'SAME')
norm1 = tf.nn.lrn(pool1, 4, bias = 1.0, alpha = 0.001 / 9.0, beta = 0.75)

weight2 = variable_with_weight_loss(shape = [5, 5, 64, 64], stddev = 5e-2, w1 = 0.0)
kernel2 = tf.nn.conv2d(norm1, weight2, [1, 1, 1, 1], padding = 'SAME')
bias2 = tf.Variable(tf.constant(0.1, shape = [64]))
conv2 = tf.nn.relu(tf.nn.bias_add(kernel2, bias2))
norm2 = tf.nn.lrn(conv2, 4, bias = 1.0, alpha = 0.001 / 9.0, beta = 0.75)
pool2 = tf.nn.max_pool(norm2, ksize = [1, 3, 3, 1], strides = [1, 2, 2, 1], padding = 'SAME')

reshape = tf.reshape(pool2, [batch_size, -1])
dim = reshape.get_shape()[1].value
weight3 = variable_with_weight_loss(shape = [dim, 384], stddev = 0.04, w1 = 0.004)
bias3 = tf.Variable(tf.constant(0.1, shape = [384]))
local3 = tf.nn.relu(tf.matmul(reshape, weight3) + bias3)

weight4 = variable_with_weight_loss(shape = [384, 192], stddev = 0.04, w1 = 0.004)
bias4 = tf.Variable(tf.constant(0.1, shape = [192]))
local4 = tf.nn.relu(tf.matmul(local3, weight4) + bias4)


weight5 = variable_with_weight_loss(shape = [192, 10], stddev = 1.0 / 192.0, w1 = 0.0)
bias5 = tf.Variable(tf.constant(0.0, shape = [10]))
logits = tf.add(tf.matmul(local4, weight5), bias5)

def loss(logits, labels):
    labels = tf.cast(labels, tf.int32)
    cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits = logits, labels = labels, name = 'cross_entropy_per_example')
    cross_entropy_mean = tf.reduce_mean(cross_entropy, name = 'cross_entropy')
    tf.add_to_collection('losses', cross_entropy_mean)
    return tf.add_n(tf.get_collection('losses'), name = 'total_loss')


loss = loss(logits, label_holder)
train_op = tf.train.AdamOptimizer(1e-3).minimize(loss) ##############
#选择优化器Adam,学习率lr设为1e-3
# lr= 1e-2 迭代时 loss 无法下降
top_k_op = tf.nn.in_top_k(logits, label_holder, 1)
sess = tf.InteractiveSession()
tf.global_variables_initializer().run()

tf.train.start_queue_runners()
for step in range(1,max_steps):
    start_time = time.time()
    image_batch, label_batch = sess.run([images_train, labels_train])
    _, loss_value = sess.run([train_op, loss], feed_dict = {image_holder: image_batch, label_holder: label_batch})
    duration = time.time() - start_time
    if step % 10 == 0:
        examples_per_sec = batch_size / duration
        sec_per_batch = float(duration)

        format_str = ('%s: step %d, loss = %.2f(%.1f examples/sec; %.3f sec/batch)')
        print(format_str % (datetime.now(), step, loss_value, examples_per_sec, sec_per_batch))

# 检测
    if ((step % 100 == 0) | (step+1 == max_steps)):
        num_examples = 10000
        import math
        num_iter = int(math.ceil(num_examples / batch_size))
        true_count = 0
        total_sample_count = num_iter * batch_size
        # print total_sample_count
        step = 0
        while step < num_iter:
            image_batch, label_batch = sess.run([images_test, labels_test])
            predictions = sess.run([top_k_op], feed_dict = {image_holder: image_batch, label_holder: label_batch})
        
            true_count += np.sum(predictions)
            step += 1
            # print(true_count)
        precision = true_count / total_sample_count
        print('precision @ 1 = %.3f' %precision)    
