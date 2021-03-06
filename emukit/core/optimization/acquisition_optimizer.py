# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import abc
from typing import Dict, Optional, Tuple

import numpy as np

from .context_manager import ContextManager, Context
from .. import ParameterSpace
from ..acquisition import Acquisition

import logging
_log = logging.getLogger(__name__)


class AcquisitionOptimizerBase(abc.ABC):
    def __init__(self, space: ParameterSpace):
        self.space = space
        self.gpyopt_space = space.convert_to_gpyopt_design_space()

    def _validate_context_parameters(self, context: Dict[str, any]):
        for context_name, context_value in context.items():
            # Check parameter exists in space
            if context_name not in self.space.parameter_names:
                raise ValueError(context_name + ' appears as variable in context but not in the parameter space.')

            # Log warning if context parameter is out of domain
            param = self.space.get_parameter_by_name(context_name)
            if param.check_in_domain(context_value) is False:
                _log.warning(context_name + ' with value ' + str(context_value), ' is out of the domain')
            else:
                _log.info('Parameter ' + context_name + ' fixed to ' + str(context_value))

    @abc.abstractmethod
    def _optimize(self, acquisition: Acquisition, context_manager: ContextManager)\
        -> Tuple[np.ndarray, np.ndarray]:
        """
        Implementation of optimization. See class docstring for details.

        :param acquisition: The acquisition function to be optimized
        :param context_manager: Optimization context manager.
        :return: Tuple of (location of maximum, acquisition value at maximizer)
        """
        pass

    def optimize(self, acquisition: Acquisition, context: Optional[Context] = None)\
        -> Tuple[np.ndarray, np.ndarray]:
        """
        Optimizes the acquisition function.

        :param acquisition: The acquisition function to be optimized
        :param context: Optimization context.
                        Determines whether any variable values should be fixed during the optimization
        :return: Tuple of (location of maximum, acquisition value at maximizer)
        """
        if context is None:
            context = dict()
        else:
            self._validate_context_parameters(context)
        context_manager = ContextManager(self.space, context, self.gpyopt_space)
        max_x, max_value = self._optimize(acquisition, context_manager)

        # Optimization might not match any encoding exactly
        # Rounding operation here finds the closest encoding
        rounded_max_x = self.space.round(max_x)

        if not np.array_equal(max_x, rounded_max_x):
            # re-evaluate if x changed while rounding to make sure value is correct
            return rounded_max_x, acquisition.evaluate(rounded_max_x)
        else:
            return max_x, max_value
