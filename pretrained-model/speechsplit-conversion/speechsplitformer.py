import os

os.environ['CUDA_VISIBLE_DEVICES'] = '3'

import numpy as np
import random
import tensorflow as tf
from math import ceil
from glob import glob
from collections import defaultdict
from malaya_speech.train.model import speechsplit, speechsplitformer
from malaya_speech import train
import malaya_speech
import sklearn
import pickle

speaker_model = malaya_speech.speaker_vector.deep_model('vggvox-v2')
files = glob('speechsplit-dataset/*.pkl')
sr = 22050


def pad_seq(x, base = 8):
    len_out = int(base * ceil(float(x.shape[0]) / base))
    len_pad = len_out - x.shape[0]
    assert len_pad >= 0
    return np.pad(x, ((0, len_pad), (0, 0)), 'constant'), x.shape[0]


def generate(hop_size = 256):
    while True:
        shuffled = sklearn.utils.shuffle(files)
        for f in shuffled:
            with open(f, 'rb') as fopen:
                wav, f0, mel = pickle.load(fopen)

            batch_max_steps = random.randint(16384, 110250)
            batch_max_frames = batch_max_steps // hop_size

            if len(mel) > batch_max_frames:
                interval_start = 0
                interval_end = len(mel) - batch_max_frames
                start_frame = random.randint(interval_start, interval_end)
                start_step = start_frame * hop_size
                mel = mel[start_frame : start_frame + batch_max_frames, :]
                f0 = f0[start_frame : start_frame + batch_max_frames, :]
                wav = wav[start_step : start_step + batch_max_steps]

            mel, _ = pad_seq(mel)
            f0, _ = pad_seq(f0)

            wav_16k = malaya_speech.resample(wav, sr, 16000)
            v = speaker_model([wav_16k])[0]
            v = v / v.max()

            yield {
                'mel': mel,
                'mel_length': [len(mel)],
                'f0': f0,
                'f0_length': [len(f0)],
                'audio': wav,
                'v': v,
            }


def get_dataset(batch_size = 4):
    def get():
        dataset = tf.data.Dataset.from_generator(
            generate,
            {
                'mel': tf.float32,
                'mel_length': tf.int32,
                'f0': tf.float32,
                'f0_length': tf.int32,
                'audio': tf.float32,
                'v': tf.float32,
            },
            output_shapes = {
                'mel': tf.TensorShape([None, 80]),
                'mel_length': tf.TensorShape([None]),
                'f0': tf.TensorShape([None, 1]),
                'f0_length': tf.TensorShape([None]),
                'audio': tf.TensorShape([None]),
                'v': tf.TensorShape([512]),
            },
        )
        dataset = dataset.shuffle(batch_size)
        dataset = dataset.padded_batch(
            batch_size,
            padded_shapes = {
                'audio': tf.TensorShape([None]),
                'mel': tf.TensorShape([None, 80]),
                'mel_length': tf.TensorShape([None]),
                'f0': tf.TensorShape([None, 1]),
                'f0_length': tf.TensorShape([None]),
                'v': tf.TensorShape([512]),
            },
            padding_values = {
                'audio': tf.constant(0, dtype = tf.float32),
                'mel': tf.constant(0, dtype = tf.float32),
                'mel_length': tf.constant(0, dtype = tf.int32),
                'f0': tf.constant(0, dtype = tf.float32),
                'f0_length': tf.constant(0, dtype = tf.int32),
                'v': tf.constant(0, dtype = tf.float32),
            },
        )
        return dataset

    return get


total_steps = 500000


def model_fn(features, labels, mode, params):
    vectors = features['v']
    X = features['mel']
    len_X = features['mel_length'][:, 0]
    X_f0 = features['f0']
    len_X_f0 = features['f0_length'][:, 0]

    hparams = speechsplit.hparams
    encoder_config = malaya_speech.config.transformer_config.copy()
    decoder_config = malaya_speech.config.transformer_config.copy()
    encoder_config['activation'] = 'mish'
    decoder_config['activation'] = 'mish'
    interplnr = speechsplit.InterpLnr(hparams)
    model = speechsplitformer.Model(encoder_config, decoder_config, hparams)
    model_F0 = speechsplitformer.Model_F0(
        encoder_config, decoder_config, hparams
    )

    bottleneck_speaker = tf.keras.layers.Dense(hparams.dim_spk_emb)
    speaker_dim = bottleneck_speaker(vectors)

    x_f0_intrp = interplnr(tf.concat([X, X_f0], axis = -1), len_X)
    f0_org_intrp = speechsplit.quantize_f0_tf(x_f0_intrp[:, :, -1])
    x_f0_intrp_org = tf.concat((x_f0_intrp[:, :, :-1], f0_org_intrp), axis = -1)
    f0_org = speechsplit.quantize_f0_tf(X_f0[:, :, 0])

    _, _, _, _, mel_outputs = model(x_f0_intrp_org, X, speaker_dim, len_X)
    _, _, _, f0_outputs = model_F0(X, f0_org, len_X)

    loss_f = tf.losses.absolute_difference
    max_length = tf.cast(tf.reduce_max(len_X), tf.int32)
    mask = tf.sequence_mask(
        lengths = len_X, maxlen = max_length, dtype = tf.float32
    )
    mask = tf.expand_dims(mask, axis = -1)
    mel_loss = loss_f(labels = X, predictions = mel_outputs, weights = mask)
    f0_loss = loss_f(labels = f0_org, predictions = f0_outputs, weights = mask)

    loss = mel_loss + f0_loss

    tf.identity(loss, 'total_loss')
    tf.identity(mel_loss, 'mel_loss')
    tf.identity(f0_loss, 'f0_loss')

    tf.summary.scalar('total_loss', loss)
    tf.summary.scalar('mel_loss', mel_loss)
    tf.summary.scalar('f0_loss', f0_loss)

    global_step = tf.train.get_or_create_global_step()

    if mode == tf.estimator.ModeKeys.TRAIN:

        train_op = train.optimizer.adamw.create_optimizer(
            loss,
            init_lr = 0.0001,
            num_train_steps = total_steps,
            num_warmup_steps = 150000,
            end_learning_rate = 0.00001,
            weight_decay_rate = 0.001,
            beta_1 = 0.9,
            beta_2 = 0.98,
            epsilon = 1e-6,
            clip_norm = 1.0,
        )
        estimator_spec = tf.estimator.EstimatorSpec(
            mode = mode, loss = loss, train_op = train_op
        )

    elif mode == tf.estimator.ModeKeys.EVAL:

        estimator_spec = tf.estimator.EstimatorSpec(
            mode = tf.estimator.ModeKeys.EVAL, loss = loss
        )

    return estimator_spec


train_hooks = [
    tf.train.LoggingTensorHook(
        ['total_loss', 'mel_loss', 'f0_loss'], every_n_iter = 1
    )
]
train_dataset = get_dataset()

save_directory = 'speechsplitformer-vggvox-v2'

train.run_training(
    train_fn = train_dataset,
    model_fn = model_fn,
    model_dir = save_directory,
    num_gpus = 1,
    log_step = 1,
    save_checkpoint_step = 2000,
    max_steps = total_steps,
    train_hooks = train_hooks,
    eval_step = 0,
)