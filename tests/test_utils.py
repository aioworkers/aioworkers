import os
from unittest import mock

from aioworkers import utils


def test_urandom_seed():
    utils.random_seed()


def test_random_seed():
    def not_implemented_urandom(*args):
        raise NotImplementedError

    with mock.patch.object(os, "urandom", not_implemented_urandom):
        utils.random_seed()
