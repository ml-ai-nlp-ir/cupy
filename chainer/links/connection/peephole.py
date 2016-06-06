from chainer.functions.activation import peephole 
from chainer import link
from chainer.links.connection import linear
from chainer import variable
from chainer.functions.activation import sigmoid
from chainer.functions.activation import tanh
from chainer.functions.array import reshape
from chainer.functions.array import split_axis

import six
import numpy


class Peephole(link.Chain):

    """Fully-connected LSTM with peephole connections layer.

    This is a fully-connected LSTM with peephole connections layer as a chain. Unlike the
    :func:`~chainer.functions.peephole` function, which is defined as a stateless
    activation function, this chain holds upward, lateral and peephole connections as
    child links.

    It also maintains *states*, including the cell state and the output
    at the previous time step. Therefore, it can be used as a *stateful LSTM*.

    Args:
        in_size (int): Dimensionality of input vectors.
        out_size (int): Dimensionality of output vectors.

    Attributes:
        upward (~chainer.links.Linear): Linear layer of upward connections.
        lateral (~chainer.links.Linear): Linear layer of lateral connections.
        peep_i (~chainer.links.Linear): Linear layer of peephole input connections.
        peep_f (~chainer.links.Linear): Linear layer of peephole forget connections.
        peep_o (~chainer.links.Linear): Linear layer of peephole output connections.
        c (~chainer.Variable): Cell states of LSTM units.
        h (~chainer.Variable): Output at the previous time step.

    """
    def __init__(self, in_size, out_size):
        super(Peephole, self).__init__(
            upward=linear.Linear(in_size, 4 * out_size),
            lateral=linear.Linear(out_size, 4 * out_size, nobias=True),
            peep_i=linear.Linear(out_size, out_size, nobias=True),
            peep_f=linear.Linear(out_size, out_size, nobias=True), 
            peep_o=linear.Linear(out_size, out_size, nobias=True), 
        )
        self.state_size = out_size
        self.reset_state()

    def to_cpu(self):
        super(Peephole, self).to_cpu()
        if self.c is not None:
            self.c.to_cpu()
        if self.h is not None:
            self.h.to_cpu()

    def to_gpu(self, device=None):
        super(Peephole, self).to_gpu(device)
        if self.c is not None:
            self.c.to_gpu(device)
        if self.h is not None:
            self.h.to_gpu(device)

    def reset_state(self):
        """Resets the internal state.

        It sets ``None`` to the :attr:`c` and :attr:`h` attributes.

        """
        self.c = self.h = None

    def __call__(self, x):
        """Updates the internal state and returns the LSTM outputs.

        Args:
            x (~chainer.Variable): A new batch from the input sequence.

        Returns:
            ~chainer.Variable: Outputs of updated LSTM units.

        """
        lstm_in = self.upward(x)
        if self.h is not None:
            lstm_in += self.lateral(self.h)
        if self.c is None:
            xp = self.xp
            self.c = variable.Variable(
                xp.zeros((len(x.data), self.state_size), dtype=x.data.dtype),
                volatile='auto')
        
        lstm_in = reshape.reshape(lstm_in, (lstm_in.data.shape[0], lstm_in.data.shape[1] // 4, 4) + lstm_in.data.shape[2:])
        a, i, f, o = split_axis.split_axis(lstm_in, 4, 2) 
        a = reshape.reshape(a, (a.data.shape[0], a.data.shape[1])) 
        i = reshape.reshape(i, (i.data.shape[0], i.data.shape[1])) 
        f = reshape.reshape(f, (f.data.shape[0], f.data.shape[1])) 
        o = reshape.reshape(o, (o.data.shape[0], o.data.shape[1])) 
        peep_in_i = self.peep_i(self.c)
        peep_in_f = self.peep_f(self.c)
        a = tanh.tanh(a)
            #peep_in_i.data = numpy.reshape(peep_in_i.data, i.data.shape)
        i = sigmoid.sigmoid(i + peep_in_i)
            #peep_in_f.data = numpy.reshape(peep_in_f.data, f.data.shape)
        f = sigmoid.sigmoid(f + peep_in_f)
        self.c = a * i + f * self.c
        peep_in_o = self.peep_o(self.c)
            #peep_in_o.data = numpy.reshape(peep_in_o.data, o.data.shape)
        o = sigmoid.sigmoid(o + peep_in_o)
        self.h = o * tanh.tanh(self.c)
        return self.h
