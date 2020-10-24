import tensorflow as tf
from ..quartznet import layer, abstract

residual_dense = False

config = {
    'convnet_layers': [
        {
            'type': 'conv1d',
            'repeat': 1,
            'kernel_size': [11],
            'stride': [2],
            'num_channels': 256,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [11],
            'stride': [1],
            'num_channels': 256,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [11],
            'stride': [1],
            'num_channels': 256,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [13],
            'stride': [1],
            'num_channels': 384,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [13],
            'stride': [1],
            'num_channels': 384,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [17],
            'stride': [1],
            'num_channels': 512,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [17],
            'stride': [1],
            'num_channels': 512,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.8,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [21],
            'stride': [1],
            'num_channels': 640,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.7,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [21],
            'stride': [1],
            'num_channels': 640,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.7,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [25],
            'stride': [1],
            'num_channels': 768,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.7,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 5,
            'kernel_size': [25],
            'stride': [1],
            'num_channels': 768,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.7,
            'residual': True,
            'residual_dense': residual_dense,
        },
        {
            'type': 'conv1d',
            'repeat': 1,
            'kernel_size': [29],
            'stride': [1],
            'num_channels': 896,
            'padding': 'SAME',
            'dilation': [2],
            'dropout_keep_prob': 0.6,
        },
        {
            'type': 'conv1d',
            'repeat': 1,
            'kernel_size': [1],
            'stride': [1],
            'num_channels': 1024,
            'padding': 'SAME',
            'dilation': [1],
            'dropout_keep_prob': 0.6,
        },
    ],
    'dropout_keep_prob': 0.7,
    'initializer': tf.contrib.layers.xavier_initializer,
    'initializer_params': {'uniform': False},
    'normalization': 'batch_norm',
    'activation_fn': tf.nn.relu,
    'data_format': 'channels_last',
    'use_conv_mask': True,
}


class Model:
    def __init__(self, inputs, inputs_length, mode = 'train'):
        self.model = abstract.TDNNEncoder(config, None, mode = mode)
        input_dict = {'source_tensors': [inputs, inputs_length]}
        self.logits = self.model.encode(input_dict)
