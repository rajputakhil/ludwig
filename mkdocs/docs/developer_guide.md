Codebase Structure
==================

The codebase is organized in a modular, datatype / feature centric way so that adding a feature for a new datatype is pretty straightforward and requires isolated code changes. All the datatype specific logic lives in the corresponding feature module all of which are under `ludwig/features/`.

Feature classes contain raw data preprocessing logic specific to each data type. All input (output) features implement `build_input` (`build_output`) method which is used to build encodings (decode outputs). Output features also contain datatype-specific logic to compute output measures such as loss, accuracy, etc.

Encoders and decoders are modularized as well (they are under `ludwig/models/modules`) so that they can be used by multiple features. For example sequence encoders are shared among text, sequence, and timeseries features.

Various model architecture components which can be reused are also split into dedicated modules, for example convolutional modules, fully connected modules, etc.

Bulk of the training logic resides in `ludwig/models/model.py` which initializes a tensorflow session, feeds the data, and executes training.

Adding an Encoder
=================

 1. Add a new encoder class
---------------------------

Source code for encoders lives under `ludwig/models/modules`.
New encoder objects should be defined in the corresponding files, for example all new sequence encoders should be added to `ludwig/models/modules/sequence_encoders.py`.

All the encoder parameters should be provided as arguments in the constructor with their default values set. For example `RNN` encoder takes the following list of arguments in its constructor:

```python
def __init__(
    self,
    should_embed=True,
    vocab=None,
    representation='dense',
    embedding_size=256,
    embeddings_trainable=True,
    pretrained_embeddings=None,
    embeddings_on_cpu=False,
    num_layers=1,
    state_size=256,
    cell_type='rnn',
    bidirectional=False,
    dropout=False,
    initializer=None,
    regularize=True,
    reduce_output='last',
    **kwargs
):
```

Typically all the dependencies are initialized in the encoder's constructor (in the case of the RNN encoder these are EmbedSequence and RecurrentStack modules) so that at the end of the constructor call all the layers are fully described.

Actual creation of tensorflow variables takes place inside the `__call__` method of the encoder. All encoders should have the following signature:

```python
__call__(
    self,
    input_placeholder,
    regularizer,
    dropout,
    is_training
)
```

__Inputs__

- __input_placeholder__ (tf.Tensor): input tensor.
- __regularizer__ (A (Tensor -> Tensor or None) function): regularizer function passed to `tf.get_variable` method.
- __dropout__ (tf.Tensor(dtype: tf.float32)): dropout rate.
- __is_training__ (tf.Tensor(dtype: tf.bool), default: `True`): boolean indicating whether this is a training dataset.


__Return__

- __hidden__ (tf.Tensor(dtype: tf.float32)): feature encodings.
- __hidden_size__ (int): feature encodings size.

Encoders are initialized as class member variables in input feature object constructors and called inside `build_input` methods.


 2. Add the new encoder class to the corresponding encoder registry
-------------------------------------------------------------------

Mapping between encoder keywords in the model definition and encoder classes is done by encoder registries: for example sequence encoder registry is defined in `ludwig/features/sequence_feature.py`

```
sequence_encoder_registry = {
    'stacked_cnn': StackedCNN,
    'parallel_cnn': ParallelCNN,
    'stacked_parallel_cnn': StackedParallelCNN,
    'rnn': RNN,
    'cnnrnn': CNNRNN,
    'embed': EmbedEncoder
}
```

Adding a Decoder
================

 1. Add a new decoder class
---------------------------

Souce code for decoders lives under `ludwig/models/modules`.
New decoder objects should be defined in the corresponding files, for example all new sequence decoders should be added to `ludwig/models/modules/sequence_decoders.py`.

All the decoder parameters should be provided as arguments in the constructor with their default values set. For example `Generator` decoder takes the following list of arguments in its constructor:

