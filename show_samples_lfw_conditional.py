from argparse import ArgumentParser

import numpy as np
from pylearn2.config import yaml_parse
from pylearn2.datasets import dense_design_matrix
from pylearn2.gui.patch_viewer import PatchViewer
from pylearn2.utils import serial
import theano


def sample_conditional_fix_random(generator, m, n, noise_range=1):
    """
    Sample `m * n` points in condition space by sampling `m` points
    and adding small random noise `n` times for each point.
    """

    conditional_data = generator.condition_distribution.sample(m).eval()
    conditional_dim = conditional_data.shape[1]
    conditional_data = (conditional_data.reshape((m, 1, conditional_dim)).repeat(n, axis=1)
                                        .reshape((m * n, conditional_dim)))
    conditional_data += noise_range * (np.random.rand(*conditional_data.shape) * 2. - 1.)

    return conditional_data


def sample_conditional_fix_embeddings(generator, m, n,
                                      embedding_file='/afs/cs.stanford.edu/u/jgauthie/scr/lfw-lsa/LFW_attributes_30d.npz',
                                      noise_range=1):
    """
    Sample `m * n` points in condition space by retrieving `m` points
    from a provided dataset and adding small random noise `n - 1` times
    for each point.
    """

    embs = np.load(embedding_file)['arr_0']
    np.random.shuffle(embs)

    source_points = embs[:m]
    dim = source_points.shape[1]

    noisy_points = np.copy(source_points).reshape((m, 1, dim)).repeat(n - 1, axis=1)
    noisy_points += noise_range * (np.random.rand(*noisy_points.shape) * 2. - 1.)

    ret = (np.concatenate((source_points.reshape((m, 1, dim)), noisy_points), axis=1)
             .reshape((m * n, dim)))

    return np.cast['float32'](ret)


# Build string mapping for conditional samplers so that they can be
# triggered from CLI
conditional_samplers = {
    'fix_random': sample_conditional_fix_random,
    'fix_embeddings': sample_conditional_fix_embeddings,
}


# Parse arguments
parser = ArgumentParser(description=('Sample images from the generative component of a '
                                     'cGAN learned on the LFW/LFWcrop dataset.'))
parser.add_argument('-g', '--model-is-generator-only', action='store_true', default=False,
                    help='If true, provided model path is a generator only, not a full cGAN')
parser.add_argument('-s', '--conditional-sampler', default='fix_random',
                    choices=conditional_samplers.values(),
                    type=lambda k: conditional_samplers[k])
parser.add_argument('model_path')
args = parser.parse_args()


# Load model
model = serial.load(args.model_path)
generator = model if args.model_is_generator_only else model.generator
space = generator.get_output_space()

rows = 4
sample_cols = 5

# First sample conditional data
# TODO: Also try retrieving real conditional data
conditional_batch = generator.condition_space.make_theano_batch()
conditional_data = args.conditional_sampler(generator, rows, sample_cols)

topo_samples_batch = generator.sample(conditional_batch)
topo_sample_f = theano.function([conditional_batch], topo_samples_batch)
topo_samples = topo_sample_f(conditional_data).swapaxes(0, 3)

pv = PatchViewer(grid_shape=(rows, sample_cols), patch_shape=(32,32),
                 is_color=True)
scale = np.abs(topo_samples).max()

for i in xrange(topo_samples.shape[0]):
    topo_sample = topo_samples[i, :, :, :]
    print topo_samples.shape, topo_sample.shape
    print topo_sample.min(), topo_sample.max(), topo_sample.shape
    pv.add_patch(topo_sample / scale, rescale=False)

pv.show()