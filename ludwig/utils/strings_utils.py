#! /usr/bin/env python
# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import json
import logging
import re
import unicodedata
from collections import Counter

import numpy as np

from ludwig.utils.misc import get_from_registry
from ludwig.utils.nlp_utils import load_nlp_pipeline, process_text

UNKNOWN_SYMBOL = '<UNK>'
PADDING_SYMBOL = '<PAD>'

SPLIT_REGEX = re.compile(r'\s+')
SPLIT_PUNCTUATION_REGEX = re.compile(r'\w+|[^\w\s]')
COMMA_REGEX = re.compile(r'\s*,\s*')
UNDERSCORE_REGEX = re.compile(r'\s*_\s*')


def make_safe_filename(s):
    def safe_char(c):
        if c.isalnum():
            return c
        else:
            return '_'

    return ''.join(safe_char(c) for c in s).rstrip('_')


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def str2bool(v):
    return v.lower() in ('yes', 'true', 't', '1')


def match_replace(string_to_match, list_regex):
    """Matches strings against regular expressions.

    arguments:
    string_to_match -- the string to match

    returns:
    string_to_match -- the cleaned string
    matched -- the list of regular expressions that matched
    """
    matched = []
    for regex in list_regex:
        match = re.search(regex[0], string_to_match)
        if match:
            string_to_match = re.sub(regex[0], regex[1], string_to_match)
            matched.append(regex[0].pattern)
    return string_to_match, matched


def create_vocabulary(data, format='space', custom_vocabulary=(),
                      add_unknown=True, add_padding=True,
                      lowercase=True,
                      num_most_frequent=None):
    max_line_length = 0
    unit_counts = Counter()

    if format == 'custom':
        vocab = sorted(list(set(custom_vocabulary)))
    else:
        format_function = get_from_registry(
            format,
            format_registry
        )
        for line in data:
            processed_line = format_function(
                line.lower() if lowercase else line)
            unit_counts.update(processed_line)
            max_line_length = max(max_line_length, len(processed_line))

        vocab = [unit for unit, count in
                 unit_counts.most_common(num_most_frequent)]

    if add_unknown:
        vocab = [UNKNOWN_SYMBOL] + vocab
    if add_padding:
        vocab = [PADDING_SYMBOL] + vocab

    str2idx = {unit: i for i, unit in enumerate(vocab)}
    str2freq = {unit: unit_counts.get(unit) if unit in unit_counts else 0 for
                unit in vocab}

    return vocab, str2idx, str2freq, max_line_length


def get_sequence_vector(sequence, format, unit_to_id, lowercase=True):
    format_function = get_from_registry(
        format,
        format_registry
    )
    format_dtype = get_from_registry(
        format,
        format_dtype_registry
    )
    return _get_sequence_vector(sequence, format_function, format_dtype,
                                unit_to_id, lowercase=lowercase)


def _get_sequence_vector(sequence, format_function, format_dtype, unit_to_id,
                         lowercase=True):
    unit_sequence = format_function(sequence.lower() if lowercase else sequence)
    unit_indices_vector = np.empty(len(unit_sequence), dtype=format_dtype)
    for i in range(len(unit_sequence)):
        curr_unit = unit_sequence[i]
        if curr_unit in unit_to_id:
            unit_indices_vector[i] = unit_to_id[curr_unit]
        else:
            unit_indices_vector[i] = unit_to_id[UNKNOWN_SYMBOL]
    return unit_indices_vector


