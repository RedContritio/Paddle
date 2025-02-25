# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
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

import unittest

import numpy as np
from pass_test import PassTest

import paddle
from paddle.base import core

paddle.enable_static()


class TestConv2dAddActFusePattern(PassTest):
    r"""
      x_var   f_var
    \       /
       conv2d
         |
      conv2d_var    y_var
          \          /
         elementwise_add
              |
       elementwise_add_var
              |
             act
              |
            act_var
    """

    def is_program_valid(self, program):
        return True

    def build_ir_progam(self):
        with paddle.pir_utils.IrGuard():
            main_prog = paddle.static.Program()
            start_prog = paddle.static.Program()
            with paddle.pir.core.program_guard(main_prog, start_prog):
                x = paddle.static.data(
                    name='x', shape=[3, 1, 28, 28], dtype='float32'
                )
                conv2d = paddle.nn.Conv2D(
                    in_channels=1,
                    out_channels=32,
                    kernel_size=3,
                    padding=1,
                    data_format='NCHW',
                    bias_attr=False,
                )
                y = paddle.static.data(
                    name="y", shape=[3, 32, 28, 28], dtype="float32"
                )
                act_op = paddle.nn.ReLU()
                out = act_op(paddle.add(conv2d(x), y))
                out = paddle.assign(out)
                self.pass_list = ['conv2d_add_act_fuse_pass']
                self.feeds = {
                    "x": np.random.random((3, 1, 28, 28)).astype("float32"),
                    "y": np.random.random((3, 32, 28, 28)).astype("float32"),
                }
                self.fetch_list = [out]
                self.valid_op_map = {
                    "pd_op.add": 0,
                    "pd_op.relu": 0,
                    "pd_op.conv2d": 0,
                    "pd_op.fused_conv2d_add_act": 1,
                }
                return [main_prog, start_prog]

    def setUp(self):
        if core.is_compiled_with_cuda():
            self.places.append(paddle.CUDAPlace(0))
        # todo(bukejiyu): This pass will support accuracy verification in the future
        self.skip_accuracy_verification = True

    def sample_program(self):
        yield self.build_ir_progam(), False

    def test_check_output(self):
        self.check_pass_correct()


class TestConv2dAdd2ActFusePattern(PassTest):
    r"""
     x_var   f_var(persistable)
         \       /
             conv2d
             |
             conv2d_var    y_var(persistable)
                 \          /
             elementwise_add
                     |
    x1_var  elementwise_add_out_var
      \              /
      elementwise_add
             |
            act
             |
           act_var
    """

    def is_program_valid(self, program):
        return True

    def build_ir_progam(self):
        with paddle.pir_utils.IrGuard():
            main_prog = paddle.static.Program()
            start_prog = paddle.static.Program()
            with paddle.pir.core.program_guard(main_prog, start_prog):
                x = paddle.static.data(
                    name='x', shape=[3, 1, 28, 28], dtype='float32'
                )
                conv2d = paddle.nn.Conv2D(
                    in_channels=1,
                    out_channels=32,
                    kernel_size=3,
                    padding=1,
                    data_format='NCHW',
                    bias_attr=False,
                )
                y = paddle.static.data(
                    name="y", shape=[3, 32, 28, 28], dtype="float32"
                )
                residual_data = paddle.static.data(
                    name="residual_data", shape=[3, 32, 28, 28], dtype="float32"
                )
                act_op = paddle.nn.ReLU()
                out = act_op(
                    paddle.add(residual_data, paddle.add(conv2d(x), y))
                )
                out = paddle.assign(out)
                self.pass_list = ['conv2d_add_act_fuse_pass']
                self.feeds = {
                    "x": np.random.random((3, 1, 28, 28)).astype("float32"),
                    "y": np.random.random((3, 32, 28, 28)).astype("float32"),
                    "residual_data": np.random.random((3, 32, 28, 28)).astype(
                        "float32"
                    ),
                }
                self.fetch_list = [out]
                self.valid_op_map = {
                    "pd_op.add": 0,
                    "pd_op.relu": 0,
                    "pd_op.conv2d": 0,
                    "pd_op.fused_conv2d_add_act": 1,
                }
                return [main_prog, start_prog]

    def setUp(self):
        if core.is_compiled_with_cuda():
            self.places.append(paddle.CUDAPlace(0))
        # todo(bukejiyu): This pass will support accuracy verification in the future
        self.skip_accuracy_verification = True

    def sample_program(self):
        yield self.build_ir_progam(), False

    def test_check_output(self):
        self.check_pass_correct()


if __name__ == "__main__":
    unittest.main()