```python
__init__(
    self,
    cell_type='rnn',
    state_size=256,
    embedding_size=64,
    beam_width=1,
    num_layers=1,
    attention_mechanism=None,
    tied_embeddings=None,
    initializer=None,
    regularize=True,
    **kwargs
)
```

Decoders are initialized as class member variables in output feature object constructors and called inside `build_output` methods.

 2. Add the new decoder class to the corresponding decoder registry
-------------------------------------------------------------------

Mapping between decoder keywords in the model definition and decoder classes is done by decoder registries: for example sequence decoder registry is defined in `ludwig/features/sequence_feature.py`

```python
sequence_decoder_registry = {
    'generator': Generator,
    'tagger': Tagger
}
```

Adding a new Feature Type
=========================

 1. Add a new feature class
---------------------------

Souce code for feature classes lives under `ludwig/features`.
Input and output feature classes are defined in the same file, for example `CategoryInputFeature` and `CategoryOutputFeature` are defined in `ludwig/features/category_feature.py`.

An input features inherit from the `InputFeature` and corresponding base feature classes, for example `CategoryInputFeature` inherits from `CategoryBaseFeature` and `InputFeature`.

Similarly, output features inherit from the `OutputFeature` and corresponding base feature classes, for example `CategoryOutputFeature` inherits from `CategoryBaseFeature` and `OutputFeature`.

Feature parameters are provided in a dictionary of key-value pairs as an argument to the input or output feature constructor which contains default parameter values as well.

All input and output features should implement `build_input` and `build_output` methods correspondingly with the following signatures:


### build_input

```python
build_input(
    self,
    regularizer,
    dropout_rate,
    is_training=False,
    **kwargs
)
```

__Inputs__


- __regularizer__ (A (Tensor -> Tensor or None) function): regularizer function passed to `tf.get_variable` method.
- __dropout_rate__ (tf.Tensor(dtype: tf.float32)): dropout rate.
- __is_training__ (tf.Tensor(dtype: tf.bool), default: `True`): boolean indicating whether this is a training dataset.


__Return__

- __feature_representation__ (dict): the following dictionary

```python
{
    'type': self.type, # str
    'representation': feature_representation, # tf.Tensor(dtype: tf.float32)
    'size': feature_representation_size, # int
    'placeholder': placeholder # tf.Tensor(dtype: tf.float32)
}
```

### build_output

```python
build_output(
    self,
    hidden,
    hidden_size,
    regularizer=None,
    **kwargs
)
```

__Inputs__

- __hidden__ (tf.Tensor(dtype: tf.float32)): output feature representation.
- __hidden_size__ (int): output feature representation size.
- __regularizer__ (A (Tensor -> Tensor or None) function): regularizer function passed to `tf.get_variable` method.

__Return__
- __train_mean_loss__ (tf.Tensor(dtype: tf.float32)): mean loss for train dataset.
- __eval_loss__ (tf.Tensor(dtype: tf.float32)): mean loss for evaluation dataset.
- __output_tensors__ (dict): dictionary containing feature specific output tensors (predictions, probabilities, losses, etc).

 2. Add the new feature class to the corresponding feature registry
-------------------------------------------------------------------

Input and output feature registries are defined in `ludwig/features/feature_registries.py`.


Style Guidelines
================
We expect contributions to mimic existing patterns in the codebase and demonstrate good practices: the code should be concise, readable, PEP8-compliant, and conforming to 80 character line length limit.

Tests
=====

We are using ```pytest``` to run tests. 
Current test coverage is limited to several integration tests which ensure end-to-end functionality but we are planning to expand it.

Checklist
---------

Before running tests, make sure 
1. Your environment is properly setup.
2. You build the latest code by running ```python setup.py install``` from the Ludwig root directory.
3. You have write access on the machine. Some of the tests require saving data to disk.

Running tests
-------------

To run all tests, just run
```pytest``` from the ludwig root directory.

To run a single test, run
``` 
pytest path_to_filename::test_method_name
```

Example
-------

```
pytest tests/integration_tests/test_experiment.py::test_visual_question_answering
```