def build_sequence_matrix(sequences, inverse_vocabulary, format, length_limit,
                          padding_symbol, padding='right',
                          lowercase=True):
    format_function = get_from_registry(
        format,
        format_registry
    )
    format_dtype = get_from_registry(
        format,
        format_dtype_registry
    )
    max_length = 0
    unit_vectors = []
    for sequence in sequences:
        unit_indices_vector = _get_sequence_vector(sequence, format_function,
                                                   format_dtype,
                                                   inverse_vocabulary,
                                                   lowercase=lowercase)
        unit_vectors.append(unit_indices_vector)
        if len(unit_indices_vector) > max_length:
            max_length = len(unit_indices_vector)

    if max_length < length_limit:
        logging.debug('max length of {0}: {1} < limit: {2}'.format(
            format, max_length, length_limit
        ))
    max_length = length_limit
    sequence_matrix = np.full((len(sequences), max_length),
                              inverse_vocabulary[padding_symbol],
                              dtype=format_dtype)
    for i, vector in enumerate(unit_vectors):
        limit = min(vector.shape[0], max_length)
        if padding == 'right':
            sequence_matrix[i, :limit] = vector[:limit]
        else:  # if padding == 'left
            sequence_matrix[i, max_length - limit:] = vector[:limit]
    return sequence_matrix


def ids_array_to_string(matrix, idx2str):
    texts = []
    for row in matrix:
        texts.append(
            ' '.join(map(lambda x: idx2str[x], [x for x in row if x > 0])))
    return texts


def json_string_to_list(s):
    s = str.replace(s, '\'', '\'')
    return json.loads(str.replace(s, '\'', '\''))


def space_string_to_list(s):
    return SPLIT_REGEX.split(s.strip())


def space_punctuation_string_to_list(s):
    return SPLIT_PUNCTUATION_REGEX.split(s.strip())

def underscore_string_to_list(s):
    return UNDERSCORE_REGEX.split(s.strip())


def comma_string_to_list(s):
    return COMMA_REGEX.split(s.strip())


def untokenized_string_to_list(s):
    return [s]


def stripped_string_to_list(s):
    return [s.strip()]


def english_tokenize(text):
    return process_text(text, load_nlp_pipeline())


def english_tokenize_filter(text):
    return process_text(text, load_nlp_pipeline(),
                        filter_numbers=True,
                        filter_punctuation=True,
                        filter_short_tokens=True)


def english_tokenize_remove_stopwords(text):
    return process_text(text, load_nlp_pipeline(), filter_stopwords=True)


def english_lemmatize(text):
    return process_text(text, load_nlp_pipeline(), return_lemma=True)


def english_lemmatize_filter(text):
    return process_text(text, load_nlp_pipeline(),
                        return_lemma=True,
                        filter_numbers=True,
                        filter_punctuation=True,
                        filter_short_tokens=True)


def english_lemmatize_remove_stopwords(text):
    return process_text(text, load_nlp_pipeline(),
                        return_lemma=True,
                        filter_stopwords=True)


def characters_to_list(s):
    return s


format_registry = {
    'json': json_string_to_list,
    'space': space_string_to_list,
    'space_punct': space_punctuation_string_to_list,
    'underscore': underscore_string_to_list,
    'comma': comma_string_to_list,
    'untokenized': untokenized_string_to_list,
    'stripped': stripped_string_to_list,
    'english_tokenize': english_tokenize,
    'english_tokenize_filter': english_tokenize_filter,
    'english_tokenize_remove_stopwords': english_tokenize_remove_stopwords,
    'english_lemmatize': english_lemmatize,
    'english_lemmatize_filter': english_lemmatize_filter,
    'english_lemmatize_remove_stopwords': english_lemmatize_remove_stopwords,
    'characters': characters_to_list
}

format_dtype_registry = {
    'json': np.int32,
    'space': np.int32,
    'space_punct': np.int32,
    'underscore': np.int32,
    'comma': np.int32,
    'untokenized': np.int32,
    'stripped': np.int32,
    'english_tokenize': np.int32,
    'english_tokenize_filter': np.int32,
    'english_tokenize_remove_stopwords': np.int32,
    'english_lemmatize': np.int32,
    'english_lemmatize_filter': np.int32,
    'english_lemmatize_remove_stopwords': np.int32,
    'characters': np.int8
}
