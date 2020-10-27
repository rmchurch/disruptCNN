#!/usr/bin python
#
#MIT License
#
#Copyright (c) 2018 CMU Locus Lab
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#
#Temporal Convolutional Network code, from the original repo (https://github.com/locuslab/TCN)
#@article{BaiTCN2018,
#	author    = {Shaojie Bai and J. Zico Kolter and Vladlen Koltun},
#	title     = {An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling},
#	journal   = {arXiv:1803.01271},
#	year      = {2018},
#}
#
#modified slightly here for arbitrary dilation factors. 
#

import torch
import torch.nn as nn
from torch.nn.utils import weight_norm
import numpy as np
#from apex.parallel import SyncBatchNorm as batch_norm
from torch.nn import LayerNorm
#import torch.nn.init as init


class Chomp1d(nn.Module):
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous()


class TemporalBlock(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2, nsub=None):
        super(TemporalBlock, self).__init__()
        #self.norm1 = batch_norm(n_inputs)
        self.norm1 = LayerNorm(nsub)
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation)
        # self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size,
        #                            stride=stride, padding=padding, dilation=dilation)
        # init.constant(self.conv1.weight, 1.0)
        # init.constant(self.conv1.bias, 0.0)
        
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        #self.norm2 = batch_norm(n_outputs)
        self.norm2 = LayerNorm(nsub)
        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size,
                                           stride=stride, padding=padding, dilation=dilation)
        # self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size,
        #                                    stride=stride, padding=padding, dilation=dilation)
        # init.constant(self.conv2.weight, 1.0)
        # init.constant(self.conv2.bias, 0.0)

        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        #self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
        #                         self.conv2, self.chomp2, self.relu2, self.dropout2)
        self.net = nn.Sequential(self.norm1, self.relu1, self.conv1, self.chomp1, self.dropout1,
                                 self.norm2, self.relu2, self.conv2, self.chomp2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        self.conv1.weight.data.normal_(0, 0.01)
        self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)

    def forward(self, x):
        #write out components for testing
        #x1 = self.norm1(x)
        #x2 = self.relu1(x1)
        #x3 = self.conv1(x2)
        #x4 = self.chomp1(x3)
        #x5 = self.norm2(x4)
        #x6 = self.relu2(x5)
        #x7 = self.conv2(x6)
        #out = self.chomp2(x7)
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        #return self.relu(out + res)
        return out + res


class TemporalConvNet(nn.Module):
    def __init__(self, num_inputs, num_channels, dilation_size = 2, kernel_size=2, dropout=0.2, nsub=None):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        if np.isscalar(dilation_size): dilation_size = [dilation_size**i for i in range(num_levels)]
        for i in range(num_levels):
            dilation = dilation_size[i]
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1,
                                     padding=(kernel_size-1) * dilation, dilation=dilation, 
                                     dropout=dropout, nsub=nsub)]

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)
